"""Entry point for the Telegram event monitoring bot."""
from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, Router, html
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message, URLInputFile

from .config import settings
from .db import Database, Watcher
from .monitor import WatcherMonitor
from .parser import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


def _validate_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme in {"http", "https"} and parsed.netloc)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! Пришли команду /watch <ссылка> чтобы подписаться на обновления афиши.\n"
        "Для отмены подписи используй /unwatch <ссылка>.\n"
        "Команда /list покажет текущие подписки."
    )
    await message.answer(text)


@router.message(Command("watch"))
async def cmd_watch(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Укажи ссылку после команды, например: /watch https://example.com")
        return
    url = command.args.strip()
    if not _validate_url(url):
        await message.answer("Некорректная ссылка. Поддерживаются только http/https URL.")
        return
    watcher = await message.bot["db"].add_watcher(message.from_user.id, url)
    await message.bot["monitor"].add_watcher(watcher)
    await message.answer(f"Добавил мониторинг страницы: {url}")


@router.message(Command("unwatch"))
async def cmd_unwatch(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Укажи ссылку, от которой нужно отписаться.")
        return
    url = command.args.strip()
    removed = await message.bot["db"].remove_watcher(message.from_user.id, url)
    if not removed:
        await message.answer("У тебя нет такой подписки.")
        return
    await message.bot["monitor"].remove_watcher(removed.id)
    await message.answer(f"Мониторинг для {url} остановлен.")


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    watchers = await message.bot["db"].list_watchers(message.from_user.id)
    if not watchers:
        await message.answer("Подписок пока нет. Добавь их через /watch <ссылка>.")
        return
    text_lines = ["Текущие подписки:"]
    for watcher in watchers:
        text_lines.append(f"• {watcher.url}")
    await message.answer("\n".join(text_lines))


async def send_event(bot: Bot, watcher: Watcher, event: Event) -> None:
    parts = []
    if event.title:
        parts.append(html.bold(event.title))
    if event.date_text:
        parts.append(f"📅 {html.quote(event.date_text)}")
    parts.append(html.link("Открыть сайт", event.link))
    caption = "\n".join(parts)

    if event.title:
        await bot.send_message(
            watcher.user_id,
            caption,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )
    elif event.image_url:
        await bot.send_photo(
            watcher.user_id,
            photo=URLInputFile(event.image_url),
            caption=caption,
            parse_mode=ParseMode.HTML,
        )
    else:
        await bot.send_message(
            watcher.user_id,
            caption,
            parse_mode=ParseMode.HTML,
        )


async def main() -> None:
    db = Database(settings.database_path)
    await db.connect()

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)

    async def _send_callback(watcher: Watcher, event: Event) -> None:
        await send_event(bot, watcher, event)

    monitor = WatcherMonitor(db=db, send_callback=_send_callback)
    bot["db"] = db
    bot["monitor"] = monitor

    async with AsyncExitStack() as stack:
        await monitor.start()
        stack.push_async_callback(monitor.stop)
        await stack.enter_async_context(bot.session)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
