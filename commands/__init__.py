from aiogram import Router

# Working commands
from commands.start import router as start_router
from commands.help import router as help_router
from commands.auth import router as auth_router      # /auth – Stripe checker
from commands.shopify import router as shopify_router # /sh – Shopify API checker

# Optional – keep these if they work for you (remove if not)
from commands.gen import router as gen_router
from commands.co import router as co_router
from commands.proxy import router as proxy_router
from commands.admin import router as admin_router
from commands.tempmail import router as temp_router
from commands.wallet import router as wallet_router
from commands.referral import router as ref_router

# Create main router
router = Router()

# Include only working routers
router.include_router(start_router)
router.include_router(help_router)
router.include_router(auth_router)
router.include_router(shopify_router)

# Optional (keep if they work)
router.include_router(gen_router)
router.include_router(co_router)
router.include_router(proxy_router)
router.include_router(admin_router)
router.include_router(temp_router)
router.include_router(wallet_router)
router.include_router(ref_router)
