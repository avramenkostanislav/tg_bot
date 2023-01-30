import os

import logging
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters
from books import get_all_books
import message_text

import sqlite3


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    exit('specify TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /start")
        return
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text=message_text.GREETINGS)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /help")
        return
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text=message_text.HELP)

async def all_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /allbooks")
        return
    categories_with_books = await get_all_books()
    for category in categories_with_books:
        response = "*" + category.name + "*\n\n"
        for index, book in enumerate(category.books,1):
            response += f"{index}. {book.name}\n"
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=response,
            parse_mode=telegram.constants.ParseMode.MARKDOWN)

if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)

    all_books_handler = CommandHandler("allbooks", all_books)
    application.add_handler(all_books_handler)

    application.run_polling()


#TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
#PATH = os.environ.get("OS")

