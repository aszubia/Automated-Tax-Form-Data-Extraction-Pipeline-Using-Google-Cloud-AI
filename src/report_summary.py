import pandas as pd
from google.cloud import bigquery

from config import PROJECT_ID, DATASET_ID, TABLE_ID, BUCKET_NAME, OUTPUT_FOLDER
from storage_client import upload_file_to_gcs


def run_query(query: str):
    client = bigquery.Client(project=PROJECT_ID)
    result = client.query(query).result()
    return [dict(row.items()) for row in result]


def create_report_outputs():
    full_table = f"`{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`"

    detail_query = f"""
        SELECT
            file_name,
            gcs_uri,
            CASE
                WHEN file_name LIKE '%clean%' THEN 'clean'
                WHEN file_name LIKE '%noisy%' THEN 'noisy'
                ELSE 'unknown'
            END AS file_type,
            employee_name,
            employee_address,
            employee_ssn,
            employer_name,
            employer_address,
            employer_ein,
            name_confidence,
            address_confidence,
            id_confidence,
            overall_confidence,
            status,
            review_reason,
            processed_at
        FROM {full_table}
        ORDER BY file_name
    """

    status_summary_query = f"""
        SELECT
            status,
            COUNT(*) AS total
        FROM {full_table}
        GROUP BY status
        ORDER BY status
    """

    pipeline_summary_query = f"""
        SELECT
            CASE
                WHEN file_name LIKE '%clean%' THEN 'clean'
                WHEN file_name LIKE '%noisy%' THEN 'noisy'
                ELSE 'unknown'
            END AS file_type,
            status,
            COUNT(*) AS total
        FROM {full_table}
        GROUP BY file_type, status
        ORDER BY file_type, status
    """

    detail_rows = run_query(detail_query)
    status_rows = run_query(status_summary_query)
    pipeline_rows = run_query(pipeline_summary_query)

    detail_path = "sample_output/extracted_tax_forms_preview.csv"
    status_path = "sample_output/status_summary.csv"
    pipeline_path = "sample_output/pipeline_summary.csv"

    pd.DataFrame(detail_rows).to_csv(detail_path, index=False)
    pd.DataFrame(status_rows).to_csv(status_path, index=False)
    pd.DataFrame(pipeline_rows).to_csv(pipeline_path, index=False)

    upload_file_to_gcs(
        BUCKET_NAME,
        detail_path,
        f"{OUTPUT_FOLDER}/extracted_tax_forms_preview.csv",
    )

    upload_file_to_gcs(
        BUCKET_NAME,
        status_path,
        f"{OUTPUT_FOLDER}/status_summary.csv",
    )

    upload_file_to_gcs(
        BUCKET_NAME,
        pipeline_path,
        f"{OUTPUT_FOLDER}/pipeline_summary.csv",
    )

    print("Report files created:")
    print(detail_path)
    print(status_path)
    print(pipeline_path)

    print("\nUploaded to Cloud Storage:")
    print(f"gs://{BUCKET_NAME}/{OUTPUT_FOLDER}/extracted_tax_forms_preview.csv")
    print(f"gs://{BUCKET_NAME}/{OUTPUT_FOLDER}/status_summary.csv")
    print(f"gs://{BUCKET_NAME}/{OUTPUT_FOLDER}/pipeline_summary.csv")


if __name__ == "__main__":
    create_report_outputs()