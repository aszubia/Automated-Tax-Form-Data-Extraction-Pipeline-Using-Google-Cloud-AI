import os
import tempfile
from google.cloud import storage


def list_raw_pdfs(bucket_name: str, raw_folder: str = "raw"):
    """
    Lists all PDF files inside the raw/ folder of the Cloud Storage bucket.
    """

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    prefix = raw_folder.rstrip("/") + "/"
    blobs = bucket.list_blobs(prefix=prefix)

    pdf_files = []

    for blob in blobs:
        if blob.name.lower().endswith(".pdf"):
            pdf_files.append(blob.name)

    return sorted(pdf_files)


def download_blob_to_temp(bucket_name: str, blob_name: str):
    """
    Downloads a Cloud Storage PDF file to a temporary local file.
    Returns the local file path.
    """

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    file_name = os.path.basename(blob_name)

    temp_dir = tempfile.gettempdir()
    local_path = os.path.join(temp_dir, file_name)

    blob.download_to_filename(local_path)

    return local_path


def upload_file_to_gcs(bucket_name: str, local_file_path: str, destination_blob_name: str):
    """
    Uploads a local file to Cloud Storage.
    """

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(local_file_path)

    return f"gs://{bucket_name}/{destination_blob_name}"