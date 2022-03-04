import logging
import asyncio

from aiogram import Bot
from aiogram.types import BotCommand

from bot.register_handlers import register_handlers
from bot.config import bot, dp


async def set_commands(_bot: Bot):
    await _bot.set_my_commands([
        BotCommand(command="/settings", description="Настройки"),
        BotCommand(command="/rooms", description="Меню комнат"),
        BotCommand(command="/rules", description="Правила взаимодействия с ботом"),
    ])


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    logging.getLogger(__name__).error("Starting bot")

    register_handlers(dp)

    await set_commands(bot)
    await dp.start_polling()

asyncio.run(main())
