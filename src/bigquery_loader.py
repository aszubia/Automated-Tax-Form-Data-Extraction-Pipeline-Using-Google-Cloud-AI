import time

from google.api_core.exceptions import NotFound
from google.cloud import bigquery


TABLE_SCHEMA = [
    bigquery.SchemaField("file_name", "STRING"),
    bigquery.SchemaField("gcs_uri", "STRING"),
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
    bigquery.SchemaField("processed_at", "TIMESTAMP"),
    bigquery.SchemaField("raw_text", "STRING"),
]


def ensure_bigquery_table_exists(
    project_id: str,
    dataset_id: str,
    table_id: str,
    location: str = "US",
):
    """
    Creates the BigQuery dataset/table if missing.
    This prevents 'table not found' errors after resetting the table.
    """

    client = bigquery.Client(project=project_id)

    dataset_ref = f"{project_id}.{dataset_id}"
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    try:
        client.get_dataset(dataset_ref)
        print(f"BigQuery dataset exists: {dataset_ref}")
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        client.create_dataset(dataset)
        print(f"Created BigQuery dataset: {dataset_ref}")

    try:
        client.get_table(full_table_id)
        print(f"BigQuery table exists: {full_table_id}")
    except NotFound:
        table = bigquery.Table(full_table_id, schema=TABLE_SCHEMA)
        client.create_table(table)
        print(f"Created BigQuery table: {full_table_id}")


def insert_extraction_result(
    project_id: str,
    dataset_id: str,
    table_id: str,
    row_data: dict,
    max_retries: int = 5,
):
    """
    Inserts one extracted document result into BigQuery.
    Includes retry logic in case the table was just created.
    """

    client = bigquery.Client(project=project_id)
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    for attempt in range(1, max_retries + 1):
        try:
            errors = client.insert_rows_json(full_table_id, [row_data])

            if errors:
                raise RuntimeError(f"BigQuery insert failed: {errors}")

            return True

        except NotFound:
            if attempt == max_retries:
                raise

            print(
                f"BigQuery table not ready yet. Retrying insert "
                f"({attempt}/{max_retries})..."
            )
            time.sleep(3)

    return False


def file_already_processed(
    project_id: str,
    dataset_id: str,
    table_id: str,
    file_name: str,
):
    """
    Checks if a file has already been inserted into BigQuery.
    This helps avoid duplicate rows during testing.
    """

    client = bigquery.Client(project=project_id)

    query = f"""
        SELECT COUNT(*) AS row_count
        FROM `{project_id}.{dataset_id}.{table_id}`
        WHERE file_name = @file_name
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("file_name", "STRING", file_name)
        ]
    )

    try:
        result = client.query(query, job_config=job_config).result()

        for row in result:
            return row.row_count > 0

    except NotFound:
        return False

    return False


def fetch_extraction_results(
    project_id: str,
    dataset_id: str,
    table_id: str,
    limit: int = 1000,
):
    """
    Fetches extracted rows from BigQuery for CSV export.
    """

    client = bigquery.Client(project=project_id)

    query = f"""
        SELECT
            file_name,
            gcs_uri,
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
        FROM `{project_id}.{dataset_id}.{table_id}`
        ORDER BY file_name ASC
        LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("limit", "INT64", limit)
        ]
    )

    try:
        result = client.query(query, job_config=job_config).result()
    except NotFound:
        return []

    rows = []

    for row in result:
        rows.append(dict(row.items()))

    return rows