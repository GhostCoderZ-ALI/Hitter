from config import FORCE_JOIN_CHANNEL

async def check_force_join(bot, user_id):

    try:

        member = await bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)

        if member.status in ["member","administrator","creator"]:
            return True

    except:
        pass

    return False
