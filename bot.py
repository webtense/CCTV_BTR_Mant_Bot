#!/usr/bin/env python3
import os, subprocess, datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv("/opt/CCTV_BTR_Mant_Bot/.env")
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text("🟢 Bot de mantenimiento listo. Usa /help")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text(
        "/estado — disco /CAM y uptime\n"
        "/ping — latido simple\n"
        "/help — esta ayuda"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(f"🏓 Pong {ts}")

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    try:
        df_cam = subprocess.check_output(["bash","-lc","df -hP /CAM | tail -n1"]).decode().strip()
        df_root= subprocess.check_output(["bash","-lc","df -hP / | tail -n1"]).decode().strip()
        up     = subprocess.check_output(["bash","-lc","uptime -p"]).decode().strip()
        msg = "📊 *Estado rápido*\n" \
              f"CAM: `{df_cam}`\n" \
              f"ROOT: `{df_root}`\n" \
              f"Uptime: `{up}`"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error en /estado: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("estado", estado))
    # Importante: NO metas esto dentro de asyncio.run. run_polling ya gestiona el loop.
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
