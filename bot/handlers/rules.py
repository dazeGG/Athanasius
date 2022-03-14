from aiogram import Dispatcher, types

import bot.keyboards as k
import bot.scripts as sc

from bot.config import bot, mongo_users, mongo_games


def register_handlers_rules(dp: Dispatcher):
    dp.register_message_handler(start, commands="rules")
