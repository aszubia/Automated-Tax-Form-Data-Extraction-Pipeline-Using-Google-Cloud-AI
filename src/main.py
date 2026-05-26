import os
import csv
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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


TEST_FILE_NAMES = [
    "W2_XL_input_clean_1000.pdf",
    "W2_XL_input_clean_1001.pdf",
    "W2_XL_input_clean_1002.pdf",
    "W2_XL_input_clean_1003.pdf",
    "W2_XL_input_clean_1004.pdf",
    "W2_XL_input_clean_1005.pdf",
    "W2_XL_input_clean_1006.pdf",
    "W2_XL_input_clean_1007.pdf",
    "W2_XL_input_clean_1008.pdf",
    "W2_XL_input_clean_1009.pdf",
    "W2_XL_input_clean_1010.pdf",

    "W2_XL_input_noisy_2536.pdf",
    "W2_XL_input_noisy_2908.pdf",
    "W2_XL_input_noisy_2909.pdf",
    "W2_XL_input_noisy_2910.pdf",
    "W2_XL_input_noisy_2911.pdf",
    "W2_XL_input_noisy_2913.pdf",
    "W2_XL_input_noisy_2915.pdf",
    "W2_XL_input_noisy_2916.pdf",
    "W2_XL_input_noisy_2917.pdf",
    "W2_XL_input_noisy_2918.pdf",
    "W2_XL_input_noisy_2919.pdf",
    "W2_XL_input_noisy_2920.pdf",
    "W2_XL_input_noisy_2921.pdf",
    "W2_XL_input_noisy_2922.pdf",
    "W2_XL_input_noisy_2923.pdf",
    "W2_XL_input_noisy_2924.pdf",
]


LOG_FILE_PATH = "sample_output/noisy_test_results.txt"
CSV_FILE_PATH = "sample_output/extracted_test_results.csv"

# Global lock to ensure thread-safe file writing and clean logs
LOG_LOCK = threading.Lock()


def write_log(message, log_file):
    with LOG_LOCK:
        print(message)
        log_file.write(message + "\n")


def get_file_type(file_name):
    if "clean" in file_name.lower():
        return "clean"
    if "noisy" in file_name.lower():
        return "noisy"
    return "unknown"


def process_test_pdf(pdf_blob_name: str, log_file):
    """
    Test-only processing:
    - Downloads one PDF
    - Sends original PDF directly to Document AI
    - Runs parser
    - Runs validation
    - Returns one dictionary row for CSV output
    """
    file_name = os.path.basename(pdf_blob_name)
    file_type = get_file_type(file_name)

    write_log("\n" + "=" * 100, log_file)
    write_log(f"TESTING PDF: {file_name}", log_file)
    write_log("=" * 100, log_file)

    local_pdf_path = download_blob_to_temp(BUCKET_NAME, pdf_blob_name)

    document = process_pdf_with_document_ai(
        project_id=PROJECT_ID,
        location=LOCATION,
        processor_id=PROCESSOR_ID,
        file_path=local_pdf_path,
    )

    raw_text = document.text or ""

    parsed_fields = parse_w2_document(raw_text)
    validation_result = validate_extracted_fields(parsed_fields, raw_text)

    # Clean multi-line log chunk assembled before locking to optimize speed
    log_chunk = (
        f"\nExtracted fields for {file_name}:\n"
        f"{'-' * 100}\n"
        f"employee_name:    {parsed_fields.get('employee_name')}\n"
        f"employee_address: {parsed_fields.get('employee_address')}\n"
        f"employee_ssn:     {parsed_fields.get('employee_ssn')}\n"
        f"employer_name:    {parsed_fields.get('employer_name')}\n"
        f"employer_address: {parsed_fields.get('employer_address')}\n"
        f"employer_ein:     {parsed_fields.get('employer_ein')}\n"
        f"{'-' * 100}\n"
        f"\nValidation result for {file_name}:\n"
        f"{'-' * 100}\n"
        f"name_confidence:    {validation_result.get('name_confidence')}\n"
        f"address_confidence: {validation_result.get('address_confidence')}\n"
        f"id_confidence:      {validation_result.get('id_confidence')}\n"
        f"overall_confidence: {validation_result.get('overall_confidence')}\n"
        f"status:             {validation_result.get('status')}\n"
        f"review_reason:      {validation_result.get('review_reason')}\n"
        f"{'-' * 100}"
    )
    write_log(log_chunk, log_file)

    # Clean up local temp file to avoid clogging disk space during concurrent runs
    try:
        os.remove(local_pdf_path)
    except Exception:
        pass

    return {
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


def write_csv_output(rows):
    os.makedirs("sample_output", exist_ok=True)

    fieldnames = [
        "file_name", "file_type", "employee_name", "employee_address",
        "employee_ssn", "employer_name", "employer_address", "employer_ein",
        "name_confidence", "address_confidence", "id_confidence",
        "overall_confidence", "status", "review_reason",
    ]

    with open(CSV_FILE_PATH, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    validate_config()
    os.makedirs("sample_output", exist_ok=True)

    # Dictionary to maintain consistent sorting after concurrent processing finishes
    threaded_results_map = {}

    with open(LOG_FILE_PATH, "w", encoding="utf-8") as log_file:
        write_log("PDF Parser Test Results - Extracted Fields and Validation Only", log_file)
        write_log(f"Generated at: {datetime.now().isoformat()}", log_file)
        write_log(f"Bucket: {BUCKET_NAME}", log_file)
        write_log(f"Folder: {RAW_FOLDER}/", log_file)
        write_log("Preprocessing: DISABLED", log_file)
        write_log("=" * 100, log_file)

        write_log("\nChecking PDF files in Cloud Storage...", log_file)
        pdf_files = list_raw_pdfs(BUCKET_NAME, RAW_FOLDER)
        write_log(f"\nFound {len(pdf_files)} PDF file(s).", log_file)

        selected_pdfs = sorted([p for p in pdf_files if os.path.basename(p) in TEST_FILE_NAMES])

        if not selected_pdfs:
            write_log("\nNo matching test PDFs found.", log_file)
            return

        write_log("\nSelected PDFs for testing:", log_file)
        for pdf in selected_pdfs:
            write_log(f"- {pdf}", log_file)

        write_log(f"\nStarting concurrent execution loop across threads...", log_file)

        # Optimization: Concurrently manage idle I/O network wait blocks
        # 5 to 8 workers is standard to avoid API quota rate limits
        max_workers = min(6, len(selected_pdfs))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map futures to their associated blob tracking keys
            future_to_pdf = {executor.submit(process_test_pdf, pdf, log_file): pdf for pdf in selected_pdfs}
            
            for future in as_completed(future_to_pdf):
                pdf_blob_name = future_to_pdf[future]
                file_name = os.path.basename(pdf_blob_name)
                try:
                    row_data = future.result()
                    threaded_results_map[file_name] = row_data
                except Exception as error:
                    write_log("\n" + "=" * 100, log_file)
                    write_log(f"FAILED PDF FUTURE THREAD: {file_name}", log_file)
                    write_log("=" * 100, log_file)
                    write_log(f"Error: {error}", log_file)

                    threaded_results_map[file_name] = {
                        "file_name": file_name,
                        "file_type": get_file_type(file_name),
                        "employee_name": None, "employee_address": None, "employee_ssn": None,
                        "employer_name": None, "employer_address": None, "employer_ein": None,
                        "name_confidence": 0.0, "address_confidence": 0.0, "id_confidence": 0.0,
                        "overall_confidence": 0.0, "status": "FAILED", "review_reason": str(error),
                    }

        # Ensure the final CSV rows follow the original alphabetized sorting order
        sorted_extracted_rows = [threaded_results_map[os.path.basename(p)] for p in selected_pdfs if os.path.basename(p) in threaded_results_map]
        
        write_csv_output(sorted_extracted_rows)

        write_log("\n" + "=" * 100, log_file)
        write_log("Test run completed.", log_file)
        write_log(f"Local text log file: {LOG_FILE_PATH}", log_file)
        write_log(f"Local CSV output file: {CSV_FILE_PATH}", log_file)

    txt_gcs_uri = upload_file_to_gcs(BUCKET_NAME, LOG_FILE_PATH, f"{OUTPUT_FOLDER}/noisy_test_results.txt")
    csv_gcs_uri = upload_file_to_gcs(BUCKET_NAME, CSV_FILE_PATH, f"{OUTPUT_FOLDER}/extracted_test_results.csv")

    print(f"\nText log created:\n{LOG_FILE_PATH}\n\nUploaded to:\n{txt_gcs_uri}")
    print(f"\nCSV output created:\n{CSV_FILE_PATH}\n\nUploaded to:\n{csv_gcs_uri}")


if __name__ == "__main__":
    main()