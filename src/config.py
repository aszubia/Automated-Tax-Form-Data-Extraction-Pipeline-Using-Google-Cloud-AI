import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
PROJECT_NUMBER = os.getenv("PROJECT_NUMBER")
LOCATION = os.getenv("LOCATION", "us")
PROCESSOR_ID = os.getenv("PROCESSOR_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")

RAW_FOLDER = os.getenv("RAW_FOLDER", "raw")
PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", "processed")
FAILED_FOLDER = os.getenv("FAILED_FOLDER", "failed")
OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", "output")

DATASET_ID = os.getenv("DATASET_ID", "taxform_extraction")
TABLE_ID = os.getenv("TABLE_ID", "extracted_tax_forms")


def validate_config():
    required_values = {
        "PROJECT_ID": PROJECT_ID,
        "PROJECT_NUMBER": PROJECT_NUMBER,
        "LOCATION": LOCATION,
        "PROCESSOR_ID": PROCESSOR_ID,
        "BUCKET_NAME": BUCKET_NAME,
        "DATASET_ID": DATASET_ID,
        "TABLE_ID": TABLE_ID,
    }

    missing = [key for key, value in required_values.items() if not value]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )