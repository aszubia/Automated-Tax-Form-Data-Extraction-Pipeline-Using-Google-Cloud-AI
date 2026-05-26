# Tax Form Extraction Pipeline

## 1. Project Overview

This project is a Google Cloud Platform based document extraction pipeline for scanned W-2 tax form PDFs.

The goal of this project is to reduce manual reading and encoding of customer tax form information into a structured data system. The pipeline ingests PDF files from Google Cloud Storage, extracts key customer fields using Google Document AI, validates the extracted results, and stores the structured output in BigQuery.

The required extracted fields are:
- Employee's name
- Employee's address
- Employee's identification number
- Employer identification number
- Employer name and address

For this practical exam, employee identification numbers are treated as customer identification numbers.

## 2. Problem Statement

Organizations that collect scanned or PDF tax forms often need to manually read each document and encode customer information into internal systems.

This manual process is:

- Time-consuming
- Repetitive
- Error-prone
- Difficult to scale as document volume increases

This project automates the extraction and validation of key tax form fields so that clean and complete documents can be auto-approved, while incomplete or noisy documents are routed for manual review.

## 3. System Design

## 4. GCP Services Used

This project uses the following Google Cloud Platform services:

| GCP Service | Purpose in the Project |
|---|---|
| Google Cloud Storage | Stores the input PDF tax forms in the `raw/` folder and stores generated CSV output files in the `output/` folder. |
| Google Document AI | Performs OCR/document extraction on the uploaded W-2 PDF tax forms. |
| BigQuery | Stores the structured extraction results, including extracted fields, validation status, confidence scores, review reasons, and raw OCR text. |
| Cloud Shell | Used as the development environment for writing and running the Python pipeline. |
| Cloud Shell Editor | Used to edit project files such as `main.py`, `parser.py`, `validation.py`, and `README.md`. |
| Application Default Credentials | Used to authenticate the Python scripts when accessing Cloud Storage, Document AI, and BigQuery. |

## 5. Project Folder Structure

The project is organized into separate folders for source code, generated outputs, SQL references, screenshots, architecture diagrams, and presentation files. This structure makes the pipeline easier to understand, reproduce, and maintain.

```text
firstgen-taxform-extraction/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── src/
│   ├── config.py
│   ├── storage_client.py
│   ├── document_ai_client.py
│   ├── parser.py
│   ├── validation.py
│   ├── main.py
│   ├── evaluate_accuracy.py
│   └── process_all_pdfs.py
│
├── sample_output/
│   ├── extracted_test_results.csv
│   ├── validation_results.csv
│   ├── failed_fields.csv
│   ├── accuracy_summary.csv
│   ├── extracted_all_results.csv
│   ├── manual_review_records.csv
│   ├── full_processing_summary.csv
│   └── status_statistics.csv
│
├── sql/
│   └── sample_bigquery_queries.sql
│
├── screenshots/
│   ├── cloud_storage_raw_folder.png
│   ├── document_ai_processor.png
│   ├── bigquery_tables.png
│   └── output_files.png
│
├── architecture/
│   └── pipeline_architecture.png
│
└── presentation/
    └── tax_form_extraction_presentation.pdf
```

### File and Folder Definitions

| File / Folder | Definition |
|---|---|
| `README.md` | Main project documentation. It explains the project objective, architecture, setup instructions, validation logic, accuracy results, and full processing results. |
| `requirements.txt` | List of Python packages required to run the project. This allows the environment to be recreated using `pip install -r requirements.txt`. |
| `.gitignore` | Specifies files and folders that should not be committed, such as virtual environments, cache files, and temporary output folders. |
| `.env.example` | Template file showing the required environment variables, such as GCP project ID, bucket name, Document AI location, and processor ID. |
| `src/` | Contains all Python source code used by the extraction pipeline. |
| `src/config.py` | Loads and validates project configuration values used by the pipeline. |
| `src/storage_client.py` | Handles Google Cloud Storage operations, including listing PDFs, downloading files, and uploading output files. |
| `src/document_ai_client.py` | Sends PDF files to Google Document AI and returns OCR text for parsing. |
| `src/parser.py` | Extracts structured fields from OCR text, including employee/customer name, address, identification number, employer name, employer address, and employer EIN. |
| `src/validation.py` | Applies field validation rules and confidence scoring. It determines whether a record is `AUTO_APPROVED` or `NEEDS_REVIEW`. |
| `src/main.py` | Runs test extraction on selected PDFs and generates test output files. This is mainly used during development and accuracy testing. |
| `src/evaluate_accuracy.py` | Compares extracted test results against the manually checked ground truth and calculates accuracy, failed fields, and precision metrics. |
| `src/process_all_pdfs.py` | Processes the full dataset in batches. It saves results to CSV, uploads outputs to Cloud Storage, loads tables into BigQuery, and generates processing statistics. |
| `sample_output/` | Contains generated output files from testing, validation, full processing, and statistics generation. |
| `sample_output/extracted_test_results.csv` | Extracted results from the manually tested sample PDFs. |
| `sample_output/validation_results.csv` | Field-by-field comparison between extracted values and manually checked ground truth values. |
| `sample_output/failed_fields.csv` | List of fields that failed during accuracy evaluation, including expected and extracted values. |
| `sample_output/accuracy_summary.csv` | Summary of field-level accuracy, clean accuracy, noisy accuracy, and auto-approval precision. |
| `sample_output/extracted_all_results.csv` | Full extraction output for all processed PDFs. Each row represents one processed PDF. |
| `sample_output/manual_review_records.csv` | Subset of records that were not auto-approved and require manual review. |
| `sample_output/full_processing_summary.csv` | Overall processing summary, including total PDFs processed, remaining PDFs, auto-approved count, needs-review count, failed count, and processing time. |
| `sample_output/status_statistics.csv` | Status distribution summary showing `AUTO_APPROVED`, `NEEDS_REVIEW`, and `FAILED` counts and percentages. |
| `sql/` | Contains sample SQL queries for analyzing the output tables in BigQuery. |
| `sql/sample_bigquery_queries.sql` | Sample BigQuery queries for checking status counts, manual review records, and processing-time statistics. |
| `screenshots/` | Contains screenshots used as documentation evidence, such as Cloud Storage, Document AI, BigQuery, and output files. |
| `architecture/` | Contains the project architecture diagram showing the full extraction pipeline. |
| `presentation/` | Contains the final presentation slides or exported PDF used for the project presentation. |

## 6. GCP Services Used

This project uses Google Cloud Platform services to support document ingestion, OCR extraction, structured storage, and output reporting.

| GCP Service | Purpose in the Project |
|---|---|
| Google Cloud Storage | Stores the input PDF tax forms in the `raw/` folder and stores generated output files in the `output/` folder. |
| Google Document AI | Performs OCR and document text extraction from the PDF tax forms. |
| BigQuery | Stores the structured extraction results, manual review records, summary statistics, and status distribution tables. |
| Cloud Shell | Used as the development and execution environment for running Python scripts and managing GCP resources. |

The pipeline starts by reading PDF files from Cloud Storage, sends each file to Document AI for OCR, parses the extracted text using Python, validates the extracted fields, and stores the final structured results in both CSV files and BigQuery tables.

## 7. Environment Configuration

The project uses environment variables to store configuration values such as the GCP project ID, Cloud Storage bucket name, Document AI processor details, and output folder paths.

Create a `.env` file based on `.env.example`.

```env
PROJECT_ID=your-gcp-project-id
LOCATION=us
PROCESSOR_ID=your-document-ai-processor-id
BUCKET_NAME=your-cloud-storage-bucket
RAW_FOLDER=raw
OUTPUT_FOLDER=output
```

### Configuration Variables

| Variable | Description |
|---|---|
| `PROJECT_ID` | Google Cloud project ID used by the pipeline. |
| `LOCATION` | Document AI processor location, such as `us`. |
| `PROCESSOR_ID` | ID of the Document AI processor used for OCR extraction. |
| `BUCKET_NAME` | Cloud Storage bucket containing the input PDFs and output files. |
| `RAW_FOLDER` | Folder in Cloud Storage where the raw PDF files are stored. |
| `OUTPUT_FOLDER` | Folder in Cloud Storage where generated CSV outputs are uploaded. |

## 8. Pipeline Workflow and Architecture

The pipeline follows an end-to-end workflow that starts from PDF ingestion and ends with structured outputs for reporting, review, and storage.

```text
PDF Tax Forms
Cloud Storage raw/
        ↓
Google Document AI
OCR and text extraction
        ↓
Python Parser
Field extraction from OCR text
        ↓
Validation Logic
Confidence scoring and completeness checks
        ↓
BigQuery Tables
Structured storage and analysis
        ↓
CSV Outputs
Reporting and manual review files
```

### Workflow Steps

| Step | Process | Description |
|---|---|---|
| 1 | PDF Upload | Tax form PDFs are stored in the Google Cloud Storage `raw/` folder. |
| 2 | OCR Extraction | Google Document AI reads each PDF and converts the document content into OCR text. |
| 3 | Field Parsing | The Python parser extracts required fields such as employee/customer name, address, identification number, employer name, employer address, and employer EIN. |
| 4 | Field Validation | The validation script checks whether extracted fields are complete, correctly formatted, and reliable enough for auto-approval. |
| 5 | Status Assignment | Each record is assigned either `AUTO_APPROVED`, `NEEDS_REVIEW`, or `FAILED`. |
| 6 | Structured Output | Extracted records are saved to CSV files and loaded into BigQuery tables. |
| 7 | Manual Review Output | Records that do not pass validation are separated into a manual review CSV file. |
| 8 | Statistics Generation | The pipeline generates summary statistics, including auto-approved count, needs-review count, failed count, percentages, and processing time. |

### Status Definitions

| Status | Meaning |
|---|---|
| `AUTO_APPROVED` | The required fields passed validation and are considered complete and reliable. |
| `NEEDS_REVIEW` | One or more required fields are missing, incomplete, uncertain, or did not pass validation rules. |
| `FAILED` | The PDF could not be processed due to an error such as timeout, API failure, or unexpected pipeline issue. |

## 9. Extracted Fields and Output Schema

The pipeline extracts customer-related and employer-related fields from each tax form PDF. For this project, employee information is treated as customer information based on the exam instruction.

### Extracted Fields

| Field | Description |
|---|---|
| `file_name` | Name of the processed PDF file. |
| `file_type` | Type of document based on filename, such as `clean` or `noisy`. |
| `employee_name` | Extracted employee/customer name from the tax form. |
| `employee_address` | Extracted employee/customer address, including street, city, state, and ZIP code when available. |
| `employee_ssn` | Extracted employee/customer identification number. |
| `employer_name` | Extracted employer name from the tax form. |
| `employer_address` | Extracted employer address. |
| `employer_ein` | Extracted employer identification number. |
| `name_confidence` | Confidence score assigned to the extracted employee/customer name. |
| `address_confidence` | Confidence score assigned to the extracted employee/customer address. |
| `id_confidence` | Confidence score assigned to the extracted employee/customer identification number. |
| `overall_confidence` | Average confidence score across required customer fields. |
| `status` | Final processing status: `AUTO_APPROVED`, `NEEDS_REVIEW`, or `FAILED`. |
| `review_reason` | Explanation of why the record was auto-approved, sent for review, or failed. |
| `processing_time_seconds` | Time taken to process each PDF file. |

### Required Customer Fields

The main fields used for validation and auto-approval are:

```text
employee_name
employee_address
employee_ssn
```

A record is only marked as `AUTO_APPROVED` when these required fields are complete and pass validation rules.

### Output Table Schema

The full extraction output is saved in:

```text
sample_output/extracted_all_results.csv
```

and loaded into BigQuery as:

```text
tax_form_extraction.extracted_all_results
```

Each row represents one processed PDF file.

## 10. Validation Logic and Confidence Thresholds

After the parser extracts fields from the OCR text, the validation layer checks whether the required customer fields are complete, properly formatted, and reliable enough for automatic approval.

The validation step focuses on the three required customer fields:

```text
employee_name
employee_address
employee_ssn
```

### Validation Rules

| Field | Validation Rule |
|---|---|
| `employee_name` | Must contain a valid person-like name with at least two name parts. Company-like names and OCR noise are rejected. |
| `employee_address` | Must contain a street number, street/address term, city, state abbreviation, and ZIP code. |
| `employee_ssn` | Must follow the expected identification number format: `###-##-####`. |
| `overall_confidence` | Computed from the name, address, and ID confidence scores. |

### Confidence Thresholds

The project uses rule-based confidence thresholds to decide whether a record can be automatically approved.

| Confidence Field | Threshold |
|---|---:|
| `name_confidence` | 0.90 |
| `address_confidence` | 0.90 |
| `id_confidence` | 0.90 |
| `overall_confidence` | 0.90 |

A record is marked as `AUTO_APPROVED` only when all required fields meet the minimum confidence threshold.

### Status Assignment

| Status | Condition |
|---|---|
| `AUTO_APPROVED` | All required customer fields are complete and pass validation rules. |
| `NEEDS_REVIEW` | One or more required fields are missing, incomplete, uncertain, or below the confidence threshold. |
| `FAILED` | The file could not be processed due to an error, timeout, or unexpected issue. |

### Example

```text
employee_name: April Hensley
employee_address: 31403 David Circles Suite 863 West Erinfort WY 45881-3334
employee_ssn: 077-49-4905
status: AUTO_APPROVED
```

If a field is incomplete, the record is routed for review:

```text
employee_name: Brian Thompson
employee_address: NOT_VERIFIABLE
employee_ssn: 401-09-3931
status: NEEDS_REVIEW
review_reason: Missing or incomplete customer field(s): employee_address
```

This validation step helps prevent incomplete or uncertain OCR results from being automatically accepted.

## 11. How to Run the Project

This section explains how to set up the environment, run test extraction, evaluate accuracy, and process the full PDF dataset in batches.

### 1. Clone or open the project folder

```bash
cd ~/firstgen-taxform-extraction
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If spaCy is used by the parser, install the English model:

```bash
python -m spacy download en_core_web_sm
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`.

```bash
cp .env.example .env
```

Update the values inside `.env`:

```env
PROJECT_ID=your-gcp-project-id
LOCATION=us
PROCESSOR_ID=your-document-ai-processor-id
BUCKET_NAME=your-cloud-storage-bucket
RAW_FOLDER=raw
OUTPUT_FOLDER=output
```

### 5. Run test extraction

Use `main.py` to test selected PDFs and generate test extraction outputs.

```bash
python src/main.py
```

This creates:

```text
sample_output/extracted_test_results.csv
sample_output/noisy_test_results.txt
```

### 6. Evaluate accuracy using manual ground truth

After running the test extraction, run:

```bash
python src/evaluate_accuracy.py
```

This creates:

```text
sample_output/validation_results.csv
sample_output/failed_fields.csv
sample_output/accuracy_summary.csv
```

### 7. Process the full dataset in batches

Use `process_all_pdfs.py` to process all PDF files from Cloud Storage.

```bash
python src/process_all_pdfs.py
```

The script processes a fixed number of pending PDFs per run, based on the batch setting:

```python
MAX_FILES_PER_RUN = 50
```

Run the same command repeatedly until all PDFs are processed:

```bash
python src/process_all_pdfs.py
```

Check progress using:

```bash
cat sample_output/full_processing_summary.csv
```

When the full run is complete, the value of `remaining_pdfs` should be `0`.

### 8. View output files

The full processing script creates the following output files:

```text
sample_output/extracted_all_results.csv
sample_output/manual_review_records.csv
sample_output/full_processing_summary.csv
sample_output/status_statistics.csv
```

### 9. BigQuery output

The full processing script also loads the results into BigQuery tables:

```text
tax_form_extraction.extracted_all_results
tax_form_extraction.manual_review_records
tax_form_extraction.full_processing_summary
tax_form_extraction.status_statistics
```

### 10. Cloud Storage output

Generated CSV outputs are uploaded to the Cloud Storage `output/` folder:

```text
gs://<bucket-name>/output/extracted_all_results.csv
gs://<bucket-name>/output/manual_review_records.csv
gs://<bucket-name>/output/full_processing_summary.csv
gs://<bucket-name>/output/status_statistics.csv
```

## 12. Output Files and BigQuery Tables

The pipeline generates CSV outputs locally, uploads them to Google Cloud Storage, and loads the structured results into BigQuery for querying and reporting.

### Local Output Files

Generated files are saved in the `sample_output/` folder.

| Output File | Description |
|---|---|
| `extracted_test_results.csv` | Contains extracted fields and validation results from selected test PDFs. |
| `validation_results.csv` | Contains field-by-field comparison between extracted values and manually checked ground truth values. |
| `failed_fields.csv` | Lists fields that failed during accuracy evaluation, including expected and extracted values. |
| `accuracy_summary.csv` | Summarizes field-level accuracy, clean accuracy, noisy accuracy, and auto-approval precision. |
| `extracted_all_results.csv` | Contains the full extraction output for all processed PDFs. Each row represents one PDF. |
| `manual_review_records.csv` | Contains records that were not auto-approved and require manual checking. |
| `full_processing_summary.csv` | Contains overall processing statistics such as total processed files, remaining files, approval counts, and processing time. |
| `status_statistics.csv` | Shows the distribution of `AUTO_APPROVED`, `NEEDS_REVIEW`, and `FAILED` records by file type. |

### Cloud Storage Output

The generated CSV files are uploaded to the Cloud Storage `output/` folder.

```text
gs://<bucket-name>/output/extracted_all_results.csv
gs://<bucket-name>/output/manual_review_records.csv
gs://<bucket-name>/output/full_processing_summary.csv
gs://<bucket-name>/output/status_statistics.csv
```

### BigQuery Tables

The full processing script loads the generated outputs into the following BigQuery tables:

| BigQuery Table | Description |
|---|---|
| `tax_form_extraction.extracted_all_results` | Main structured output table containing extracted fields, confidence scores, statuses, and processing time. |
| `tax_form_extraction.manual_review_records` | Contains only records that require manual review. |
| `tax_form_extraction.full_processing_summary` | Contains summary metrics for the full processing run. |
| `tax_form_extraction.status_statistics` | Contains auto-approval, needs-review, and failed-status statistics. |

### Example BigQuery Query

```sql
SELECT
  status,
  COUNT(*) AS total,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM `project-64d84820-2c87-46af-aa0.tax_form_extraction.extracted_all_results`
GROUP BY status
ORDER BY total DESC;
```

This query summarizes how many records were auto-approved, routed for review, or failed during processing.

## 13. Accuracy and Evaluation Results

The extraction pipeline was evaluated using a manually checked ground truth sample. Each PDF was checked at the field level using the required customer fields:

```text
employee_name
employee_address
employee_ssn
```

Each PDF has three field-level checks. Fields marked as `NOT_VERIFIABLE` were excluded from the accuracy calculation because they could not be confidently confirmed during manual checking.

### Accuracy Formula

```text
Accuracy = Pass / (Pass + Fail)
```

Where:

| Term | Meaning |
|---|---|
| `Pass` | The extracted field matched the manually checked ground truth. |
| `Fail` | The extracted field did not match the manually checked ground truth. |
| `NOT_VERIFIABLE` | The field could not be manually confirmed and was excluded from the denominator. |

### Evaluation Summary

| Metric | Result |
|---|---:|
| Total manually checked PDFs | 27 |
| Total field checks | 81 |
| Verifiable fields | 77 |
| Not verifiable fields | 4 |
| Field-level accuracy | XX.XX% |
| Clean field-level accuracy | XX.XX% |
| Noisy field-level accuracy | XX.XX% |
| Auto-approval precision | XX.XX% |

### Auto-Approval Precision

Auto-approval precision measures how reliable the system is when it marks a record as `AUTO_APPROVED`.

```text
Auto-approval precision = Correct AUTO_APPROVED fields / All AUTO_APPROVED verifiable fields
```

This metric is important because the pipeline is designed to automatically approve only records that are complete and reliable, while uncertain records are routed to manual review.

### Evaluation Output Files

The following files are generated by `evaluate_accuracy.py`:

| File | Description |
|---|---|
| `validation_results.csv` | Field-by-field comparison of expected and extracted values. |
| `failed_fields.csv` | List of failed fields with expected value, extracted value, status, and review reason. |
| `accuracy_summary.csv` | Summary of accuracy, clean/noisy performance, and auto-approval precision. |

### Notes on Noisy Documents

Noisy or partially cut-off PDFs may produce missing or uncertain OCR results. In these cases, the pipeline is designed to assign `NEEDS_REVIEW` instead of forcing an unreliable extraction. This helps reduce the risk of incorrect records being automatically accepted.

## 14. Full Dataset Processing Results

After validating the extraction logic on the manually checked sample, the full dataset was processed in batches using `process_all_pdfs.py`.

The batch processing script automatically skips files that were already processed and continues with the next pending PDFs. This makes the full extraction run resumable and safer for longer processing sessions.

### Full Processing Output

The full processing run generates the following main files:

| Output File | Description |
|---|---|
| `extracted_all_results.csv` | Contains extracted fields, confidence scores, status, review reason, and processing time for each processed PDF. |
| `manual_review_records.csv` | Contains only records marked as `NEEDS_REVIEW` or `FAILED`. |
| `full_processing_summary.csv` | Contains total processed files, remaining files, status counts, percentages, and processing time statistics. |
| `status_statistics.csv` | Contains `AUTO_APPROVED`, `NEEDS_REVIEW`, and `FAILED` distribution by file type. |

### Processing Summary

Replace the values below after completing all batches.

| Metric | Result |
|---|---:|
| Total PDFs found | 481 |
| Total PDFs processed | ___ |
| Remaining PDFs | ___ |
| Auto-approved records | ___ |
| Needs-review records | ___ |
| Failed records | ___ |
| Auto-approved percentage | ___% |
| Needs-review percentage | ___% |
| Failed percentage | ___% |
| Average processing time per PDF | ___ seconds |
| Total processing time | ___ seconds |

### Status Interpretation

| Status | Meaning |
|---|---|
| `AUTO_APPROVED` | The record passed validation and contains complete required customer fields. |
| `NEEDS_REVIEW` | The record was processed, but one or more required fields were missing, incomplete, uncertain, or below the validation threshold. |
| `FAILED` | The file could not be processed due to timeout, API issue, or another processing error. |

### Batch Processing Notes

The full dataset was processed in batches to make the run more manageable and fault-tolerant.

```text
MAX_FILES_PER_RUN = 50
```

After each batch, the script updates the local CSV files, uploads outputs to Cloud Storage, and refreshes the BigQuery tables using the latest consolidated results.

### BigQuery Result Tables

The processed results are also stored in BigQuery:

```text
tax_form_extraction.extracted_all_results
tax_form_extraction.manual_review_records
tax_form_extraction.full_processing_summary
tax_form_extraction.status_statistics
```

These tables can be used to analyze extraction results, monitor manual review volume, and summarize processing performance.
