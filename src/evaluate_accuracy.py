import csv
import os
import re
from difflib import SequenceMatcher


GROUND_TRUTH_CSV = "sample_output/manual_ground_truth.csv"
EXTRACTED_RESULTS_CSV = "sample_output/extracted_test_results.csv"

VALIDATION_RESULTS_CSV = "sample_output/validation_results.csv"
ACCURACY_SUMMARY_CSV = "sample_output/accuracy_summary.csv"
FAILED_FIELDS_CSV = "sample_output/failed_fields.csv"


FIELDS_TO_CHECK = [
    "employee_name",
    "employee_address",
    "employee_ssn",
]


US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def normalize_value(value):
    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in {"none", "null", "nan"}:
        return ""

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def extract_state(value):
    if not value:
        return ""

    parts = value.replace(",", " ").split()

    for part in parts:
        part = part.strip().upper()

        if part in US_STATES:
            return part

    return ""


def extract_zip(value):
    if not value:
        return ""

    match = re.search(r"\b\d{5}(?:-\d{4})?\b", value)

    if match:
        return match.group(0)

    return ""


def values_match(field_name, expected, extracted):
    expected = str(expected or "").strip()
    extracted = str(extracted or "").strip()

    if expected == "NOT_VERIFIABLE":
        return "Not Verifiable"

    expected_norm = normalize_value(expected)
    extracted_norm = normalize_value(extracted)

    if not expected_norm and not extracted_norm:
        return "Pass"

    if not expected_norm or not extracted_norm:
        return "Fail"

    if field_name in {"employee_name", "employee_ssn"}:
        return "Pass" if expected_norm == extracted_norm else "Fail"

    if field_name == "employee_address":
        expected_state = extract_state(expected)
        extracted_state = extract_state(extracted)

        expected_zip = extract_zip(expected)
        extracted_zip = extract_zip(extracted)

        state_matches = expected_state == extracted_state
        zip_matches = expected_zip == extracted_zip

        similarity = SequenceMatcher(None, expected_norm, extracted_norm).ratio()

        if expected_norm == extracted_norm:
            return "Pass"

        if state_matches and zip_matches and similarity >= 0.90:
            return "Pass"

        return "Fail"

    return "Pass" if expected_norm == extracted_norm else "Fail"


def read_ground_truth():
    rows = []

    with open(GROUND_TRUTH_CSV, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            rows.append(row)

    return rows


def read_extracted_results():
    extracted_by_file = {}

    with open(EXTRACTED_RESULTS_CSV, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            file_name = row.get("file_name", "").strip()

            if file_name:
                extracted_by_file[file_name] = row

    return extracted_by_file


def write_validation_results(ground_truth_rows, extracted_by_file):
    os.makedirs("sample_output", exist_ok=True)

    validation_rows = []

    for truth_row in ground_truth_rows:
        file_name = truth_row["file_name"]
        file_type = truth_row["file_type"]

        extracted_row = extracted_by_file.get(file_name, {})

        for field_name in FIELDS_TO_CHECK:
            expected_value = truth_row.get(field_name, "")
            extracted_value = extracted_row.get(field_name, "")

            result = values_match(field_name, expected_value, extracted_value)

            validation_rows.append({
                "file_name": file_name,
                "file_type": file_type,
                "field_name": field_name,
                "expected_value": expected_value,
                "extracted_value": extracted_value,
                "result": result,
                "status": extracted_row.get("status", ""),
                "review_reason": extracted_row.get("review_reason", ""),
            })

    fieldnames = [
        "file_name",
        "file_type",
        "field_name",
        "expected_value",
        "extracted_value",
        "result",
        "status",
        "review_reason",
    ]

    with open(VALIDATION_RESULTS_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(validation_rows)

    return validation_rows


def write_failed_fields(validation_rows):
    failed_rows = [
        row for row in validation_rows
        if row["result"] == "Fail"
    ]

    fieldnames = [
        "file_name",
        "file_type",
        "field_name",
        "expected_value",
        "extracted_value",
        "result",
        "status",
        "review_reason",
    ]

    with open(FAILED_FIELDS_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failed_rows)

    return failed_rows


def summarize_results(validation_rows):
    pass_count = sum(1 for row in validation_rows if row["result"] == "Pass")
    fail_count = sum(1 for row in validation_rows if row["result"] == "Fail")
    not_verifiable_count = sum(1 for row in validation_rows if row["result"] == "Not Verifiable")

    verifiable_count = pass_count + fail_count

    field_level_accuracy = pass_count / verifiable_count if verifiable_count else 0

    clean_rows = [
        row for row in validation_rows
        if row["file_type"] == "clean"
        and row["result"] != "Not Verifiable"
    ]

    noisy_rows = [
        row for row in validation_rows
        if row["file_type"] == "noisy"
        and row["result"] != "Not Verifiable"
    ]

    clean_pass = sum(1 for row in clean_rows if row["result"] == "Pass")
    noisy_pass = sum(1 for row in noisy_rows if row["result"] == "Pass")

    clean_accuracy = clean_pass / len(clean_rows) if clean_rows else 0
    noisy_accuracy = noisy_pass / len(noisy_rows) if noisy_rows else 0

    auto_approved_rows = [
        row for row in validation_rows
        if row["status"] == "AUTO_APPROVED"
        and row["result"] != "Not Verifiable"
    ]

    auto_approved_pass = sum(1 for row in auto_approved_rows if row["result"] == "Pass")

    auto_approval_precision = (
        auto_approved_pass / len(auto_approved_rows)
        if auto_approved_rows
        else 0
    )

    summary_rows = [
        {"metric": "total_files_in_ground_truth", "value": len(set(row["file_name"] for row in validation_rows))},
        {"metric": "total_field_checks", "value": len(validation_rows)},
        {"metric": "pass_fields", "value": pass_count},
        {"metric": "fail_fields", "value": fail_count},
        {"metric": "not_verifiable_fields", "value": not_verifiable_count},
        {"metric": "verifiable_fields", "value": verifiable_count},
        {"metric": "field_level_accuracy_excluding_not_verifiable", "value": f"{field_level_accuracy:.2%}"},
        {"metric": "clean_field_level_accuracy", "value": f"{clean_accuracy:.2%}"},
        {"metric": "noisy_field_level_accuracy", "value": f"{noisy_accuracy:.2%}"},
        {"metric": "auto_approval_precision", "value": f"{auto_approval_precision:.2%}"},
        {"metric": "accuracy_formula", "value": "Pass / (Pass + Fail), excluding Not Verifiable fields"},
        {"metric": "precision_formula", "value": "Correct AUTO_APPROVED fields / all AUTO_APPROVED verifiable fields"},
    ]

    with open(ACCURACY_SUMMARY_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_rows)

    return summary_rows


def print_failed_fields(failed_rows):
    print("\nFailed fields:")

    if not failed_rows:
        print("No failed fields found.")
        return

    for row in failed_rows:
        print("-" * 100)
        print(f"File:      {row['file_name']}")
        print(f"Type:      {row['file_type']}")
        print(f"Field:     {row['field_name']}")
        print(f"Expected:  {row['expected_value']}")
        print(f"Extracted: {row['extracted_value']}")
        print(f"Status:    {row['status']}")
        print(f"Reason:    {row['review_reason']}")


def main():
    ground_truth_rows = read_ground_truth()
    extracted_by_file = read_extracted_results()

    validation_rows = write_validation_results(ground_truth_rows, extracted_by_file)
    failed_rows = write_failed_fields(validation_rows)
    summary_rows = summarize_results(validation_rows)

    print("\nValidation results created:")
    print(VALIDATION_RESULTS_CSV)

    print("\nAccuracy summary created:")
    print(ACCURACY_SUMMARY_CSV)

    print("\nFailed fields created:")
    print(FAILED_FIELDS_CSV)

    print("\nSummary:")
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}")

    print_failed_fields(failed_rows)


if __name__ == "__main__":
    main()