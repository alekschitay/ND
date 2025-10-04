from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import List

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram import Router
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import get_settings
from .db import Database, Event
from .scraper import scrape_events

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("events_bot")


def format_event_message(ev: Event) -> str:
    parts = [
        f"{ev.event_url}",
    ]
    if ev.date_text:
        parts.append(f"Дата: {ev.date_text}")
    if ev.title:
        parts.append(f"Название: {ev.title}")
    return "\n".join(parts)


router = Router()


async def handle_subscribe(message: Message, command: CommandObject, db: Database):
    if not command.args:
        await message.reply("Укажи ссылку: /subscribe https://example.com/events")
        return
    url = command.args.strip()
    db.add_user(message.from_user.id)
    db.add_subscription(message.from_user.id, url)
    # Baseline: quietly index current items so user gets only future updates
    try:
        scraped = await scrape_events(url)
        events = [Event(event_url=s.event_url, title=s.title, date_text=s.date_text, image_url=s.image_url) for s in scraped]
        _ = db.record_new_events(url, events)
    except Exception:
        logger.exception("initial scrape failed for %s", url)
    await message.reply("Подписка добавлена. Учту существующие события и сообщу о новых.")


async def handle_unsubscribe(message: Message, command: CommandObject, db: Database):
    if not command.args:
        await message.reply("Укажи ссылку: /unsubscribe https://example.com/events")
        return
    url = command.args.strip()
    removed = db.remove_subscription(message.from_user.id, url)
    if removed:
        await message.reply("Подписка удалена.")
    else:
        await message.reply("Такой подписки нет.")


async def handle_list(message: Message, db: Database):
    subs = db.list_subscriptions(message.from_user.id)
    if not subs:
        await message.reply("У тебя нет подписок. Добавь: /subscribe <url>")
        return
    text = "Твои подписки:\n" + "\n".join(f"- {u}" for u in subs)
    await message.reply(text)


async def handle_start(message: Message):
    await message.reply(
        "Привет! Пришли ссылку раздела с событиями и подпишись.\n\n"
        "Команды:\n"
        "/subscribe <url> — подписаться на страницу\n"
        "/unsubscribe <url> — отписаться\n"
        "/list — список подписок"
    )


async def check_updates(bot: Bot, db: Database):
    urls = db.list_all_subscription_urls()
    if not urls:
        return
    for url in urls:
        try:
            scraped = await scrape_events(url)
        except Exception as e:
            logger.exception("scrape failed for %s", url)
            continue
        events = [Event(event_url=s.event_url, title=s.title, date_text=s.date_text, image_url=s.image_url) for s in scraped]
        new_events = db.record_new_events(url, events)
        if not new_events:
            continue
        user_ids = db.list_users_for_url(url)
        for user_id in user_ids:
            for ev in new_events:
                try:
                    text = format_event_message(ev)
                    if ev.image_url:
                        await bot.send_photo(chat_id=user_id, photo=ev.image_url, caption=text, parse_mode=ParseMode.HTML)
                    else:
                        await bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.HTML)
                except Exception:
                    logger.exception("send failed to %s", user_id)


async def main():
    settings = get_settings()
    db = Database(settings.database_path)

    bot = Bot(settings.telegram_bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    @router.message(Command(commands=["subscribe"]))
    async def _subscribe(message: Message, command: CommandObject):
        await handle_subscribe(message, command, db)

    @router.message(Command(commands=["unsubscribe"]))
    async def _unsubscribe(message: Message, command: CommandObject):
        await handle_unsubscribe(message, command, db)

    @router.message(Command(commands=["list"]))
    async def _list(message: Message):
        await handle_list(message, db)

    @router.message(Command(commands=["start", "help"]))
    async def _start(message: Message):
        await handle_start(message)

    dp.include_router(router)

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(lambda: asyncio.create_task(check_updates(bot, db)), "interval", minutes=settings.check_interval_minutes, id="check_updates", replace_existing=True)
    scheduler.start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
