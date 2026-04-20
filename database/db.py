import motor.motor_asyncio
from datetime import datetime, date, timedelta, timezone
import secrets
import string
import os
from config import FREE_DAILY_LIMIT

MONGO_URL = os.getenv("MONGO_URL", "")
DB_NAME = os.getenv("DB_NAME", "semex_bot")

_client = None
_db = None


async def get_db():
    global _client, _db
    if _db is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
        _db = _client[DB_NAME]
        await _ensure_indexes()
    return _db


async def _ensure_indexes():
    db = _db
    await db.users.create_index("user_id", unique=True)
    await db.user_plans.create_index("user_id", unique=True)
    await db.daily_hits.create_index([("user_id", 1), ("hit_date", 1)], unique=True)
    await db.check_logs.create_index([("user_id", 1), ("timestamp", -1)])
    await db.check_logs.create_index("status")
    await db.proxies.create_index([("user_id", 1), ("proxy", 1)], unique=True)
    await db.redeem_codes.create_index("code", unique=True)
    await db.code_uses.create_index([("code", 1), ("user_id", 1)], unique=True)
    await db.admins.create_index("user_id", unique=True)
    await db.saved_bins.create_index([("user_id", 1), ("name", 1)], unique=True)
    await db.bot_settings.create_index("key", unique=True)


# ─── User CRUD ───

async def upsert_user(user_id: int, username: str = None, first_name: str = None):
    db = await get_db()
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id, "username": username or "", "first_name": first_name or ""},
         "$setOnInsert": {"join_date": date.today().isoformat(), "is_banned": 0, "proxy_mode": "system", "show_site": "ask"}},
        upsert=True
    )
    await db.user_plans.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"user_id": user_id, "plan_type": "free", "expiry_date": None, "hits_per_day": 0}},
        upsert=True
    )

async def check_delay(user_id):

    db = await get_db()

    row = await db.cooldowns.find_one({"user_id": user_id})

    return row
    
async def is_banned(user_id: int) -> bool:
    db = await get_db()
    row = await db.users.find_one({"user_id": user_id}, {"_id": 0, "is_banned": 1})
    return bool(row and row.get("is_banned"))


async def ban_user(user_id: int):
    db = await get_db()
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_banned": 1}})


async def unban_user(user_id: int):
    db = await get_db()
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_banned": 0}})


# ─── Proxy mode ───

async def get_user_proxy_mode(user_id: int) -> str:
    db = await get_db()
    row = await db.users.find_one({"user_id": user_id}, {"_id": 0, "proxy_mode": 1})
    return row.get("proxy_mode", "system") if row else "system"


async def set_user_proxy_mode(user_id: int, mode: str):
    db = await get_db()
    await db.users.update_one({"user_id": user_id}, {"$set": {"proxy_mode": mode}})


async def get_show_site(user_id: int) -> str:
    db = await get_db()
    row = await db.users.find_one({"user_id": user_id}, {"_id": 0, "show_site": 1})
    return row.get("show_site", "ask") if row else "ask"


async def set_show_site(user_id: int, mode: str):
    db = await get_db()
    await db.users.update_one({"user_id": user_id}, {"$set": {"show_site": mode}})


# ─── Plans ───

async def get_user_plan(user_id: int) -> dict:
    db = await get_db()
    row = await db.user_plans.find_one({"user_id": user_id}, {"_id": 0})

    if not row:
        return {"type": "free", "label": "Free", "unlimited": False, "hits_per_day": 0, "expiry": None, "just_expired": False}

    plan_type = row.get("plan_type", "free")
    expiry = row.get("expiry_date")
    hpd = row.get("hits_per_day") or 0

    if plan_type != "free" and expiry:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
        if expiry_date < date.today():
            await db.user_plans.update_one(
                {"user_id": user_id},
                {"$set": {"plan_type": "free", "expiry_date": None, "hits_per_day": 0}}
            )
            return {"type": "free", "label": "Free", "unlimited": False, "hits_per_day": 0, "expiry": None, "just_expired": True, "expired_plan": plan_type}
        return {
            "type": plan_type, "label": plan_type, "unlimited": True,
            "hits_per_day": hpd, "expiry": expiry, "just_expired": False,
        }

    return {"type": "free", "label": "Free", "unlimited": False, "hits_per_day": 0, "expiry": None, "just_expired": False}


async def set_user_plan(user_id: int, plan_type: str, days: int, hits_per_day: int = 0):
    db = await get_db()
    expiry = (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
    await db.user_plans.update_one(
        {"user_id": user_id},
        {"$set": {"plan_type": plan_type, "expiry_date": expiry, "hits_per_day": hits_per_day}},
        upsert=True
    )


# ─── Daily hits ───

async def get_daily_hits(user_id: int) -> int:
    db = await get_db()
    today = date.today().isoformat()
    row = await db.daily_hits.find_one({"user_id": user_id, "hit_date": today}, {"_id": 0, "count": 1})
    return row["count"] if row else 0


async def increment_daily_hits(user_id: int) -> int:
    db = await get_db()
    today = date.today().isoformat()
    await db.daily_hits.update_one(
        {"user_id": user_id, "hit_date": today},
        {"$inc": {"count": 1}},
        upsert=True
    )
    return await get_daily_hits(user_id)


async def can_hit(user_id: int) -> tuple:
    if await is_admin(user_id):
        return True, None
    plan = await get_user_plan(user_id)
    if plan["unlimited"]:
        if plan["hits_per_day"] > 0:
            hits = await get_daily_hits(user_id)
            if hits >= plan["hits_per_day"]:
                return False, f"Daily limit reached ({plan['hits_per_day']}/day). Contact owner for upgrade!"
        return True, None
    hits = await get_daily_hits(user_id)
    remaining = FREE_DAILY_LIMIT - hits
    if remaining <= 0:
        return False, f"Daily limit reached ({FREE_DAILY_LIMIT}/day on Free plan). Contact owner for access!"
    return True, None


# ─── Logging ───

async def log_check(user_id: int, card: str, url: str, merchant: str, amount: str, status: str, response: str, time_taken: float):
    db = await get_db()
    await db.check_logs.insert_one({
        "user_id": user_id, "card": card, "checkout_url": url[:100],
        "merchant": merchant or "", "amount": amount or "",
        "status": status, "response": response or "",
        "time_taken": time_taken, "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def get_user_logs(user_id: int, limit: int = 20) -> list:
    db = await get_db()
    cursor = db.check_logs.find({"user_id": user_id}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_recent_charged_hits(limit: int = 20) -> list:
    db = await get_db()
    cursor = db.check_logs.find({"status": "CHARGED"}, {"_id": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_user_hit_stats(user_id: int) -> dict:
    db = await get_db()
    total = await db.check_logs.count_documents({"user_id": user_id})
    charged = await db.check_logs.count_documents({"user_id": user_id, "status": "CHARGED"})
    live = await db.check_logs.count_documents({"user_id": user_id, "status": "LIVE"})
    declined = await db.check_logs.count_documents({"user_id": user_id, "status": "DECLINED"})
    return {"total": total, "charged": charged, "live": live, "declined": declined}


# ─── Proxies ───

async def add_proxy(user_id: int, proxy: str):
    db = await get_db()
    try:
        await db.proxies.update_one(
            {"user_id": user_id, "proxy": proxy},
            {"$set": {"user_id": user_id, "proxy": proxy}},
            upsert=True
        )
        return True
    except Exception:
        return False


async def remove_proxy(user_id: int, proxy: str = None):
    db = await get_db()
    if proxy and proxy.lower() != "all":
        await db.proxies.delete_one({"user_id": user_id, "proxy": proxy})
    else:
        await db.proxies.delete_many({"user_id": user_id})


async def get_proxies(user_id: int) -> list:
    db = await get_db()
    cursor = db.proxies.find({"user_id": user_id}, {"_id": 0, "proxy": 1})
    rows = await cursor.to_list(length=100)
    return [r["proxy"] for r in rows]


# ─── Ranking ───

async def get_charged_ranking(limit: int = 10) -> list:
    db = await get_db()
    pipeline = [
        {"$match": {"status": "CHARGED"}},
        {"$group": {"_id": "$user_id", "charged_count": {"$sum": 1}}},
        {"$sort": {"charged_count": -1}},
        {"$limit": limit},
        {"$lookup": {"from": "users", "localField": "_id", "foreignField": "user_id", "as": "user_info"}},
        {"$unwind": {"path": "$user_info", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 0, "user_id": "$_id", "charged_count": 1,
            "username": {"$ifNull": ["$user_info.username", ""]},
            "first_name": {"$ifNull": ["$user_info.first_name", ""]},
        }}
    ]
    return await db.check_logs.aggregate(pipeline).to_list(length=limit)


# ─── Saved BINs ───

async def save_bin(user_id: int, name: str, bin_value: str) -> bool:
    db = await get_db()
    try:
        await db.saved_bins.update_one(
            {"user_id": user_id, "name": name.lower()},
            {"$set": {"user_id": user_id, "name": name.lower(), "bin_value": bin_value, "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        return True
    except Exception:
        return False


async def get_saved_bins(user_id: int) -> list:
    db = await get_db()
    cursor = db.saved_bins.find({"user_id": user_id}, {"_id": 0, "name": 1, "bin_value": 1}).sort("created_at", -1)
    return await cursor.to_list(length=50)


async def delete_saved_bin(user_id: int, name: str) -> bool:
    db = await get_db()
    await db.saved_bins.delete_one({"user_id": user_id, "name": name.lower()})
    return True


# ─── Redeem codes ───

async def create_redeem_code(plan_type: str, days: int, hits_per_day: int, max_uses: int, created_by: int) -> str:
    db = await get_db()
    chars = string.ascii_uppercase + string.digits
    code = "-".join("".join(secrets.choice(chars) for _ in range(4)) for _ in range(3))
    await db.redeem_codes.insert_one({
        "code": code, "plan_type": plan_type, "days": days,
        "hits_per_day": hits_per_day, "max_uses": max_uses,
        "used_count": 0, "created_by": created_by,
        "is_active": 1, "created_at": datetime.now(timezone.utc).isoformat()
    })
    return code


async def use_redeem_code(user_id: int, code: str) -> dict:
    db = await get_db()
    code = code.upper().strip()
    row = await db.redeem_codes.find_one({"code": code, "is_active": 1}, {"_id": 0})
    if not row:
        return {"success": False, "error": "Invalid or expired code"}
    if row["used_count"] >= row["max_uses"]:
        return {"success": False, "error": "Code already fully used"}
    already = await db.code_uses.find_one({"code": code, "user_id": user_id})
    if already:
        return {"success": False, "error": "You already used this code"}
    await db.code_uses.insert_one({"code": code, "user_id": user_id, "used_at": datetime.now(timezone.utc).isoformat()})
    await db.redeem_codes.update_one({"code": code}, {"$inc": {"used_count": 1}})
    if row["used_count"] + 1 >= row["max_uses"]:
        await db.redeem_codes.update_one({"code": code}, {"$set": {"is_active": 0}})
    hpd = row.get("hits_per_day") or 0
    await set_user_plan(user_id, row["plan_type"], row["days"], hpd)
    return {"success": True, "plan_type": row["plan_type"], "days": row["days"], "hits_per_day": hpd}


async def revoke_code(code: str) -> bool:
    db = await get_db()
    code = code.upper().strip()
    row = await db.redeem_codes.find_one({"code": code})
    if not row:
        return False
    await db.redeem_codes.update_one({"code": code}, {"$set": {"is_active": 0}})
    return True


async def get_active_codes() -> list:
    db = await get_db()
    cursor = db.redeem_codes.find({"is_active": 1}, {"_id": 0}).sort("created_at", -1).limit(20)
    return await cursor.to_list(length=20)


# ─── Stats ───

async def get_global_stats() -> dict:
    db = await get_db()
    users = await db.users.count_documents({"is_banned": 0})
    checks = await db.check_logs.count_documents({})
    charged = await db.check_logs.count_documents({"status": "CHARGED"})
    live = await db.check_logs.count_documents({"status": "LIVE"})
    banned = await db.users.count_documents({"is_banned": 1})
    active_codes = await db.redeem_codes.count_documents({"is_active": 1})
    return {"users": users, "checks": checks, "charged": charged, "live": live, "banned": banned, "active_codes": active_codes}


async def get_all_users() -> list:
    db = await get_db()
    pipeline = [
        {"$lookup": {"from": "user_plans", "localField": "user_id", "foreignField": "user_id", "as": "plan"}},
        {"$unwind": {"path": "$plan", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 0, "user_id": 1, "username": 1, "first_name": 1,
            "join_date": 1, "is_banned": 1, "proxy_mode": 1,
            "plan_type": {"$ifNull": ["$plan.plan_type", "free"]},
            "expiry_date": {"$ifNull": ["$plan.expiry_date", None]},
            "hits_per_day": {"$ifNull": ["$plan.hits_per_day", 0]},
        }},
        {"$sort": {"join_date": -1}}
    ]
    return await db.users.aggregate(pipeline).to_list(length=1000)


async def get_all_users_with_hits() -> list:
    db = await get_db()
    pipeline = [
        {"$lookup": {"from": "user_plans", "localField": "user_id", "foreignField": "user_id", "as": "plan"}},
        {"$unwind": {"path": "$plan", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "check_logs", "localField": "user_id", "foreignField": "user_id", "as": "hits"}},
        {"$project": {
            "_id": 0, "user_id": 1, "username": 1, "first_name": 1,
            "join_date": 1, "is_banned": 1, "proxy_mode": 1,
            "plan_type": {"$ifNull": ["$plan.plan_type", "free"]},
            "expiry_date": {"$ifNull": ["$plan.expiry_date", None]},
            "hits_per_day": {"$ifNull": ["$plan.hits_per_day", 0]},
            "total_hits": {"$size": "$hits"},
            "charged_hits": {"$size": {"$filter": {"input": "$hits", "as": "h", "cond": {"$eq": ["$$h.status", "CHARGED"]}}}},
        }},
        {"$sort": {"join_date": -1}}
    ]
    return await db.users.aggregate(pipeline).to_list(length=1000)


async def get_all_user_ids() -> list:
    db = await get_db()
    cursor = db.users.find({"is_banned": 0}, {"_id": 0, "user_id": 1})
    rows = await cursor.to_list(length=10000)
    return [r["user_id"] for r in rows]


async def get_user_info(user_id: int) -> dict:
    db = await get_db()
    row = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return row


async def get_setting(key: str, default=None):
    db = await get_db()
    row = await db.bot_settings.find_one({"key": key}, {"_id": 0, "value": 1})
    return row["value"] if row else default


async def set_setting(key: str, value: str):
    db = await get_db()
    await db.bot_settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value": value}},
        upsert=True
    )


async def close():
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


# ─── Admin role ───

async def add_admin(user_id: int):
    db = await get_db()
    await db.admins.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)


async def remove_admin(user_id: int):
    db = await get_db()
    await db.admins.delete_one({"user_id": user_id})


async def is_admin(user_id: int) -> bool:
    db = await get_db()
    return bool(await db.admins.find_one({"user_id": user_id}))


async def get_all_admins() -> list:
    db = await get_db()
    cursor = db.admins.find({}, {"_id": 0, "user_id": 1})
    rows = await cursor.to_list(length=100)
    return [r["user_id"] for r in rows]


# ─── Reset stats ───

async def reset_global_stats():
    db = await get_db()
    await db.check_logs.delete_many({})
    await db.daily_hits.delete_many({})


async def clear_daily_cache():
    db = await get_db()
    await db.daily_hits.delete_many({})


async def get_total_users_count() -> int:
    db = await get_db()
    return await db.users.count_documents({})
  
