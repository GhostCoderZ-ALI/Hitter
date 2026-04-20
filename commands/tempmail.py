from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

import requests
import random
import string

import database.db as db
from config import OWNER_IDS

router = Router()

# user_id : {email:core}
user_emails = {}

# core1 tokens
core1_tokens = {}


async def is_admin(uid):
    if uid in OWNER_IDS:
        return True
    return await db.is_admin(uid)


def rand(n=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


# ---------------- CORE 1 ----------------

def core1_generate():

    API = "https://api.mail.tm"

    dom = requests.get(f"{API}/domains").json()["hydra:member"][0]["domain"]

    email = f"{rand()}@{dom}"

    pwd = rand(12)

    payload = {"address": email, "password": pwd}

    requests.post(f"{API}/accounts", json=payload)

    token = requests.post(f"{API}/token", json=payload).json()["token"]

    return email, token


def core1_inbox(token):

    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get("https://api.mail.tm/messages", headers=headers).json()

    msgs = r.get("hydra:member", [])

    result = []

    for m in msgs:

        mid = m["id"]

        d = requests.get(
            f"https://api.mail.tm/messages/{mid}",
            headers=headers
        ).json()

        subject = d.get("subject","No subject")
        body = d.get("text","")

        result.append(f"{subject}\n{body[:500]}")

    return result


# ---------------- CORE 2 ----------------

def core2_generate():

    r = requests.post(
        "https://api.internal.temp-mail.io/api/v3/email/new",
        json={"min_name_length":10,"max_name_length":12}
    ).json()

    return r.get("email")


def core2_inbox(email):

    r = requests.get(
        f"https://api.internal.temp-mail.io/api/v3/email/{email}/messages"
    ).json()

    result = []

    for m in r:

        subject = m.get("subject","No subject")
        body = m.get("body_text","")

        result.append(f"{subject}\n{body[:500]}")

    return result


# ---------------- CORE 3 ----------------

def core3_generate():

    email = requests.get(
        "https://priyo-mail-unofficial-api.vercel.app/api/gen"
    ).text.strip()

    return email


def core3_inbox(email):

    r = requests.get(
        f"https://priyo-mail-unofficial-api.vercel.app/api/inbox?email={email}"
    ).json()

    msgs = r.get("messages", [])

    result = []

    for m in msgs:

        subject = m.get("subject","No subject")
        body = m.get("body","")

        result.append(f"{subject}\n{body[:500]}")

    return result


# ---------------- LIMIT CHECK ----------------

async def check_limit(uid):

    if await is_admin(uid):
        return True

    can, reason = await db.can_hit(uid)

    return can


# ---------------- TEMP1 ----------------

@router.message(Command("temp1"))
async def temp1(msg: Message):

    uid = msg.from_user.id
    args = msg.text.split()

    if not await check_limit(uid):
        await msg.answer("Daily limit reached.")
        return

    if len(args) == 1:

        email, token = core1_generate()

        core1_tokens[email] = token

        user_emails.setdefault(uid,{})[email] = 1

        await msg.answer(f"CORE1 EMAIL\n\n{email}")

    else:

        email = args[1]

        if email not in user_emails.get(uid,{}):
            await msg.answer("You can only open your own email inbox.")
            return

        token = core1_tokens.get(email)

        mails = core1_inbox(token)

        if not mails:
            await msg.answer("Inbox empty.")
            return

        await msg.answer("\n\n".join(mails))


# ---------------- TEMP2 ----------------

@router.message(Command("temp2"))
async def temp2(msg: Message):

    uid = msg.from_user.id
    args = msg.text.split()

    if not await check_limit(uid):
        await msg.answer("Daily limit reached.")
        return

    if len(args) == 1:

        email = core2_generate()

        user_emails.setdefault(uid,{})[email] = 2

        await msg.answer(f"CORE2 EMAIL\n\n{email}")

    else:

        email = args[1]

        if email not in user_emails.get(uid,{}):
            await msg.answer("You can only open your own email inbox.")
            return

        mails = core2_inbox(email)

        if not mails:
            await msg.answer("Inbox empty.")
            return

        await msg.answer("\n\n".join(mails))


# ---------------- TEMP3 ----------------

@router.message(Command("temp3"))
async def temp3(msg: Message):

    uid = msg.from_user.id
    args = msg.text.split()

    if not await check_limit(uid):
        await msg.answer("Daily limit reached.")
        return

    if len(args) == 1:

        email = core3_generate()

        user_emails.setdefault(uid,{})[email] = 3

        await msg.answer(f"CORE3 EMAIL\n\n{email}")

    else:

        email = args[1]

        if email not in user_emails.get(uid,{}):
            await msg.answer("You can only open your own email inbox.")
            return

        mails = core3_inbox(email)

        if not mails:
            await msg.answer("Inbox empty.")
            return

        await msg.answer("\n\n".join(mails))
