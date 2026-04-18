import re


PHONE_PATTERN = re.compile(r"01[016789]-?\d{3,4}-?\d{4}")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def anonymize(text: str) -> tuple[str, dict]:
    pii_map: dict[str, str] = {}
    result = text

    phone_idx = 0
    seen_phones: dict[str, str] = {}

    def _phone_sub(match: re.Match) -> str:
        nonlocal phone_idx
        raw = match.group(0)
        if raw in seen_phones:
            return seen_phones[raw]
        phone_idx += 1
        token = f"[연락처{phone_idx}]"
        seen_phones[raw] = token
        pii_map[token] = raw
        return token

    result = PHONE_PATTERN.sub(_phone_sub, result)

    email_idx = 0
    seen_emails: dict[str, str] = {}

    def _email_sub(match: re.Match) -> str:
        nonlocal email_idx
        raw = match.group(0)
        if raw in seen_emails:
            return seen_emails[raw]
        email_idx += 1
        token = f"[이메일{email_idx}]"
        seen_emails[raw] = token
        pii_map[token] = raw
        return token

    result = EMAIL_PATTERN.sub(_email_sub, result)

    return result, pii_map


def restore(text: str, pii_map: dict) -> str:
    result = text
    for token, original in pii_map.items():
        result = result.replace(token, original)
    return result
