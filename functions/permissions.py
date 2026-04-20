from config import OWNER_IDS
import database.db as db

async def is_admin(user_id):

    if user_id in OWNER_IDS:
        return True

    return await db.is_admin(user_id)


async def is_command_enabled(cmd):

    val = await db.get_setting(f"cmd_{cmd}", "on")

    return val != "off"
