import re


AUTO_APPROVED = "AUTO_APPROVED"
NEEDS_REVIEW = "NEEDS_REVIEW"


MIN_NAME_CONFIDENCE = 0.90
MIN_ADDRESS_CONFIDENCE = 0.90
MIN_ID_CONFIDENCE = 0.90
MIN_OVERALL_CONFIDENCE = 0.90


US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


ADDRESS_TERMS = {
    "street",
    "st",
    "road",
    "rd",
    "avenue",
    "ave",
    "drive",
    "dr",
    "lane",
    "ln",
    "highway",
    "hwy",
    "throughway",
    "throughwa",
    "way",
    "court",
    "ct",
    "circle",
    "circles",
    "cir",
    "suite",
    "ste",
    "apt",
    "apartment",
    "plaza",
    "plain",
    "plains",
    "trail",
    "trails",
    "view",
    "views",
    "neck",
    "shoal",
    "shoals",
    "shore",
    "shores",
    "cliff",
    "cliffs",
    "mill",
    "mills",
    "prairie",
    "crest",
    "stream",
    "burg",
    "falls",
    "lock",
    "locks",
    "crescent",
    "pines",
    "brooks",
    "radial",
    "islands",
    "loop",
    "loops",
    "extension",
    "extensions",
    "union",
    "unions",
    "freeway",
    "track",
    "tracks",
    "point",
    "points",
    "mission",
    "spurs",
    "pine",
}


COMPANY_NAME_TERMS = {
    "llc",
    "ltd",
    "inc",
    "plc",
    "group",
    "corp",
    "corporation",
    "company",
    "limited",
    "sons",
    "industries",
    "services",
    "associates",
    "partners",
}


BAD_NAME_TERMS = {
    "efile",
    "e-file",
    "www",
    "statement",
    "safe",
    "accurate",
    "retirement",
    "retrement",
    "statutory",
    "stutery",
    "turbanty",
    "cena",
    "mgumu",
    "kuniam",
    "tigating",
    "ampuni",
    "salle",
    "annual",
    "sabote",
    "wilay",
    "ways",
    "eade",
}


ZIP_PATTERN = r"\b\d{5}(?:-\d{4})?\b"
SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
STATE_PATTERN = r"\b(" + "|".join(sorted(US_STATES)) + r")\b"


def clean_text(value):
    if value is None:
        return None

    value = str(value)
    value = re.sub(r"\s+", " ", value).strip()

    if not value:
        return None

    if value.lower() in {"none", "null", "nan", "not_verifiable"}:
        return None

    return value


def normalize_text(value):
    if not value:
        return ""

    value = str(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def contains_company_term(value):
    if not value:
        return False

    words = re.findall(r"[A-Za-z]+", value.lower())

    if " and sons" in value.lower():
        return True

    return any(word in COMPANY_NAME_TERMS for word in words)


def is_valid_employee_name(employee_name):
    employee_name = clean_text(employee_name)

    if not employee_name:
        return False

    if contains_company_term(employee_name):
        return False

    lower_name = employee_name.lower()

    if any(term in lower_name for term in BAD_NAME_TERMS):
        return False

    parts = employee_name.split()

    if len(parts) < 2:
        return False

    if len(parts) > 4:
        return False

    valid_parts = []

    for part in parts:
        cleaned = part.strip(".'- ")

        if len(cleaned) <= 1:
            continue

        if not re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", cleaned):
            return False

        # Reject all-uppercase OCR noise such as CENA JE.
        if cleaned.isupper():
            return False

        valid_parts.append(cleaned)

    return len(valid_parts) >= 2


def has_address_term(address):
    if not address:
        return False

    words = re.findall(r"[A-Za-z]+", address.lower())

    return any(word in ADDRESS_TERMS for word in words)


def has_street_number(address):
    if not address:
        return False

    return bool(re.search(r"^\d{1,6}\s+[A-Za-z]", address.strip()))


def extract_state_zip(address):
    """
    Extracts state and ZIP only when the ZIP appears after the state.

    Good:
    New Scott AL 92936-1875
    Erinville ID 20207-7340
    East Richardshire DE 42353

    Bad:
    29204 Harding Shoals Apt. 943 Benjaminchester ID
    148 Marquez Cliff Apt. 823 Port Alexanderside AZ
    """

    if not address:
        return None, None

    pattern = rf"{STATE_PATTERN}\s+({ZIP_PATTERN})"
    match = re.search(pattern, address)

    if not match:
        return None, None

    state = match.group(1)
    zip_code = match.group(2)

    return state, zip_code


def has_valid_state_zip(address):
    state, zip_code = extract_state_zip(address)

    return bool(state and zip_code)


def is_valid_employee_address(employee_address):
    employee_address = clean_text(employee_address)

    if not employee_address:
        return False

    if not has_street_number(employee_address):
        return False

    if not has_address_term(employee_address):
        return False

    if not has_valid_state_zip(employee_address):
        return False

    # Require at least enough words for street + city/state/ZIP.
    words = re.findall(r"[A-Za-z0-9-]+", employee_address)

    if len(words) < 6:
        return False

    return True


def is_valid_ssn(employee_ssn):
    employee_ssn = clean_text(employee_ssn)

    if not employee_ssn:
        return False

    return bool(re.fullmatch(SSN_PATTERN, employee_ssn))


def count_name_evidence(employee_name, raw_text):
    employee_name = clean_text(employee_name)

    if not employee_name or not raw_text:
        return 0

    normalized_raw = normalize_text(raw_text)
    normalized_name = normalize_text(employee_name)

    if not normalized_name:
        return 0

    exact_count = normalized_raw.count(normalized_name)

    if exact_count > 0:
        return exact_count

    parts = normalized_name.split()

    if len(parts) < 2:
        return 0

    first_name = parts[0]
    last_name = parts[-1]

    first_count = len(re.findall(rf"\b{re.escape(first_name)}\b", normalized_raw))
    last_count = len(re.findall(rf"\b{re.escape(last_name)}\b", normalized_raw))

    return min(first_count, last_count)


def count_ssn_evidence(employee_ssn, raw_text):
    employee_ssn = clean_text(employee_ssn)

    if not employee_ssn or not raw_text:
        return 0

    return len(re.findall(re.escape(employee_ssn), raw_text))


def count_address_evidence(employee_address, raw_text):
    """
    Counts address evidence loosely using street number and ZIP.

    This avoids requiring the full address to appear as one continuous line.
    """

    employee_address = clean_text(employee_address)

    if not employee_address or not raw_text:
        return 0

    if not is_valid_employee_address(employee_address):
        return 0

    street_number_match = re.search(r"^\d{1,6}", employee_address)
    state, zip_code = extract_state_zip(employee_address)

    if not street_number_match or not zip_code:
        return 0

    street_number = street_number_match.group(0)

    street_count = len(re.findall(rf"\b{re.escape(street_number)}\b", raw_text))
    zip_count = len(re.findall(re.escape(zip_code), raw_text))

    if street_count == 0 or zip_count == 0:
        return 0

    return min(street_count, zip_count)


def get_name_confidence(employee_name, raw_text):
    if not is_valid_employee_name(employee_name):
        return 0.0

    evidence_count = count_name_evidence(employee_name, raw_text)

    if evidence_count >= 2:
        return 0.95

    return 0.90


def get_address_confidence(employee_address, raw_text):
    if not is_valid_employee_address(employee_address):
        return 0.0

    evidence_count = count_address_evidence(employee_address, raw_text)

    if evidence_count >= 2:
        return 0.95

    return 0.90


def get_id_confidence(employee_ssn, raw_text):
    if not is_valid_ssn(employee_ssn):
        return 0.0

    evidence_count = count_ssn_evidence(employee_ssn, raw_text)

    if evidence_count >= 2:
        return 0.95

    return 0.90


def validate_extracted_fields(parsed_fields, raw_text):
    raw_text = raw_text or ""

    employee_name = clean_text(parsed_fields.get("employee_name"))
    employee_address = clean_text(parsed_fields.get("employee_address"))
    employee_ssn = clean_text(parsed_fields.get("employee_ssn"))

    name_confidence = get_name_confidence(employee_name, raw_text)
    address_confidence = get_address_confidence(employee_address, raw_text)
    id_confidence = get_id_confidence(employee_ssn, raw_text)

    overall_confidence = (
        name_confidence + address_confidence + id_confidence
    ) / 3

    missing_or_incomplete_fields = []

    if name_confidence < MIN_NAME_CONFIDENCE:
        missing_or_incomplete_fields.append("employee_name")

    if address_confidence < MIN_ADDRESS_CONFIDENCE:
        missing_or_incomplete_fields.append("employee_address")

    if id_confidence < MIN_ID_CONFIDENCE:
        missing_or_incomplete_fields.append("employee_ssn")

    if (
        not missing_or_incomplete_fields
        and overall_confidence >= MIN_OVERALL_CONFIDENCE
    ):
        status = AUTO_APPROVED

        review_reason = (
            "Required customer fields are complete. "
            f"Repeat evidence - name: {count_name_evidence(employee_name, raw_text)}, "
            f"address: {count_address_evidence(employee_address, raw_text)}, "
            f"SSN: {count_ssn_evidence(employee_ssn, raw_text)}."
        )

    else:
        status = NEEDS_REVIEW

        if missing_or_incomplete_fields:
            review_reason = (
                "Missing or incomplete customer field(s): "
                + ", ".join(missing_or_incomplete_fields)
            )
        else:
            review_reason = (
                "Overall confidence is below the auto-approval threshold."
            )

    return {
        "name_confidence": name_confidence,
        "address_confidence": address_confidence,
        "id_confidence": id_confidence,
        "overall_confidence": overall_confidence,
        "status": status,
        "review_reason": review_reason,
    }