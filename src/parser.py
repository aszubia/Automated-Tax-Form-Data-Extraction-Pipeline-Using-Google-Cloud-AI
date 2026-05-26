import re


try:
    import spacy

    try:
        NLP = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
    except Exception:
        NLP = None
        SPACY_AVAILABLE = False

except Exception:
    NLP = None
    SPACY_AVAILABLE = False


US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
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
    "co",
    "limited",
    "sons",
    "industries",
    "services",
    "associates",
    "partners",
}


IGNORE_SINGLE_WORDS = {
    "employee",
    "plan",
    "retirement",
    "retrement",
    "statutory",
    "stutery",
    "satey",
    "third-party",
    "sick",
    "pay",
    "last",
    "name",
    "other",
    "see",
    "instructions",
    "turbanty",
    "tumorang",
    "lapaine",
    "parures",
    "statement",
    "safe",
    "accurate",
    "fast",
    "file",
    "efile",
    "copy",
    "wage",
    "tax",
    "department",
    "treasury",
    "internal",
    "revenue",
    "service",
    "www",
    "the",
    "his",
    "cena",
    "je",
    "mgumu",
    "kuniam",
    "tigating",
    "van",
    "ampuni",
    "salle",
    "annual",
    "sabote",
    "wilay",
    "ways",
    "eade",
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
}


ZIP_PATTERN = r"\b\d{5}(?:-\d{4})?(?!-\d)\b"


def clean_text(value):
    if not value:
        return None

    value = re.sub(r"\s+", " ", value).strip()
    return value if value else None


def clean_employee_name(value):
    if not value:
        return None

    value = clean_text(value)
    name_parts = value.split()

    cleaned_parts = []

    for part in name_parts:
        part_clean = part.strip(". ")

        if len(part_clean) == 1 and part_clean.isalpha():
            continue

        cleaned_parts.append(part)

    if not cleaned_parts:
        return value

    return clean_text(" ".join(cleaned_parts))


def get_lines(raw_text):
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def find_first_match(pattern, text):
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return None


def is_money_or_number(line):
    return bool(re.fullmatch(r"\d+(\.\d+)?", line))


def is_code_or_checkbox(line):
    return line in {"X", "x", "G", "D"} or bool(re.fullmatch(r"\d+[a-zA-Z]?", line))


def is_state(line):
    return line.strip() in US_STATES


def contains_state(line):
    words = line.strip().split()
    return any(word in US_STATES for word in words)


def is_zip(line):
    return bool(re.fullmatch(ZIP_PATTERN, line.strip()))


def contains_zip(line):
    return bool(re.search(ZIP_PATTERN, line.strip()))


def has_address_term(line):
    if not line:
        return False

    words = re.findall(r"[A-Za-z]+", line.lower())

    for word in words:
        if word in ADDRESS_TERMS:
            return True

    return False


def is_company_like_name(name):
    """
    Detects company-like names only for candidate scoring.
    This does not globally remove company lines.
    """

    if not name:
        return False

    lower_name = name.lower()
    words = re.findall(r"[A-Za-z]+", lower_name)

    if " and sons" in lower_name:
        return True

    return any(word in COMPANY_NAME_TERMS for word in words)


def is_person_entity_spacy(name):
    """
    Uses spaCy as an optional PERSON check.

    If spaCy is not installed or model is missing, this safely returns False.
    The parser still works using rule-based logic.
    """

    if not name or not SPACY_AVAILABLE or NLP is None:
        return False

    try:
        doc = NLP(name)

        for ent in doc.ents:
            if ent.label_ == "PERSON" and ent.text.strip().lower() == name.strip().lower():
                return True

        # Some short names may not be returned as a full entity.
        # Accept if all detected entities are PERSON and cover most of the string.
        person_text = " ".join(ent.text for ent in doc.ents if ent.label_ == "PERSON").strip()

        if person_text and person_text.lower() == name.strip().lower():
            return True

    except Exception:
        return False

    return False


def spacy_person_score(name):
    if not name:
        return 0

    if is_person_entity_spacy(name):
        return 45

    swapped_name = swap_two_word_name(name)

    if swapped_name and swapped_name != name and is_person_entity_spacy(swapped_name):
        return 35

    return 0


def swap_two_word_name(name):
    if not name:
        return None

    name = clean_employee_name(name)
    parts = name.split()

    if len(parts) != 2:
        return name

    return clean_text(f"{parts[1]} {parts[0]}")


def choose_best_name_order(name, context_lines=None):
    """
    Chooses between:
    Martinez Joseph vs Joseph Martinez
    Mason Steven vs Steven Mason

    It uses:
    1. nearby W-2 label order when available
    2. spaCy PERSON detection when available
    3. original order as fallback
    """

    if not name:
        return None

    name = clean_employee_name(name)
    parts = name.split()

    if len(parts) != 2:
        return name

    swapped = swap_two_word_name(name)

    context_text = " ".join(context_lines or []).lower()

    last_name_pos = context_text.find("last name")
    first_name_pos = context_text.find("employee's first name")

    label_suggests_reversed = (
        last_name_pos != -1
        and first_name_pos != -1
        and last_name_pos < first_name_pos
    )

    if label_suggests_reversed:
        return swapped

    original_is_person = is_person_entity_spacy(name)
    swapped_is_person = is_person_entity_spacy(swapped)

    if swapped_is_person and not original_is_person:
        return swapped

    return name


def is_street_line(line):
    """
    A street line should:
    - start with a number
    - contain alphabetic text
    - contain a street/address-like word
    """

    if not line:
        return False

    line = clean_text(line)

    if not line:
        return False

    starts_with_number = bool(re.search(r"^\d{1,6}\s+[A-Za-z]", line))

    return starts_with_number and has_address_term(line)


def is_city_state_zip_line(line):
    if not line:
        return False

    return contains_state(line) and contains_zip(line)


def parse_city_state_zip_from_line(line):
    if not line:
        return None, None, None

    parts = line.strip().split()

    zip_code = None
    state = None
    city_parts = []

    for i, part in enumerate(parts):
        zip_match = re.search(ZIP_PATTERN, part)

        if zip_match:
            zip_code = zip_match.group(0)

            if i > 0 and parts[i - 1] in US_STATES:
                state = parts[i - 1]
                city_parts = parts[:i - 1]

            break

    city = " ".join(city_parts) if city_parts else None

    return clean_text(city), state, zip_code


def parse_city_state_from_line(line):
    if not line:
        return None, None

    parts = line.strip().split()

    if len(parts) < 2:
        return None, None

    possible_state = parts[-1]

    if possible_state in US_STATES:
        city = " ".join(parts[:-1])
        return clean_text(city), possible_state

    return None, None


def is_ignored_single_word(line):
    return line.strip().lower() in IGNORE_SINGLE_WORDS


def is_label_line(line):
    label_keywords = [
        "employee's social security number",
        "employer identification number",
        "wages",
        "tax withheld",
        "social security",
        "medicare",
        "allocated tips",
        "control number",
        "advance eic",
        "dependent care",
        "employee's first name",
        "last name",
        "nonqualified plans",
        "instructions",
        "statutory",
        "retirement",
        "third-party",
        "sick pay",
        "other",
        "employee's address",
        "state",
        "locality",
        "department of the treasury",
        "internal revenue service",
        "form w-2",
        "statement",
        "copy",
        "safe",
        "accurate",
        "irs",
        "efile",
        "omb",
        "visit",
        "cut here",
    ]

    lower_line = line.lower()

    if is_ignored_single_word(line):
        return True

    return any(keyword in lower_line for keyword in label_keywords)


def is_title_case_word(word):
    if not word:
        return False

    word = word.strip(". ")

    if not re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word):
        return False

    return word[0].isupper() and not word.isupper()


def is_possible_name_line(line):
    if not line:
        return False

    if is_label_line(line):
        return False

    if is_money_or_number(line):
        return False

    if is_code_or_checkbox(line):
        return False

    if is_state(line):
        return False

    if is_zip(line):
        return False

    if is_street_line(line):
        return False

    return bool(re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", line))


def extract_employee_ssn(raw_text):
    return find_first_match(r"\b\d{3}-\d{2}-\d{4}\b", raw_text)


def extract_employer_ein(raw_text):
    return find_first_match(r"\b\d{2}-\d{7}\b", raw_text)


def get_previous_city(next_lines, current_index):
    for j in range(current_index - 1, -1, -1):
        candidate = next_lines[j]

        if (
            re.search(r"[A-Za-z]", candidate)
            and not is_state(candidate)
            and not contains_zip(candidate)
            and not is_label_line(candidate)
            and not is_street_line(candidate)
        ):
            return candidate

    return None


def get_next_city(next_lines, current_index):
    for j in range(current_index + 1, len(next_lines)):
        candidate = next_lines[j]

        if (
            re.search(r"[A-Za-z]", candidate)
            and not is_state(candidate)
            and not contains_zip(candidate)
            and not is_label_line(candidate)
            and not is_street_line(candidate)
            and not is_money_or_number(candidate)
            and not is_code_or_checkbox(candidate)
        ):
            return candidate

    return None


def get_previous_state_and_city(next_lines, current_index):
    state = None
    city = None

    for j in range(current_index - 1, -1, -1):
        candidate = next_lines[j]

        if is_state(candidate):
            state = candidate
            city = get_previous_city(next_lines, j)
            break

        parsed_city, parsed_state = parse_city_state_from_line(candidate)

        if parsed_city and parsed_state:
            city = parsed_city
            state = parsed_state
            break

    return city, state


def find_zip_after_city_state(next_lines, start_index):
    for later_line in next_lines[start_index + 1:]:
        if is_zip(later_line):
            return later_line

        if contains_zip(later_line):
            zip_match = re.search(ZIP_PATTERN, later_line)
            if zip_match:
                return zip_match.group(0)

    return None


def extract_address_from_lines(useful_lines, street_index):
    if street_index is None:
        return None

    street = useful_lines[street_index]
    city = None
    state = None
    zip_code = None

    next_lines = useful_lines[street_index + 1: street_index + 12]

    for i, line in enumerate(next_lines):
        if is_city_state_zip_line(line):
            parsed_city, parsed_state, parsed_zip = parse_city_state_zip_from_line(line)

            zip_code = parsed_zip
            state = parsed_state

            if parsed_city:
                city = parsed_city
            else:
                city = get_previous_city(next_lines, i)

                if not city:
                    city = get_next_city(next_lines, i)

            address_parts = [street, city, state, zip_code]
            return clean_text(" ".join([p for p in address_parts if p]))

    for i, line in enumerate(next_lines):
        parsed_city, parsed_state = parse_city_state_from_line(line)

        if parsed_city and parsed_state:
            city = parsed_city
            state = parsed_state
            zip_code = find_zip_after_city_state(next_lines, i)

            address_parts = [street, city, state, zip_code]
            return clean_text(" ".join([p for p in address_parts if p]))

    for i, line in enumerate(next_lines):
        if is_state(line):
            state = line
            city = get_previous_city(next_lines, i)

            if not city:
                city = get_next_city(next_lines, i)

            zip_code = find_zip_after_city_state(next_lines, i)

            address_parts = [street, city, state, zip_code]
            return clean_text(" ".join([p for p in address_parts if p]))

    for i, line in enumerate(next_lines):
        if is_zip(line):
            zip_code = line
            city, state = get_previous_state_and_city(next_lines, i)

            address_parts = [street, city, state, zip_code]
            return clean_text(" ".join([p for p in address_parts if p]))

    return clean_text(street)


def normalize_street_key(street):
    if not street:
        return None

    parts = re.findall(r"[A-Za-z0-9]+", street.lower())

    if len(parts) < 2:
        return None

    return f"{parts[0]}_{parts[1]}"


def address_quality_score(address):
    if not address:
        return 0

    score = 0

    if is_street_line(address):
        score += 10

    if contains_state(address):
        score += 20

    if contains_zip(address):
        score += 25

    return score


def extract_employer_details(lines):
    employer_name = None
    employer_address = None

    start_index = None

    for i, line in enumerate(lines):
        if "Employer's name, address, and ZIP code" in line:
            start_index = i
            break

    if start_index is None:
        return employer_name, employer_address

    block = []

    for line in lines[start_index + 1:]:
        if "d Control number" in line or "Employee's first name" in line:
            break
        block.append(line)

    useful_lines = []

    for line in block:
        if is_money_or_number(line):
            continue
        if is_code_or_checkbox(line):
            continue
        if is_label_line(line):
            continue
        useful_lines.append(line)

    for line in useful_lines:
        if not employer_name and re.search(r"[A-Za-z]", line) and not is_street_line(line):
            employer_name = line
            break

    street_index = None

    for i, line in enumerate(useful_lines):
        if is_street_line(line):
            street_index = i
            break

    employer_address = extract_address_from_lines(useful_lines, street_index)

    return clean_text(employer_name), employer_address


def is_likely_single_name_part(line):
    if not line:
        return False

    line = clean_text(line)

    if not line:
        return False

    if " " in line:
        return False

    if is_label_line(line):
        return False

    if is_money_or_number(line):
        return False

    if is_code_or_checkbox(line):
        return False

    if is_state(line):
        return False

    if is_zip(line):
        return False

    if is_street_line(line):
        return False

    letters_only = re.sub(r"[^A-Za-z]", "", line)

    if len(letters_only) < 2:
        return False

    if letters_only.isupper():
        return False

    return is_title_case_word(line)


def is_likely_full_name_line(line):
    if not line:
        return False

    line = clean_text(line)

    if not line:
        return False

    if is_label_line(line):
        return False

    if contains_state(line):
        return False

    if contains_zip(line):
        return False

    if is_street_line(line):
        return False

    parts = line.split()

    if len(parts) != 2:
        return False

    for part in parts:
        cleaned = part.strip(". ")

        if len(cleaned) == 1 and cleaned.isalpha():
            return False

        if cleaned.lower() in IGNORE_SINGLE_WORDS:
            return False

        if not is_title_case_word(cleaned):
            return False

    return True


def find_name_before_street(lines, street_index):
    window_start = max(0, street_index - 15)
    previous_lines = lines[window_start:street_index]

    for j in range(len(previous_lines) - 1, -1, -1):
        line = previous_lines[j]

        if is_likely_full_name_line(line):
            return choose_best_name_order(line, previous_lines)

    name_parts_reversed = []
    gap_count = 0

    for j in range(len(previous_lines) - 1, -1, -1):
        line = previous_lines[j]

        if is_likely_single_name_part(line):
            name_parts_reversed.append(line)
            gap_count = 0

            if len(name_parts_reversed) >= 2:
                break
        else:
            if name_parts_reversed:
                gap_count += 1

                if gap_count > 5:
                    break

    if len(name_parts_reversed) >= 2:
        top_to_bottom = list(reversed(name_parts_reversed[:2]))
        bottom_to_top = name_parts_reversed[:2]

        top_to_bottom_name = clean_employee_name(" ".join(top_to_bottom))
        bottom_to_top_name = clean_employee_name(" ".join(bottom_to_top))

        top_to_bottom_name = choose_best_name_order(top_to_bottom_name, previous_lines)
        bottom_to_top_name = choose_best_name_order(bottom_to_top_name, previous_lines)

        top_score = spacy_person_score(top_to_bottom_name)
        bottom_score = spacy_person_score(bottom_to_top_name)

        if bottom_score > top_score:
            return bottom_to_top_name

        return top_to_bottom_name

    return None


def has_employee_context(lines, street_index):
    window_start = max(0, street_index - 25)
    window_end = min(len(lines), street_index + 5)
    window_text = " ".join(lines[window_start:window_end]).lower()

    employee_terms = [
        "employee's first name",
        "employee's address",
        "last name",
        "employee",
    ]

    return any(term in window_text for term in employee_terms)


def has_employer_context(lines, street_index):
    window_start = max(0, street_index - 15)
    window_end = min(len(lines), street_index + 5)
    window_text = " ".join(lines[window_start:window_end]).lower()

    employer_terms = [
        "employer's name",
        "employer identification",
        "employer",
    ]

    return any(term in window_text for term in employer_terms)


def count_name_evidence(name, lines):
    if not name:
        return 0

    parts = name.split()

    if len(parts) < 2:
        return 0

    first_name = re.escape(parts[0].lower())
    last_name = re.escape(parts[-1].lower())
    full_name = re.escape(name.lower())

    normalized_text = " ".join(lines).lower()

    full_count = len(re.findall(rf"\b{full_name}\b", normalized_text))

    if full_count > 0:
        return full_count

    first_count = len(re.findall(rf"\b{first_name}\b", normalized_text))
    last_count = len(re.findall(rf"\b{last_name}\b", normalized_text))

    return min(first_count, last_count)


def score_candidate(lines, street_index, name, address):
    score = 0

    if name:
        score += 20

    if address:
        score += 20

    if contains_state(address or ""):
        score += 15

    if contains_zip(address or ""):
        score += 20

    if has_employee_context(lines, street_index):
        score += 25

    if has_employer_context(lines, street_index):
        score -= 35

    if name and is_likely_full_name_line(name):
        score += 10

    score += spacy_person_score(name)

    name_evidence_count = count_name_evidence(name, lines)

    if name_evidence_count >= 2:
        score += 45
    elif name_evidence_count == 1:
        score += 5

    if name:
        lower_name = name.lower()
        letters_only = re.sub(r"[^A-Za-z]", "", name)
        name_parts = name.split()

        bad_name_terms = [
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
        ]

        if any(term in lower_name for term in bad_name_terms):
            score -= 120

        if letters_only.isupper():
            score -= 100

        if len(name_parts) >= 2 and len(name_parts[0]) <= 2:
            score -= 35

        if is_company_like_name(name):
            score -= 120

    return score


def build_best_address_map(lines):
    address_map = {}

    for i, line in enumerate(lines):
        if not is_street_line(line):
            continue

        key = normalize_street_key(line)

        if not key:
            continue

        address = extract_address_from_lines(lines, i)
        quality = address_quality_score(address)

        if key not in address_map or quality > address_map[key]["quality"]:
            address_map[key] = {
                "address": address,
                "quality": quality,
            }

    return address_map


def collect_employee_candidates(lines):
    candidates = []
    best_address_map = build_best_address_map(lines)

    for i, line in enumerate(lines):
        if not is_street_line(line):
            continue

        name = find_name_before_street(lines, i)
        address = extract_address_from_lines(lines, i)

        if not name or not address:
            continue

        street_key = normalize_street_key(line)

        if street_key in best_address_map:
            better_address = best_address_map[street_key]["address"]

            if address_quality_score(better_address) > address_quality_score(address):
                address = better_address

        score = score_candidate(lines, i, name, address)

        candidates.append(
            {
                "name": clean_employee_name(name),
                "address": address,
                "street_index": i,
                "score": score,
            }
        )

    return candidates


def select_best_candidate(candidates):
    if not candidates:
        return None, None

    candidates = sorted(
        candidates,
        key=lambda item: (
            item["score"],
            contains_state(item["address"] or ""),
            contains_zip(item["address"] or ""),
        ),
        reverse=True,
    )

    best = candidates[0]

    return best["name"], best["address"]


def extract_employee_details(lines):
    employee_name = None
    employee_address = None

    start_index = None
    end_index = None

    for i, line in enumerate(lines):
        if "Employee's first name and initial" in line:
            start_index = i
            break

    if start_index is not None:
        for i, line in enumerate(lines[start_index + 1:], start=start_index + 1):
            if "Employee's address and ZIP code" in line:
                end_index = i
                break

    if start_index is not None:
        if end_index is not None:
            block = lines[start_index + 1:end_index]
        else:
            block = lines[start_index + 1:start_index + 45]

        useful_lines = []

        for line in block:
            if is_money_or_number(line):
                continue
            if is_code_or_checkbox(line):
                continue
            if is_label_line(line):
                continue
            useful_lines.append(line)

        candidates = collect_employee_candidates(useful_lines)
        employee_name, employee_address = select_best_candidate(candidates)

    return clean_employee_name(employee_name), employee_address


def extract_employee_details_fallback(lines):
    candidates = collect_employee_candidates(lines)
    return select_best_candidate(candidates)


def parse_w2_document(raw_text):
    lines = get_lines(raw_text)

    employee_ssn = extract_employee_ssn(raw_text)
    employer_ein = extract_employer_ein(raw_text)
    employer_name, employer_address = extract_employer_details(lines)
    employee_name, employee_address = extract_employee_details(lines)

    if not employee_name or not employee_address:
        fallback_name, fallback_address = extract_employee_details_fallback(lines)

        if not employee_name and fallback_name:
            employee_name = fallback_name

        if not employee_address and fallback_address:
            employee_address = fallback_address

    employee_name = choose_best_name_order(employee_name, lines)

    return {
        "employee_name": employee_name,
        "employee_address": employee_address,
        "employee_ssn": employee_ssn,
        "employer_name": employer_name,
        "employer_address": employer_address,
        "employer_ein": employer_ein,
    }