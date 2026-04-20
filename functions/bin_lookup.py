import aiohttp
from config import BIN_API_URL

COUNTRY_FLAGS = {}

def _flag(code2: str) -> str:
    if not code2 or len(code2) != 2:
        return ""
    try:
        return chr(0x1F1E6 + ord(code2[0].upper()) - 65) + chr(0x1F1E6 + ord(code2[1].upper()) - 65)
    except Exception:
        return ""

_cache = {}

async def lookup_bin(bin_prefix: str) -> dict:
    bin6 = "".join(filter(str.isdigit, bin_prefix))[:6]
    if len(bin6) < 6:
        return _unknown()

    if bin6 in _cache:
        return _cache[bin6]

    url = BIN_API_URL.format(bin=bin6)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    result = {
                        "bin":      bin6,
                        "brand":    data.get("Brand", "Unknown").upper(),
                        "type":     data.get("Type", "Unknown").upper(),
                        "category": data.get("Category", "Unknown").upper(),
                        "bank":     data.get("Issuer", "Unknown").upper(),
                        "country_code":  data.get("isoCode2", ""),
                        "country_name":  data.get("CountryName", "Unknown").upper(),
                        "flag":     _flag(data.get("isoCode2", "")),
                    }
                    _cache[bin6] = result
                    return result
    except Exception:
        pass
    return _unknown(bin6)

def _unknown(bin6: str = "") -> dict:
    return {
        "bin": bin6,
        "brand": "UNKNOWN",
        "type": "UNKNOWN",
        "category": "UNKNOWN",
        "bank": "UNKNOWN",
        "country_code": "",
        "country_name": "UNKNOWN",
        "flag": "",
    }

def format_bin_block(b: dict) -> str:
    flag = b["flag"]
    country = f"{flag} {b['country_name']} ({b['country_code']})" if b["country_code"] else b["country_name"]
    return (
        f"BIN → {b['bin']} — {b['brand']} — {b['type']}\n"
        f"Product → {b['category']}\n"
        f"Bank → {b['bank']}\n"
        f"Country → {country}"
    )
