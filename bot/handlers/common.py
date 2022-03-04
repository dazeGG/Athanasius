from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import IDFilter, Text
from aiogram.dispatcher.filters.state import State, StatesGroup

import bot.keyboards as k
import bot.scripts as sc

from bot.config import bot, mongo_users, mongo_games


class Note(StatesGroup):
    input_note = State()


async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        'Привет, я бот для автоматизированной игры в "Афанасий".',
        reply_markup=types.ReplyKeyboardRemove()
    )
    await message.answer('Нажми /reg для регистрации.')


async def admin_panel(message: types.Message):
    await message.answer("ФОКУС МОД", reply_markup=k.admin_focus_mode())
    await message.delete()


async def admin_focus_mode(call: types.CallbackQuery):
    data = call.data.split('_')
    user = mongo_users.find_one({'_id': call.message.chat.id})
    match data[1]:
        case 'vkl':
            user['settings']['focus-mode'] = True
        case 'vikl':
            user['settings']['focus-mode'] = False
    mongo_users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
    await call.message.delete()


async def cards_list(message: types.Message):
    await message.delete()
    game = mongo_games.find_one(
        {'_id': mongo_users.find_one({'_id': message.from_user.id})['settings']['chosen-room']})
    if game['active']:
        player_cards = game['cards'][str(message.from_user.id)]
        for hand in player_cards.keys():
            if len(player_cards[hand]) != 0:
                break
        else:
            await message.answer('У тебя нет карт. Подожди пока игра закончится)')
            return
        await message.answer(
            'Количество каких карт ты хочешь узнать?',
            reply_markup=k.card_menu(game, message.from_user.id, f'myCards_{game["_id"]}')
        )


async def find_cards(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    game = mongo_games.find_one({'_id': game_id})
    card = data[2]
    await call.message.edit_text(sc.get_card_info(game, call.message.chat.id, card))


async def whose_turn(message: types.Message):
    await message.delete()
    game = mongo_games.find_one(
        {'_id': mongo_users.find_one({'_id': message.from_user.id})['settings']['chosen-room']})
    user_whose_turn_name = mongo_users.find_one({'_id': game['queue'][0]})['name']
    if game['active']:
        await message.answer(f'Ход игрока <b>{user_whose_turn_name}</b>')
    else:
        await message.answer(f'Ход найти не удалось. Посмотри в настройках ту ли комнату ты выбрал.')


async def athanasias_list(message: types.Message):
    await message.delete()
    try:
        game = mongo_games.find_one(
            {'_id': mongo_users.find_one({'_id': message.from_user.id})['settings']['chosen-room']})
        if game['active']:
            message_to_out = ''
            has_someone_athanasius = False

            for player_id in game['athanasias'].keys():
                if len(game['athanasias'][player_id]) != 0:
                    has_someone_athanasius = True

            if has_someone_athanasius:
                for player_id in game['athanasias'].keys():
                    user_name = mongo_users.find_one({'_id': int(player_id)})['name']
                    message_to_out += f'<b>{user_name}'
                    for card in game['athanasias'][player_id]:
                        message_to_out += ' | ' + sc.change(card)
                    message_to_out += '</b>\n\n'
            else:
                message_to_out = 'Пока что <b>ни у кого</b> нет Афанасиев)'
            await message.answer(message_to_out)
    except TypeError:
        await message.answer('Что-то пошло не так...\n'
                             'Возможно ты не выбрал комнату в настройках, <b>обязательно</b> проверь.')


async def notes(message: types.Message):
    await message.delete()
    game = mongo_games.find_one(
        {'_id': mongo_users.find_one({'_id': message.from_user.id})['settings']['chosen-room']})
    await message.answer('Выбери карту к которой добавить заметки', reply_markup=k.notes_card_choose(game))


async def notes_card(call: types.CallbackQuery):
    data = call.data.split('_')
    room_id = int(data[1])
    user = mongo_users.find_one({'_id': call.message.chat.id})
    room = mongo_games.find_one({'_id': room_id})
    match len(data):
        case 3:
            match data[2]:
                case 'back':
                    await call.message.edit_text(
                        text='Выбери карту к которой добавить заметки',
                        reply_markup=k.notes_card_choose(room)
                    )
                case _:
                    await call.message.edit_text(
                        text=f'Карта: {sc.change(data[2])}',
                        reply_markup=k.notes(room, call.message.chat.id, data[2])
                    )
        case 5:
            await call.message.delete()
            await call.message.answer(
                text='Напиши мне, что туда вписать.',
                reply_markup=k.players_names_for_notes(room, call.message.chat.id)
            )
            mongo_users.update_one({'_id': user['_id']}, {'$set': {
                'note': [room_id, data[2], int(data[3]), int(data[4])]}})
            await Note.input_note.set()


async def input_note(message: types.Message, state: FSMContext):
    user = mongo_users.find_one({'_id': message.from_user.id})
    room_id, card, i, j = user['note'][0], user['note'][1], user['note'][2], user['note'][3]
    mongo_users.update_one({'_id': user['_id']}, {'$unset': {'note': ''}})
    room = mongo_games.find_one({'_id': room_id})
    room['notes'][str(message.from_user.id)][card][i][j] = message.text
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'notes': room['notes']}})
    await message.answer('Успешно добавил заметку!', reply_markup=k.default_menu())
    await message.answer(f'Карта: {sc.change(card)}', reply_markup=k.notes(room, message.from_user.id, card))
    await state.finish()


async def add_player(message: types.Message):
    user = mongo_users.find_one({'_id': message.from_user.id})
    if user is None:
        await message.answer(f'Сначала зарегистрируйся.')
        return
    for game in mongo_games.find():
        if message.text == game['code-to-add']:
            user['games'].append(game['_id'])
            mongo_users.update_one({'_id': user['_id']}, {'$set': {'games': user['games']}})

            for player_id in game['players-ids']:
                await bot.send_message(player_id, f'У нас новый игрок! Его зовут <b>{user["name"]}</b>.')

            game['players-ids'].append(message.from_user.id)

            mongo_games.update_one({'_id': game['_id']}, {'$set': {'players-ids': game['players-ids']}})

            await message.answer(f'Успешно добавил тебя в игру <b>{game["title"]}</b>.')
            return


def register_handlers_common(dp: Dispatcher, admin_ids: list):
    dp.register_message_handler(start, commands="start")
    dp.register_message_handler(admin_panel, IDFilter(user_id=admin_ids), commands="admin")
    dp.register_callback_query_handler(admin_focus_mode, Text(startswith='admin_'))
    dp.register_message_handler(cards_list, text="Мои карты")
    dp.register_callback_query_handler(find_cards, Text(startswith='myCards'))
    dp.register_message_handler(whose_turn, text="Чей ход")
    dp.register_message_handler(athanasias_list, text="Афанасии")
    dp.register_message_handler(notes, IDFilter(user_id=admin_ids), text="Заметки")
    dp.register_callback_query_handler(notes_card, Text(startswith='notes_'))
    dp.register_message_handler(input_note, state=Note.input_note)
    dp.register_message_handler(add_player)
