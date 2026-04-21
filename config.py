import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "App Na Daaal Na MC")
OWNER_IDS = [int(x.strip()) for x in os.getenv("OWNER_IDS"," MC Mai Good Shadow Huu ").split(",") if x.strip()]

LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "")
FORCE_JOIN_CHANNELS = [x.strip() for x in os.getenv("FORCE_JOIN_CHANNELS", "").split(",") if x.strip()]
FORCE_JOIN_LINKS = [x.strip() for x in os.getenv("FORCE_JOIN_LINKS", "").split(",") if x.strip()]

MINI_APP_URL = os.getenv("MINI_APP_URL", "")

BIN_API_URL = "https://bindb.rythampkhandelwal.workers.dev/bin/{bin}"

BOT_NAME = "Deven Hitter"
BOT_USERNAME = "codevenbot"
SUPPORT_USERNAME = "@hqdeven"
OWNER_USERNAME = "@hqdeven"

FREE_DAILY_LIMIT = 5

# System-level proxy pool — used when a user has no personal proxy set.
# Paid users should add their own proxy; free users rotate through these.
SYSTEM_PROXIES = [
    "geo.g-w.info:10080:j1ZAX5jRDN54bU31:kV0bwE8IYByihLls",
    "geo.g-w.info:10080:BWwQZ5bFRqnWmKPm:Qj23ViSE8V90lRaZ",
    "geo.g-w.info:10080:ronCANdBwfj1rzaV:4EjkKwoKREPgEmSh",
    "geo.g-w.info:10080:vSbUtrs0BQPcUM75:PjcT7AWg2onuysF7",
    "geo.g-w.info:10080:KJweQKzGVBvXjmN5:LS8A5YUWXuH2UFUf",
    "geo.g-w.info:10080:DUCdmEg4jbqsQiZ7:vT7wSnt7Gl47cOyb",
    "geo.g-w.info:10080:Cq5X15wjTYufCsid:ahLoNIrYuJpKF2SS",
    "geo.g-w.info:10080:Z5RcVujYO0Oy2qHw:hpuMrTLd3XsuDzjV",
    "geo.g-w.info:10080:DML3AlYhtC7mTt77:edO1JU9tFG8CPrP6",
    "geo.g-w.info:10080:x9OjMx5b76kJlVim:WdYTukGZf3wEA61G",
    "geo.g-w.info:10080:Zn8U8mvLe89v2WOM:aPAGRoYloAFfwbA3",
    "geo.g-w.info:10080:eBAqrXDQ3ZL8qR1w:oEoJVgHxT7FqvCpT",
    "geo.g-w.info:10080:yD78uiRfg9cLiBie:JsoFIhHVE9oNep8t",
    "geo.g-w.info:10080:jF2Wplk0oth9MNPy:vcEfwVVjPZaB9ezE",
    "geo.g-w.info:10080:38K9vLWph46nkMdB:jN4yJ0tlR2Z4L3OA",
    "geo.g-w.info:10080:7ly64bRZ9BWkxeC7:7iUcyzNy2RzSzpih",
    "geo.g-w.info:10080:BcdfOyftUkpCBWYV:BorY8dfAK5gx3ZzV",
    "geo.g-w.info:10080:LirCtV6QTsI9dFFo:l6Z6YyDGhdGq9z1G",
    "geo.g-w.info:10080:7QXwCz8xf8ihXuoD:74D9KhSZ57hqFgIB",
    "geo.g-w.info:10080:xwU5EEa4MwJH7GQE:gfZkUeZuyoQUGM5z",
]

PLAN_PRICES = {
    "1d":    {"days": 1,    "label": "1 Day"},
    "3d":    {"days": 3,    "label": "3 Days"},
    "7d":    {"days": 7,    "label": "7 Days"},
    "14d":   {"days": 14,   "label": "14 Days"},
    "30d":   {"days": 30,   "label": "30 Days"},
    "60d":   {"days": 60,   "label": "60 Days"},
    "90d":   {"days": 90,   "label": "90 Days"},
    "180d":  {"days": 180,  "label": "180 Days"},
    "365d":  {"days": 365,  "label": "365 Days"},
}


DB_PATH = os.getenv("DB_PATH", "")
