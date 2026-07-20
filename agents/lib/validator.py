import json
import re
from dataclasses import dataclass, field

REQUIRED_KEYS = {
    "title", "slug", "meta_description", "html_body",
    "faq", "tags", "category", "image_brief", "fact_sources",
}

BANNED_PHRASES = [
    "you won't believe", "shocking truth", "doctors hate", "click here now",
    "number one trick", "this one weird",
]

# crude but effective heuristic: a bare 4-digit year or a rupee amount not
# accompanied by a fact_source citation is treated as an unsourced claim.
DATE_OR_AMOUNT_RE = re.compile(r"(₹\s?[\d,]+|\b(19|20)\d{2}\b)")


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_article(raw_json_text: str) -> tuple[ValidationResult, dict | None]:
    errors: list[str] = []

    try:
        # strict=False: models often emit literal newlines inside string
        # values (e.g. inside html_body) instead of escaping them as \n.
        article = json.loads(raw_json_text, strict=False)
    except json.JSONDecodeError as exc:
        return ValidationResult(ok=False, errors=[f"JSON did not parse: {exc}"]), None

    missing = REQUIRED_KEYS - article.keys()
    if missing:
        errors.append(f"missing keys: {sorted(missing)}")

    html_body = article.get("html_body", "")
    word_count = len(re.sub(r"<[^>]+>", " ", html_body).split())
    if not (700 <= word_count <= 1500):
        errors.append(f"word count {word_count} outside 700-1500")

    h2_count = len(re.findall(r"<h2", html_body, flags=re.IGNORECASE))
    if h2_count < 3:
        errors.append(f"only {h2_count} <h2> sections, need >= 3")

    meta = article.get("meta_description", "")
    if len(meta) > 155:
        errors.append(f"meta_description {len(meta)} chars, must be <= 155")

    faq = article.get("faq", [])
    if not (3 <= len(faq) <= 5):
        errors.append(f"faq has {len(faq)} entries, need 3-5 (section 5.5 structure contract)")
    elif any(not isinstance(f, dict) or not f.get("q") or not f.get("a") for f in faq):
        errors.append("faq entries must all have non-empty 'q' and 'a'")

    lowered = html_body.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            errors.append(f"banned phrase found: '{phrase}'")

    fact_sources = article.get("fact_sources", [])
    cited_claims = {fs.get("claim", "").strip().lower() for fs in fact_sources if isinstance(fs, dict)}
    body_text = re.sub(r"<[^>]+>", " ", html_body)
    for match in DATE_OR_AMOUNT_RE.finditer(body_text):
        window = body_text[max(0, match.start() - 40):match.end() + 40].lower()
        if not any(claim and claim[:15] in window for claim in cited_claims) and not cited_claims:
            errors.append(f"date/amount '{match.group(0)}' has no fact_source entry")
            break  # one flag is enough to send it to NEEDS_HUMAN, avoid noisy duplicates

    return ValidationResult(ok=not errors, errors=errors), (article if not errors else None)
