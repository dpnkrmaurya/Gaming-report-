#!/usr/bin/env python3

import os
import sys
import time
import statistics
import threading
from collections import defaultdict
from datetime import datetime

from ping3 import ping

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================
ADMIN_IDS = {123456789}  # 🔴 Replace with your Telegram ID
TOKEN_FILE = "bot_token.txt"

# ================= TOKEN =================
def get_token():
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE).read().strip()
    token = input("Enter Telegram Bot Token: ")
    open(TOKEN_FILE, "w").write(token)
    return token

BOT_TOKEN = get_token()

# ================= SERVERS =================
SERVERS = {
    "india": {
        "BGMI": "www.pubgmobile.com",
        "FreeFire": "ff.garena.com",
        "COD": "www.callofduty.com",
        "ClashRoyale": "supercell.com"
    },
    "asia": {
        "BGMI": "asia.pubgmobile.com",
        "FreeFire": "ff.garena.com",
        "COD": "asia.callofduty.com",
        "ClashRoyale": "supercell.com"
    }
}

# ================= STORAGE =================
cooldowns = defaultdict(int)
lag_history = defaultdict(list)
LOG_FILE = "user_activity_log.txt"
log_lock = threading.Lock()

# ================= LOG SYSTEM =================
def log_user_data(update, command_used, region="N/A"):
    user = update.effective_user
    chat = update.effective_chat

    log_entry = (
        f"Time: {datetime.now()}\n"
        f"User ID: {user.id}\n"
        f"Username: @{user.username}\n"
        f"Chat Type: {chat.type}\n"
        f"Command: {command_used}\n"
        f"Region: {region}\n"
        + "="*50 + "\n"
    )

    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

# ================= COOLDOWN =================
def check_cooldown(user_id):
    now = time.time()
    if now - cooldowns[user_id] < 20:
        return False
    cooldowns[user_id] = now
    return True

# ================= NETWORK TEST =================
def packet_test(host, count=8):

    success = 0
    times = []

    for _ in range(count):
        delay = ping(host, timeout=2)
        if delay:
            success += 1
            times.append(delay * 1000)
        time.sleep(0.25)

    loss = ((count - success) / count) * 100
    jitter = statistics.stdev(times) if len(times) > 1 else 0
    avg_ping = statistics.mean(times) if times else None

    return round(loss,2), round(jitter,2), round(avg_ping,2) if avg_ping else None

# ================= GAMING SCORE =================
def gaming_score(ping, loss, jitter):

    if ping is None:
        return "❌ No Response"

    score = 100

    score -= ping * 0.5
    score -= loss * 5
    score -= jitter * 0.3

    score = max(0, round(score))

    if score >= 85:
        grade = "🏆 ESPORT READY"
    elif score >= 70:
        grade = "🟢 EXCELLENT"
    elif score >= 55:
        grade = "🟡 PLAYABLE"
    else:
        grade = "🔴 UNSTABLE"

    return f"{score}/100  {grade}"

# ================= LAG AI =================
def lag_prediction_engine(user_id, ping_val, loss, jitter):

    if ping_val is None:
        return "No Data"

    history = lag_history[user_id]
    history.append({"ping": ping_val, "loss": loss, "jitter": jitter})

    if len(history) > 6:
        history.pop(0)

    if len(history) < 4:
        return "Collecting data..."

    pings = [x["ping"] for x in history]
    variation = max(pings) - min(pings)

    risk = 0
    if variation > 40:
        risk += 1
    if jitter > 30:
        risk += 1
    if loss > 3:
        risk += 1

    if risk >= 2:
        return "🚨 Lag Spike Likely"
    return "🟢 Stable"

# ================= DASHBOARD =================
def generate_dashboard(user_id, region):

    output = f"🎮 GAMING NETWORK ANALYSIS\n🌍 Region: {region.upper()}\n\n"

    for game, host in SERVERS[region].items():

        loss, jitter, avg = packet_test(host)
        prediction = lag_prediction_engine(user_id, avg, loss, jitter)
        score = gaming_score(avg, loss, jitter)

        output += (
            f"🎯 {game}\n"
            f"Ping: {avg} ms\n"
            f"Packet Loss: {loss}%\n"
            f"Jitter: {jitter} ms\n"
            f"Gaming Score: {score}\n"
            f"Lag Prediction: {prediction}\n\n"
        )

    return output

# ================= MENU =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("🎮 Ultra Gaming Scan", callback_data="ultra")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]

    await update.message.reply_text(
        "🎮 Gaming Optimized Bot\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🎮 GAMING BOT HELP\n\n"
        "✔ Ultra Gaming Scan\n"
        "✔ Ping + Packet Loss\n"
        "✔ Jitter Analysis\n"
        "✔ Gaming Score\n"
        "✔ Lag Spike Prediction\n\n"
        "No Speedtest (Gaming optimized)"
    )

    if update.message:
        await update.message.reply_text(text)
    else:
        await update.callback_query.message.edit_text(text)

async def region_menu(query):

    keyboard = [
        [InlineKeyboardButton("🇮🇳 India", callback_data="india")],
        [InlineKeyboardButton("🌏 Asia", callback_data="asia")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]

    await query.message.edit_text(
        "🌍 Select Region:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "ultra":
        await region_menu(query)

    elif data == "help":
        await help_command(update, context)

    elif data == "back":
        await start(update, context)

    elif data in SERVERS:

        region = data

        if not check_cooldown(user_id):
            await query.message.edit_text("⏳ Please wait before next scan.")
            return

        await query.message.edit_text("🔎 Analyzing network...")

        result = generate_dashboard(user_id, region)

        await query.message.reply_text(result)

# ================= ADMIN LOG VIEW =================
async def view_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Unauthorized. Admin only.")
        return

    if not os.path.exists(LOG_FILE):
        await update.message.reply_text("No logs found.")
        return

    with open(LOG_FILE, "rb") as f:
        await update.message.reply_document(document=f)

# ================= MAIN =================
def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("logs", view_logs))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🎮 GAMING OPTIMIZED BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
