from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from bot.config import mongo_users


class AthanasiusReg(StatesGroup):
    registration = State()


async def reg_start(message: types.Message):
    if mongo_users.find_one({'_id': message.from_user.id}) is None:
        await message.answer("Как тебя зовут?")
        await AthanasiusReg.registration.set()
        return
    await message.answer("Ты уже зарегистрирован, так что подожди, шалунишка))")


async def registration(message: types.Message, state: FSMContext):
    if len(message.text) > 16:
        await message.answer(f"Введи другое имя, максимальная длина имени 16 символов)")
        return

    if mongo_users.find_one({'name': message.text}) is not None:
        await message.answer(f"Введи другое имя, имя <b>{message.text}</b> уже занято")
        return

    mongo_users.insert_one({
        '_id': message.from_user.id,
        'name': message.text,
        'tg': message.from_user.username,
        'settings': {
            'applies': {
                'card': True,
                'count': False,
                'count-red': False,
                'suits': True,
            },
            'focus-mode': False,
            'card-view': 'emoji',
            'chosen-room': 0,
            'focus-mode-messages': {},
        },
        'games': [],
    })

    await message.answer(
        "Поздравляю, ты успешно зарегистрирован! "
        "Ты можешь нажать /settings, чтоб посмотреть и поменять свои настройки."
    )

    await state.finish()


def register_handlers_reg(dp: Dispatcher):
    dp.register_message_handler(reg_start, commands="reg", state="*")
    dp.register_message_handler(registration, state=AthanasiusReg.registration)
