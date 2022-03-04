from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters.state import State, StatesGroup

import bot.keyboards as k

from bot.config import mongo_users, mongo_games


class Name(StatesGroup):
    input_new_name = State()


def get_applies(player_id: int, with_num: bool = False) -> str:
    __applies = mongo_users.find_one({'_id': player_id})['settings']['applies']
    _applies = [__applies[apply] for apply in __applies.keys()]
    applies_list = 'Подтверждения:\n'
    for i, text in enumerate(['Карты', 'Количества карт', 'Количества красных карт', 'Мастей карт']):
        applies_list += f'\n{i + 1}. ' + text + ': ' if with_num else '\n' + text + ': '
        applies_list += '<b>Включено</b>' if _applies[i] else '<b>Выключено</b>'
    return applies_list


def get_cards_view_with_example(player_id: int) -> str:
    return 'Хорошо, давай посмотрим на примерах как выглядят <b>оба вида</b> '\
           'и какой ты <b>выберешь</b>?'\
           '\n\n<b>text:</b>\n\n'\
           'Рука <b>1</b>:\n\n'\
           'Количество: <b>2</b>\n'\
           'Красные: <b>1</b>\n'\
           'Червы: <b>0</b> Буби: <b>1</b>\n'\
           'Чёрные: <b>1</b>\n'\
           'Пики: <b>0</b> Крести: <b>1</b>\n\n'\
           'Рука <b>2</b>:\n\n'\
           'Количество: <b>2</b>\n'\
           'Красные: <b>1</b>\n'\
           'Червы: <b>0</b> Буби: <b>1</b>\n'\
           'Чёрные: <b>2</b>\n'\
           'Пики: <b>1</b> Крести: <b>1</b>\n\n'\
           '<b>emoji</b>:\n\n'\
           'Рука 1:\n'\
           '🔴: 1 ⚫: 1\n'\
           '♦♣\n'\
           'Рука 2:\n'\
           '🔴: 1 ⚫: 2\n'\
           f"♦♠♠\n\nТекущая настройка: <b>{mongo_users.find_one({'_id': player_id})['settings']['card-view']}</b>"


def start_menu(player_id: int) -> str:
    user = mongo_users.find_one({'_id': player_id})
    focus_mode = 'Включен' if user['settings']['focus-mode'] else 'Выключен'
    try:
        game_title = mongo_games.find_one({'_id': user['settings']['chosen-room']})['title']
    except TypeError:
        game_title = 'Ещё не выбрана'
    return f'Тебя зовут <b>{user["name"]}</b>\n\n' \
           'Твои текущие настройки:\n\n' + get_applies(player_id=player_id)\
           + f"\n\nВид карт: <b>{mongo_users.find_one({'_id': player_id})['settings']['card-view']}</b>" \
             f'\nТекущая комната: <b>{game_title}</b>' \
             f'\nФокус-мод: <b>{focus_mode}</b>\n'\
           + '\nЧто будем менять?'


async def update_applies_text(message: types.Message, change: str):
    _settings = mongo_users.find_one({'_id': message.chat.id})['settings']
    _settings['applies'][change] = not _settings['applies'][change]
    mongo_users.update_one({'_id': message.chat.id}, {'$set': {'settings': _settings}})

    await message.edit_text(
        get_applies(player_id=message.chat.id, with_num=True),
        reply_markup=k.settings_applies_toggle()
    )


async def settings_start(message: types.Message):
    if mongo_users.find_one({'_id': message.from_user.id}) is None:
        await message.answer('Перед тем, как зайти в настройки, нажми /reg.')
        return
    await message.answer(start_menu(message.from_user.id), reply_markup=k.settings_menu())


async def settings(call: types.CallbackQuery):
    data = call.data.split('_')
    match data[1]:
        case 'name':
            await call.message.edit_text('Напиши своё новое имя.')
            await Name.input_new_name.set()
        case 'applies':
            if len(data) == 2:
                await call.message.edit_text(get_applies(call.message.chat.id), reply_markup=k.settings_applies())
            else:
                match data[2]:
                    case 'toggle':
                        if len(data) == 3:
                            await call.message.edit_text(
                                get_applies(call.message.chat.id, with_num=True),
                                reply_markup=k.settings_applies_toggle()
                            )
                        else:
                            if data[3] == 'back':
                                await call.message.edit_text(
                                    get_applies(call.message.chat.id),
                                    reply_markup=k.settings_applies()
                                )
                            else:
                                await update_applies_text(call.message, data[3])
                    case 'onAll':
                        _settings = mongo_users.find_one({'_id': call.message.chat.id})['settings']
                        for key in _settings['applies'].keys():
                            _settings['applies'][key] = True
                        mongo_users.update_one({'_id': call.message.chat.id}, {'$set': {'settings': _settings}})
                        try:
                            await call.message.edit_text(
                                get_applies(call.message.chat.id),
                                reply_markup=k.settings_applies()
                            )
                        except MessageNotModified:
                            pass
                    case 'offAll':
                        _settings = mongo_users.find_one({'_id': call.message.chat.id})['settings']
                        for key in _settings['applies'].keys():
                            _settings['applies'][key] = False
                        mongo_users.update_one({'_id': call.message.chat.id}, {'$set': {'settings': _settings}})
                        try:
                            await call.message.edit_text(
                                get_applies(call.message.chat.id),
                                reply_markup=k.settings_applies()
                            )
                        except MessageNotModified:
                            pass
                    case 'back':
                        await call.message.edit_text(start_menu(call.message.chat.id), reply_markup=k.settings_menu())
        case 'cardsView':
            if len(data) == 2:
                await call.message.edit_text(
                    get_cards_view_with_example(call.message.chat.id),
                    reply_markup=k.settings_cards_view()
                )
            else:
                match data[2]:
                    case 'text':
                        _settings = mongo_users.find_one({'_id': call.message.chat.id})['settings']
                        _settings['card_view'] = 'text'
                        mongo_users.update_one({'_id': call.message.chat.id}, {'$set': {'settings': _settings}})
                        try:
                            await call.message.edit_text(
                                get_cards_view_with_example(call.message.chat.id),
                                reply_markup=k.settings_cards_view()
                            )
                        except MessageNotModified:
                            pass
                    case 'emoji':
                        _settings = mongo_users.find_one({'_id': call.message.chat.id})['settings']
                        _settings['card_view'] = 'emoji'
                        mongo_users.update_one({'_id': call.message.chat.id}, {'$set': {'settings': _settings}})
                        try:
                            await call.message.edit_text(
                                get_cards_view_with_example(call.message.chat.id),
                                reply_markup=k.settings_cards_view()
                            )
                        except MessageNotModified:
                            pass
                    case 'back':
                        await call.message.edit_text(start_menu(call.message.chat.id), reply_markup=k.settings_menu())
        case 'room':
            try:
                match data[2]:
                    case 'back':
                        await call.message.edit_text(start_menu(call.message.chat.id), reply_markup=k.settings_menu())
                    case _:
                        user = mongo_users.find_one({'_id': call.message.chat.id})
                        user['settings']['chosen-room'] = int(data[2])
                        mongo_users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
                        await call.message.edit_text(start_menu(call.message.chat.id), reply_markup=k.settings_menu())
            except IndexError:
                await call.message.edit_text('Выбери комнату.', reply_markup=k.settings_room(call.message.chat.id))
        case 'focusMode':
            user = mongo_users.find_one({'_id': call.message.chat.id})
            turns = ''
            if user['settings']['focus-mode']:
                for room_title in user['settings']['focus-mode-messages'].keys():
                    turns += f'Игра: <b>{room_title}</b>\n\n{user["settings"]["focus-mode-messages"][room_title]}\n\n'
                keys_to_delete = [key for key in user['settings']['focus-mode-messages'].keys()]
                for key in keys_to_delete:
                    user["settings"]["focus-mode-messages"].pop(key)
            if len(turns) != 0:
                await call.message.answer(turns)
            user['settings']['focus-mode'] = not user['settings']['focus-mode']
            mongo_users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
            await call.message.edit_text(start_menu(call.message.chat.id), reply_markup=k.settings_menu())
        case 'exit':
            await call.message.edit_text('Удачи!')
    await call.answer()


async def input_new_name(message: types.Message, state: FSMContext):
    user = mongo_users.find_one({'_id': message.from_user.id})
    if len(message.text) > 16:
        await message.answer(f"Введи другое имя, максимальная длина имени 16 символов.")
        return

    if user['name'].lower() == message.text.lower():
        await message.answer(f"Тебя уже так зовут, придумай что-нибудь пооригинальнее.")
        return

    if mongo_users.find_one({'name': message.text}) is not None:
        await message.answer(f"Введи другое имя, имя <b>{message.text}</b> уже занято")
        return

    user['name'] = message.text
    mongo_users.update_one({'_id': user['_id']}, {'$set': {'name': user['name']}})
    await message.answer(f'Успешно сменил твоё имя, теперь тебя зовут <b>{message.text}</b>')
    await state.finish()


def register_handlers_settings(dp: Dispatcher):
    dp.register_message_handler(settings_start, commands="settings")
    dp.register_message_handler(input_new_name, state=Name.input_new_name)
    dp.register_callback_query_handler(settings, Text(startswith='settings'))
