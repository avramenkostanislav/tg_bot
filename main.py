import asyncio
from datetime import datetime
import os
import re

import logging
import telegram
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    CommandHandler,
    filters
)

import config
from books import (
    get_all_books,
    get_already_read_books,
    get_now_reading_book,
    get_not_started_books,
    get_books_by_numbers
)
from votings import (
    get_actual_voting,
    save_vote,
    get_leaders
)
import message_text


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

async def already(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /help")
        return
    already_read_books = await get_already_read_books()
    response = "Прочитанные книги:\n\n"
    for index, book in enumerate(already_read_books, 1):
        response += (f"{index}. {book.name} "
                     f"(читали с {book.read_start} по {book.read_finish})\n")
    await context.bot.send_message(
            chat_id=effective_chat.id,
            text=response)

async def now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /help")
        return
    now_read_books = await get_now_reading_book()
    response = "Сейчас мы читаем:\n\n"
    just_one_book = len(now_read_books) == 1
    for index, book in enumerate(now_read_books, 1):
        response += (f"{str(index) + '. ' if just_one_book else ''}. {book.name} "
                     f"(читали с {book.read_start} по {book.read_finish})\n")
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=response)

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /allbooks")
        return
    if await get_actual_voting() is None:
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=message_text.NO_ACTUAL_VOTING,
            parse_mode=telegram.constants.ParseMode.MARKDOWN)
        return

    categories_with_books = await get_not_started_books()
    index = 1
    for category in categories_with_books:
        response = "*" + category.name + "*\n\n"
        for book in category.books:
            response += f"{index}. {book.name}\n"
            index += 1
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=response,
            parse_mode=telegram.constants.ParseMode.MARKDOWN)
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text=message_text.VOTE,
        parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def vote_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /allbooks")
        return

    if await get_actual_voting() is None:
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=message_text.NO_ACTUAL_VOTING,
            parse_mode=telegram.constants.ParseMode.MARKDOWN)
        return

    user_message = update.message.text
    numbers = re.findall(r"\d+", user_message)
    if len(tuple(set(map(int, numbers)))) != config.VOTE_ELEMENTS_COUNT:
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=message_text.VOTE_PROCESS_INCORRECT_INPUT,
            parse_mode=telegram.constants.ParseMode.MARKDOWN)
        return
    books = await get_books_by_numbers(numbers)
    if len(books) != config.VOTE_ELEMENTS_COUNT:
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=message_text.VOTE_PROCESS_INCORRECT_BOOKS,
            parse_mode=telegram.constants.ParseMode.MARKDOWN)
        return

    await save_vote(update.effective_user.id, books)

    response = "Ура, ты выбрал три книги:\n\n"
    for index, book in enumerate(books, 1):
        response += f"{index}. {book.name}\n"
    await context.bot.send_message(
        chat_id=effective_chat.id,
        text=response,
        parse_mode=telegram.constants.ParseMode.MARKDOWN)


async def vote_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effective_chat = update.effective_chat
    if not effective_chat:
        logger.warning("effective_chat is None in /allbooks")
        return
    leaders = await get_leaders()
    if leaders is None:
        await context.bot.send_message(
            chat_id=effective_chat.id,
            text=message_text.NO_VOTE_RESULT,
            parse_mode=telegram.constants.ParseMode.MARKDOWN)
        return

    response = "ТОП 10 книг голосования:\n\n"
    for index, book in enumerate(leaders.leaders, 1):
        response += f"{index}. {book.book_name} с рейтингом {book.score}\n"
    response += f"\nДаты голосования: с {leaders.voting.voting_start} по {leaders.voting.voting_finish}"
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

    already_handler = CommandHandler("already", already)
    application.add_handler(already_handler)

    now_handler = CommandHandler("now", now)
    application.add_handler(now_handler)

    vote_handler = CommandHandler("vote", vote)
    application.add_handler(vote_handler)

    vote_process_handler = MessageHandler(
        filters.TEXT
        & (~filters.COMMAND),
        vote_process)
    application.add_handler(vote_process_handler)

    vote_results_handler = CommandHandler("voteresults", vote_results)
    application.add_handler(vote_results_handler)

    application.run_polling()


#TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
#PATH = os.environ.get("OS")

