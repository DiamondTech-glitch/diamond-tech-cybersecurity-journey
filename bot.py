"""
Personal AI Study Assistant — Telegram bot.
Uses assistant_core.py for memory + Claude calls. Keeps one ongoing
conversation thread per Telegram user (the sidebar/multi-thread UI is
a web-app-only feature — Telegram just gets one continuous chat).
"""

import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from assistant_core import (
    save_message, ask_claude, add_progress_note, recent_progress,
    list_conversations, create_conversation,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


def get_or_create_conversation(user_id: str) -> int:
    convs = list_conversations(user_id)
    if convs:
        return convs[0]["id"]
    return create_conversation(user_id, "Telegram chat")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I'm your personal study + coding assistant. Just message me "
        "anything — cybersecurity concepts, code you're stuck on, ideas "
        "to automate.\n\n"
        "Commands:\n"
        "/progress <note> — log what you covered today\n"
        "/summary — see your last week of progress"
    )


async def log_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = " ".join(context.args)
    if not note:
        await update.message.reply_text("Usage: /progress <what you covered>")
        return
    add_progress_note(f"tg-{update.effective_user.id}", note)
    await update.message.reply_text("Logged.")


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = recent_progress(f"tg-{update.effective_user.id}")
    if not rows:
        await update.message.reply_text("No progress logged yet.")
        return
    text = "\n".join(f"{day}: {note}" for day, note in rows)
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = f"tg-{update.effective_user.id}"
    user_text = update.message.text
    conv_id = get_or_create_conversation(user_id)

    save_message(conv_id, "user", user_text)
    await update.message.chat.send_action("typing")

    reply = ask_claude(user_id, conv_id, user_text)

    save_message(conv_id, "assistant", reply)
    await update.message.reply_text(reply)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("progress", log_progress))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()