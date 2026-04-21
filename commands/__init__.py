from aiogram import Router

# Import all command routers
from commands.start import router as start_router
from commands.gen import router as gen_router
from commands.co import router as co_router
from commands.proxy import router as proxy_router
from commands.admin import router as admin_router
from commands.tempmail import router as temp_router
from commands.wallet import router as wallet_router
from commands.referral import router as ref_router
from commands.auth import router as auth_router
from commands.shopify import router as shopify_router
from commands.b3 import router as b3_router
from commands.rz import router as rz_router
from commands.auth1 import router as auth1_router
from commands.auth2 import router as auth2_router
from commands.st5 import router as st5_router
from commands.st1 import router as st1_router
from commands.adb import router as adb_router
from commands.cl import router as cl_router
from commands.help import router as help_router

# Create main router for commands package
router = Router()

# Include all routers
router.include_router(start_router)
router.include_router(gen_router)
router.include_router(co_router)
router.include_router(proxy_router)
router.include_router(admin_router)
router.include_router(temp_router)
router.include_router(wallet_router)
router.include_router(ref_router)
router.include_router(auth_router)
router.include_router(shopify_router)
router.include_router(b3_router)
router.include_router(rz_router)
router.include_router(auth1_router)
router.include_router(auth2_router)
router.include_router(st5_router)
router.include_router(st1_router)
router.include_router(adb_router)
router.include_router(cl_router)
router.include_router(help_router)
