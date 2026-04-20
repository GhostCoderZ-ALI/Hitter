import time

cooldowns = {}

def check_cooldown(user_id, seconds):

    now = time.time()

    last = cooldowns.get(user_id,0)

    if now - last < seconds:
        return False

    cooldowns[user_id] = now

    return True
