import csv
import os
import time
from datetime import datetime

from google.cloud import bigquery
from google.api_core.exceptions import NotFound

from config import (
    PROJECT_ID,
    LOCATION,
    PROCESSOR_ID,
    BUCKET_NAME,
    RAW_FOLDER,
    OUTPUT_FOLDER,
    validate_config,
)

from storage_client import (
    list_raw_pdfs,
    download_blob_to_temp,
    upload_file_to_gcs,
)

from document_ai_client import process_pdf_with_document_ai
from parser import parse_w2_document
from validation import validate_extracted_fields


OUTPUT_FOLDER_LOCAL = "sample_output"
OCR_CACHE_FOLDER = "sample_output/ocr_cache_all"

ALL_RESULTS_CSV = "sample_output/extracted_all_results.csv"
MANUAL_REVIEW_CSV = "sample_output/manual_review_records.csv"
SUMMARY_CSV = "sample_output/full_processing_summary.csv"
STATUS_STATS_CSV = "sample_output/status_statistics.csv"

USE_OCR_CACHE = True
FORCE_REFRESH_OCR = False

# Run repeatedly until all PDFs are processed.
MAX_FILES_PER_RUN = 50

# Failed files will be retried on the next run.
RETRY_FAILED = True

# BigQuery settings
SAVE_TO_BIGQUERY = True
BIGQUERY_LOCATION = "US"
BIGQUERY_DATASET_ID = "tax_form_extraction"
BIGQUERY_RESULTS_TABLE_ID = "extracted_all_results"
BIGQUERY_MANUAL_REVIEW_TABLE_ID = "manual_review_records"
BIGQUERY_SUMMARY_TABLE_ID = "full_processing_summary"
BIGQUERY_STATUS_STATS_TABLE_ID = "status_statistics"


FIELDNAMES = [
    "processed_at",
    "processing_time_seconds",
    "file_name",
    "file_type",
    "employee_name",
    "employee_address",
    "employee_ssn",
    "employer_name",
    "employer_address",
    "employer_ein",
    "name_confidence",
    "address_confidence",
    "id_confidence",
    "overall_confidence",
    "status",
    "review_reason",
]


SUMMARY_FIELDNAMES = [
    "metric",
    "value",
]


STATUS_STATS_FIELDNAMES = [
    "section",
    "file_type",
    "status",
    "total",
    "percentage",
    "ratio",
]


def get_file_type(file_name):
    if "clean" in file_name.lower():
        return "clean"

    if "noisy" in file_name.lower():
        return "noisy"

    return "unknown"


def get_ocr_cache_path(file_name):
    cache_file_name = file_name.replace(".pdf", ".txt")
    return os.path.join(OCR_CACHE_FOLDER, cache_file_name)


def load_existing_results():
    rows_by_file = {}

    if not os.path.exists(ALL_RESULTS_CSV):
        return rows_by_file

    with open(ALL_RESULTS_CSV, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            file_name = row.get("file_name", "").strip()

            if file_name:
                rows_by_file[file_name] = row

    return rows_by_file


def save_results_csv(rows_by_file):
    os.makedirs(OUTPUT_FOLDER_LOCAL, exist_ok=True)

    rows = [
        rows_by_file[file_name]
        for file_name in sorted(rows_by_file.keys())
    ]

    with open(ALL_RESULTS_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            extrasaction="ignore",
            restval="",
        )
        writer.writeheader()
        writer.writerows(rows)


def save_manual_review_csv(rows_by_file):
    rows = [
        row for row in rows_by_file.values()
        if row.get("status") != "AUTO_APPROVED"
    ]

    rows = sorted(rows, key=lambda row: row.get("file_name", ""))

    with open(MANUAL_REVIEW_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FIELDNAMES,
            extrasaction="ignore",
            restval="",
        )
        writer.writeheader()
        writer.writerows(rows)


def calculate_status_statistics(rows_by_file):
    rows = list(rows_by_file.values())
    statuses = ["AUTO_APPROVED", "NEEDS_REVIEW", "FAILED"]
    file_types = ["all", "clean", "noisy", "unknown"]

    stats_rows = []

    for file_type in file_types:
        if file_type == "all":
            filtered_rows = rows
        else:
            filtered_rows = [
                row for row in rows
                if row.get("file_type") == file_type
            ]

        file_type_total = len(filtered_rows)

        if file_type_total == 0:
            continue

        for status in statuses:
            status_total = sum(
                1 for row in filtered_rows
                if row.get("status") == status
            )

            percentage = round((status_total / file_type_total) * 100, 2)

            stats_rows.append({
                "section": "status_distribution",
                "file_type": file_type,
                "status": status,
                "total": status_total,
                "percentage": percentage,
                "ratio": "",
            })

    auto_total = sum(
        1 for row in rows
        if row.get("status") == "AUTO_APPROVED"
    )

    needs_review_total = sum(
        1 for row in rows
        if row.get("status") == "NEEDS_REVIEW"
    )

    needs_review_to_auto_ratio = (
        round(needs_review_total / auto_total, 4)
        if auto_total else ""
    )

    auto_to_needs_review_ratio = (
        round(auto_total / needs_review_total, 4)
        if needs_review_total else ""
    )

    stats_rows.append({
        "section": "ratio",
        "file_type": "all",
        "status": "NEEDS_REVIEW_to_AUTO_APPROVED",
        "total": "",
        "percentage": "",
        "ratio": needs_review_to_auto_ratio,
    })

    stats_rows.append({
        "section": "ratio",
        "file_type": "all",
        "status": "AUTO_APPROVED_to_NEEDS_REVIEW",
        "total": "",
        "percentage": "",
        "ratio": auto_to_needs_review_ratio,
    })

    return stats_rows


def save_status_statistics_csv(rows_by_file):
    stats_rows = calculate_status_statistics(rows_by_file)

    with open(STATUS_STATS_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=STATUS_STATS_FIELDNAMES)
        writer.writeheader()
        writer.writerows(stats_rows)

    return stats_rows


def get_float_value(value):
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def save_summary_csv(rows_by_file, total_pdf_count, batch_duration_seconds=None):
    rows = list(rows_by_file.values())

    auto_approved = sum(
        1 for row in rows
        if row.get("status") == "AUTO_APPROVED"
    )

    needs_review = sum(
        1 for row in rows
        if row.get("status") == "NEEDS_REVIEW"
    )

    failed = sum(
        1 for row in rows
        if row.get("status") == "FAILED"
    )

    clean_count = sum(
        1 for row in rows
        if row.get("file_type") == "clean"
    )

    noisy_count = sum(
        1 for row in rows
        if row.get("file_type") == "noisy"
    )

    total_processed = len(rows)

    total_processing_time_seconds = sum(
        get_float_value(row.get("processing_time_seconds"))
        for row in rows
    )

    average_processing_time_seconds = (
        round(total_processing_time_seconds / total_processed, 2)
        if total_processed else 0.0
    )

    auto_approved_percentage = (
        round((auto_approved / total_processed) * 100, 2)
        if total_processed else 0.0
    )

    needs_review_percentage = (
        round((needs_review / total_processed) * 100, 2)
        if total_processed else 0.0
    )

    failed_percentage = (
        round((failed / total_processed) * 100, 2)
        if total_processed else 0.0
    )

    needs_review_to_auto_ratio = (
        round(needs_review / auto_approved, 4)
        if auto_approved else ""
    )

    remaining_pdfs = total_pdf_count - total_processed

    estimated_remaining_time_seconds = (
        round(remaining_pdfs * average_processing_time_seconds, 2)
        if remaining_pdfs > 0 else 0.0
    )

    summary_rows = [
        {"metric": "total_pdfs_found_in_raw", "value": total_pdf_count},
        {"metric": "total_pdfs_processed", "value": total_processed},
        {"metric": "remaining_pdfs", "value": remaining_pdfs},

        {"metric": "auto_approved", "value": auto_approved},
        {"metric": "auto_approved_percentage", "value": auto_approved_percentage},

        {"metric": "needs_review", "value": needs_review},
        {"metric": "needs_review_percentage", "value": needs_review_percentage},

        {"metric": "failed", "value": failed},
        {"metric": "failed_percentage", "value": failed_percentage},

        {"metric": "needs_review_to_auto_approved_ratio", "value": needs_review_to_auto_ratio},

        {"metric": "clean_processed", "value": clean_count},
        {"metric": "noisy_processed", "value": noisy_count},

        {"metric": "total_processing_time_seconds", "value": round(total_processing_time_seconds, 2)},
        {"metric": "average_processing_time_seconds_per_pdf", "value": average_processing_time_seconds},
        {"metric": "estimated_remaining_time_seconds", "value": estimated_remaining_time_seconds},
        {"metric": "current_batch_runtime_seconds", "value": batch_duration_seconds if batch_duration_seconds is not None else ""},

        {"metric": "last_updated", "value": datetime.now().isoformat()},
    ]

    with open(SUMMARY_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(summary_rows)


def save_all_outputs(rows_by_file, total_pdf_count, batch_duration_seconds=None):
    save_results_csv(rows_by_file)
    save_manual_review_csv(rows_by_file)
    save_summary_csv(rows_by_file, total_pdf_count, batch_duration_seconds)
    save_status_statistics_csv(rows_by_file)


def get_ocr_text(pdf_blob_name, file_name):
    os.makedirs(OCR_CACHE_FOLDER, exist_ok=True)

    cache_path = get_ocr_cache_path(file_name)

    if USE_OCR_CACHE and not FORCE_REFRESH_OCR and os.path.exists(cache_path):
        print(f"OCR source: cache - {cache_path}")

        with open(cache_path, "r", encoding="utf-8", errors="replace") as file:
            return file.read()

    print("OCR source: Document AI")

    local_pdf_path = download_blob_to_temp(BUCKET_NAME, pdf_blob_name)

    last_error = None

    for attempt in range(1, 4):
        try:
            document = process_pdf_with_document_ai(
                project_id=PROJECT_ID,
                location=LOCATION,
                processor_id=PROCESSOR_ID,
                file_path=local_pdf_path,
            )

            raw_text = document.text or ""

            with open(cache_path, "w", encoding="utf-8") as file:
                file.write(raw_text)

            print(f"OCR cache saved: {cache_path}")
            return raw_text

        except Exception as error:
            last_error = error
            print(f"Document AI attempt {attempt} failed: {error}")

            if attempt < 3:
                time.sleep(attempt * 5)

    raise last_error


def process_pdf(pdf_blob_name):
    file_start_time = time.perf_counter()

    file_name = os.path.basename(pdf_blob_name)
    file_type = get_file_type(file_name)

    print("\n" + "=" * 100)
    print(f"PROCESSING PDF: {file_name}")
    print("=" * 100)

    raw_text = get_ocr_text(pdf_blob_name, file_name)

    parsed_fields = parse_w2_document(raw_text)
    validation_result = validate_extracted_fields(parsed_fields, raw_text)

    processing_time_seconds = round(time.perf_counter() - file_start_time, 2)

    row = {
        "processed_at": datetime.now().isoformat(),
        "processing_time_seconds": processing_time_seconds,
        "file_name": file_name,
        "file_type": file_type,
        "employee_name": parsed_fields.get("employee_name"),
        "employee_address": parsed_fields.get("employee_address"),
        "employee_ssn": parsed_fields.get("employee_ssn"),
        "employer_name": parsed_fields.get("employer_name"),
        "employer_address": parsed_fields.get("employer_address"),
        "employer_ein": parsed_fields.get("employer_ein"),
        "name_confidence": validation_result.get("name_confidence"),
        "address_confidence": validation_result.get("address_confidence"),
        "id_confidence": validation_result.get("id_confidence"),
        "overall_confidence": validation_result.get("overall_confidence"),
        "status": validation_result.get("status"),
        "review_reason": validation_result.get("review_reason"),
    }

    print(f"employee_name:    {row['employee_name']}")
    print(f"employee_address: {row['employee_address']}")
    print(f"employee_ssn:     {row['employee_ssn']}")
    print(f"status:           {row['status']}")
    print(f"review_reason:    {row['review_reason']}")
    print(f"time processed:   {processing_time_seconds} seconds")

    return row


def upload_outputs_to_gcs():
    files_to_upload = [
        (ALL_RESULTS_CSV, f"{OUTPUT_FOLDER}/extracted_all_results.csv"),
        (MANUAL_REVIEW_CSV, f"{OUTPUT_FOLDER}/manual_review_records.csv"),
        (SUMMARY_CSV, f"{OUTPUT_FOLDER}/full_processing_summary.csv"),
        (STATUS_STATS_CSV, f"{OUTPUT_FOLDER}/status_statistics.csv"),
    ]

    for local_path, gcs_path in files_to_upload:
        if os.path.exists(local_path):
            gcs_uri = upload_file_to_gcs(BUCKET_NAME, local_path, gcs_path)
            print(f"Uploaded: {gcs_uri}")


def create_bigquery_dataset_if_needed():
    client = bigquery.Client(project=PROJECT_ID)

    dataset_id = f"{PROJECT_ID}.{BIGQUERY_DATASET_ID}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = BIGQUERY_LOCATION

    try:
        client.get_dataset(dataset_id)
        print(f"BigQuery dataset exists: {dataset_id}")

    except NotFound:
        client.create_dataset(dataset)
        print(f"BigQuery dataset created: {dataset_id}")


def load_csv_to_bigquery(local_csv_path, table_name, schema):
    if not os.path.exists(local_csv_path):
        print(f"Skipped BigQuery load. File not found: {local_csv_path}")
        return

    client = bigquery.Client(project=PROJECT_ID)

    table_id = f"{PROJECT_ID}.{BIGQUERY_DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )

    with open(local_csv_path, "rb") as source_file:
        load_job = client.load_table_from_file(
            source_file,
            table_id,
            job_config=job_config,
        )

    load_job.result()

    table = client.get_table(table_id)

    print(f"Loaded {table.num_rows} row(s) to BigQuery table: {table_id}")


def save_outputs_to_bigquery():
    if not SAVE_TO_BIGQUERY:
        print("BigQuery saving is disabled.")
        return

    create_bigquery_dataset_if_needed()

    results_schema = [
        bigquery.SchemaField("processed_at", "STRING"),
        bigquery.SchemaField("processing_time_seconds", "FLOAT"),
        bigquery.SchemaField("file_name", "STRING"),
        bigquery.SchemaField("file_type", "STRING"),
        bigquery.SchemaField("employee_name", "STRING"),
        bigquery.SchemaField("employee_address", "STRING"),
        bigquery.SchemaField("employee_ssn", "STRING"),
        bigquery.SchemaField("employer_name", "STRING"),
        bigquery.SchemaField("employer_address", "STRING"),
        bigquery.SchemaField("employer_ein", "STRING"),
        bigquery.SchemaField("name_confidence", "FLOAT"),
        bigquery.SchemaField("address_confidence", "FLOAT"),
        bigquery.SchemaField("id_confidence", "FLOAT"),
        bigquery.SchemaField("overall_confidence", "FLOAT"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("review_reason", "STRING"),
    ]

    summary_schema = [
        bigquery.SchemaField("metric", "STRING"),
        bigquery.SchemaField("value", "STRING"),
    ]

    status_stats_schema = [
        bigquery.SchemaField("section", "STRING"),
        bigquery.SchemaField("file_type", "STRING"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("total", "STRING"),
        bigquery.SchemaField("percentage", "STRING"),
        bigquery.SchemaField("ratio", "STRING"),
    ]

    load_csv_to_bigquery(
        ALL_RESULTS_CSV,
        BIGQUERY_RESULTS_TABLE_ID,
        results_schema,
    )

    load_csv_to_bigquery(
        MANUAL_REVIEW_CSV,
        BIGQUERY_MANUAL_REVIEW_TABLE_ID,
        results_schema,
    )

    load_csv_to_bigquery(
        SUMMARY_CSV,
        BIGQUERY_SUMMARY_TABLE_ID,
        summary_schema,
    )

    load_csv_to_bigquery(
        STATUS_STATS_CSV,
        BIGQUERY_STATUS_STATS_TABLE_ID,
        status_stats_schema,
    )


def main():
    batch_start_time = time.perf_counter()

    validate_config()

    os.makedirs(OUTPUT_FOLDER_LOCAL, exist_ok=True)
    os.makedirs(OCR_CACHE_FOLDER, exist_ok=True)

    print("Listing PDFs in Cloud Storage...")

    pdf_files = list_raw_pdfs(BUCKET_NAME, RAW_FOLDER)

    pdf_files = [
        pdf for pdf in pdf_files
        if pdf.lower().endswith(".pdf")
    ]

    pdf_files = sorted(pdf_files)

    print(f"Total PDFs found: {len(pdf_files)}")

    rows_by_file = load_existing_results()

    already_done = set()

    for file_name, row in rows_by_file.items():
        status = row.get("status", "")

        if status == "FAILED" and RETRY_FAILED:
            continue

        already_done.add(file_name)

    pending_pdfs = [
        pdf for pdf in pdf_files
        if os.path.basename(pdf) not in already_done
    ]

    if MAX_FILES_PER_RUN is not None:
        batch_pdfs = pending_pdfs[:MAX_FILES_PER_RUN]
    else:
        batch_pdfs = pending_pdfs

    print(f"Already processed: {len(already_done)}")
    print(f"Pending PDFs: {len(pending_pdfs)}")
    print(f"Processing this run: {len(batch_pdfs)}")

    if not batch_pdfs:
        print("\nNo pending PDFs left.")

        batch_duration_seconds = round(time.perf_counter() - batch_start_time, 2)

        save_all_outputs(
            rows_by_file,
            len(pdf_files),
            batch_duration_seconds,
        )

        upload_outputs_to_gcs()
        save_outputs_to_bigquery()
        return

    for pdf_blob_name in batch_pdfs:
        file_name = os.path.basename(pdf_blob_name)
        failed_start_time = time.perf_counter()

        try:
            row = process_pdf(pdf_blob_name)
            rows_by_file[file_name] = row

        except Exception as error:
            processing_time_seconds = round(time.perf_counter() - failed_start_time, 2)

            print(f"FAILED: {file_name}")
            print(f"Error: {error}")
            print(f"time processed: {processing_time_seconds} seconds")

            rows_by_file[file_name] = {
                "processed_at": datetime.now().isoformat(),
                "processing_time_seconds": processing_time_seconds,
                "file_name": file_name,
                "file_type": get_file_type(file_name),
                "employee_name": None,
                "employee_address": None,
                "employee_ssn": None,
                "employer_name": None,
                "employer_address": None,
                "employer_ein": None,
                "name_confidence": 0.0,
                "address_confidence": 0.0,
                "id_confidence": 0.0,
                "overall_confidence": 0.0,
                "status": "FAILED",
                "review_reason": str(error),
            }

        current_batch_runtime_seconds = round(time.perf_counter() - batch_start_time, 2)

        save_all_outputs(
            rows_by_file,
            len(pdf_files),
            current_batch_runtime_seconds,
        )

    batch_duration_seconds = round(time.perf_counter() - batch_start_time, 2)

    save_all_outputs(
        rows_by_file,
        len(pdf_files),
        batch_duration_seconds,
    )

    print("\nBatch completed.")
    print(f"Batch runtime: {batch_duration_seconds} seconds")
    print(f"Results CSV: {ALL_RESULTS_CSV}")
    print(f"Manual review CSV: {MANUAL_REVIEW_CSV}")
    print(f"Summary CSV: {SUMMARY_CSV}")
    print(f"Status statistics CSV: {STATUS_STATS_CSV}")

    upload_outputs_to_gcs()
    save_outputs_to_bigquery()

    print("\nCurrent summary:")
    with open(SUMMARY_CSV, "r", encoding="utf-8") as file:
        print(file.read())

    print("\nStatus statistics:")
    with open(STATUS_STATS_CSV, "r", encoding="utf-8") as file:
        print(file.read())


if __name__ == "__main__":
    main()