import re
import random

CARD_PATTERN = re.compile(
    r'(\d{15,19})\s*[|:/\\\-]\s*(\d{1,2})\s*[|:/\\\-]\s*(\d{2,4})\s*[|:/\\\-]\s*(\d{3,4})'
)

# ─── Luhn ────────────────────────────────────────────────────────────────────

def luhn_check(number: str) -> bool:
    digits = [int(d) for d in number]
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

def luhn_complete(partial: str) -> str:
    """Append the single check digit that makes partial pass Luhn."""
    for d in range(10):
        candidate = partial + str(d)
        if luhn_check(candidate):
            return candidate
    return None

# ─── Parsing ─────────────────────────────────────────────────────────────────

def parse_card(line: str) -> dict:
    """Parse a single card line. Returns dict with cc/month/year/cvv (2-digit year)."""
    line = line.strip()
    if not line:
        return None
    match = CARD_PATTERN.search(line)
    if not match:
        return None
    cc, mm, yy, cvv = match.groups()
    mm = mm.zfill(2)
    if not (1 <= int(mm) <= 12):
        return None
    if len(yy) == 4:
        yy = yy[2:]
    if len(yy) != 2:
        return None
    return {"cc": cc, "month": mm, "year": yy, "cvv": cvv}

def parse_cards(text: str) -> list:
    cards = []
    for line in text.strip().split("\n"):
        card = parse_card(line)
        if card:
            cards.append(card)
    return cards

def format_card(card: dict) -> str:
    return f"{card['cc']}|{card['month']}|{card['year']}|{card['cvv']}"

# ─── Generator ───────────────────────────────────────────────────────────────

def _is_rand(s: str) -> bool:
    return bool(s) and all(c.lower() == "x" for c in s)

def parse_gen_input(text: str):
    """
    Parse /gen argument string.
    Format: <prefix>[|mm|yy|cvv] [count]
      - prefix: 6+ digits (the BIN + optional fixed middle digits)
      - mm/yy/cvv: exact digits OR x/xx/xxx (random)
      - count: 1-50, default 10
    Returns (prefix, mm, yy, cvv_pattern, count) or None.
    """
    text = text.strip()
    if not text:
        return None

    count = 10
    tokens = text.rsplit(None, 1)
    if len(tokens) == 2 and tokens[1].isdigit():
        n = int(tokens[1])
        if 1 <= n <= 50:
            count = n
            text = tokens[0].strip()

    fields = re.split(r"[|:/\\\-]", text)
    prefix = re.sub(r"\D", "", fields[0])
    if len(prefix) < 6:
        return None

    mm          = fields[1].strip() if len(fields) > 1 and fields[1].strip() else "xx"
    yy          = fields[2].strip() if len(fields) > 2 and fields[2].strip() else "xx"
    cvv_pattern = fields[3].strip() if len(fields) > 3 and fields[3].strip() else "xxx"

    return prefix, mm, yy, cvv_pattern, count

def generate_cards(prefix: str, mm: str, yy: str, cvv_pattern: str, count: int = 10) -> list:
    is_amex  = prefix.startswith("34") or prefix.startswith("37")
    card_len = 15 if is_amex else 16
    cvv_len  = 4  if is_amex else 3

    generated: set = set()
    cards: list    = []
    attempts = 0

    while len(cards) < count and attempts < count * 40:
        attempts += 1

        if len(prefix) >= card_len:
            partial = prefix[:card_len - 1]
        else:
            filler  = "".join(str(random.randint(0, 9)) for _ in range(card_len - len(prefix) - 1))
            partial = prefix + filler

        card_num = luhn_complete(partial)
        if not card_num:
            continue

        # Month
        if _is_rand(mm):
            card_mm = f"{random.randint(1, 12):02d}"
        elif mm.isdigit():
            card_mm = mm.zfill(2)
        else:
            card_mm = f"{random.randint(1, 12):02d}"

        # Year (stored as 2-digit)
        if _is_rand(yy):
            card_yy = str(random.randint(25, 32))
        elif yy.isdigit():
            y = yy[2:] if len(yy) == 4 else yy
            card_yy = y if len(y) == 2 else str(random.randint(25, 32))
        else:
            card_yy = str(random.randint(25, 32))

        # CVV
        if _is_rand(cvv_pattern):
            card_cvv = "".join(str(random.randint(0, 9)) for _ in range(cvv_len))
        elif cvv_pattern.isdigit():
            card_cvv = cvv_pattern
        else:
            card_cvv = "".join(str(random.randint(0, 9)) for _ in range(cvv_len))

        entry = f"{card_num}|{card_mm}|{card_yy}|{card_cvv}"
        if entry not in generated:
            generated.add(entry)
            cards.append(entry)

    return cards
