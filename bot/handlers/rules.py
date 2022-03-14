from aiogram import Dispatcher, types

import bot.scripts as sc
# import bot.keyboards as k


async def rules_start(message: types.Message):
    await message.answer(sc.get_rules())


def register_handlers_rules(dp: Dispatcher):
    dp.register_message_handler(rules_start, commands="rules")
