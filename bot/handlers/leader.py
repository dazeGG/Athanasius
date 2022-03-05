from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters.state import State, StatesGroup

import bot.scripts as sc
import bot.keyboards as k

from bot.config import bot, mongo_users, mongo_games


class GameTitle(StatesGroup):
    input_game_title = State()


class NewGameTitle(StatesGroup):
    input_new_game_title = State()


def game_menu(_game: {}) -> str:
    is_playing = 'Now playing' if _game['active'] else 'Not started'
    return f'<b>{_game["title"]}</b>\n{is_playing}\n\n<b>Настройки: </b>\n\n' + sc.settings(_game)


async def change_text(call: types.CallbackQuery, new_text: str, new_keyboard: types.InlineKeyboardMarkup = None):
    try:
        if new_keyboard is None:
            await call.message.edit_text(text=new_text)
        else:
            await call.message.edit_text(text=new_text, reply_markup=new_keyboard)
    except MessageNotModified:
        pass


async def start(message: types.Message):
    playing_games_ids = mongo_users.find_one({'_id': message.from_user.id})['games']
    games = [mongo_games.find_one({'_id': game_id}) for game_id in playing_games_ids]
    if len(games) == 0:
        await message.answer('У тебя пока нет комнат. Хочешь создать?', reply_markup=k.leader_create())
    else:
        await message.answer('Выбери комнату.', reply_markup=k.leader_choose_game(games))


async def start_menu(call: types.CallbackQuery):
    data = call.data.split('_')
    match data[1]:
        case 'yes' | 'create':
            await call.message.edit_text('Хорошо напиши мне какое название ты хочешь дать комнате.')
            await GameTitle.input_game_title.set()
        case 'no' | 'out':
            await call.message.edit_text('Ладно.')
    await call.answer()


async def input_game_title(message: types.Message, state: FSMContext):
    room_id = sc.set_new_game_id()
    games = mongo_users.find_one({'_id': message.from_user.id})['games']
    games.append(room_id)
    mongo_users.update_one({'_id': message.from_user.id}, {'$set': {'games': games}})
    mongo_games.insert_one({
        '_id': room_id,
        'title': message.text,
        'active': False,
        'code-to-add': sc.generate_code_to_add(),
        'leader-id': message.from_user.id,
        'players-ids': [message.from_user.id],
        'queue': [message.from_user.id],
        'config': {
            'count-of-decks': 4,
            'type-of-deck': 36,
            'count-of-hands': 2,
        },
        'cards': {},
        'athanasias': {},
        'chosen': {
            'player-id': 0,
            'card': '',
            'count': 1,
            'count-red': 0,
            'suits': {
                'Червы': 0,
                'Буби': 0,
                'Пики': 0,
                'Крести': 0,
            },
            'suitable-cards': {},
            'notes': {},
        },
    })
    await message.answer('Успешно создал комнату. Нажми /rooms чтобы посмотреть список своих комнат.')
    await state.finish()


async def input_new_game_title(message: types.Message, state: FSMContext):
    user = mongo_users.find_one({'_id': message.from_user.id})
    room_id = user['settings']['changing-room-id']
    user['settings'].pop('changing-room-id')
    mongo_users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
    mongo_games.update_one({'_id': room_id}, {'$set': {'title': message.text}})
    room = mongo_games.find_one({'_id': room_id})
    await message.answer(f'Успешно изменил имя комнаты на <b>{message.text}</b>.')
    await message.answer(game_menu(room), reply_markup=k.leader_game_menu(room, message.from_user.id))
    await state.finish()


async def game(call: types.CallbackQuery):
    data = call.data.split('_')

    room_id = int(data[2])
    room = mongo_games.find_one({'_id': room_id})

    match len(data):
        case 3:
            await change_text(call, game_menu(room), k.leader_game_menu(room, call.message.chat.id))
        case 4:
            match data[3]:
                case 'back':
                    playing_games_ids = mongo_users.find_one({'_id': call.message.chat.id})['games']
                    leader_games = [mongo_games.find_one({'_id': game_id}) for game_id in playing_games_ids]
                    await change_text(call, 'Выбери комнату.', k.leader_choose_game(leader_games))
                case 'start':
                    await call.message.delete()

                    sc.card_distributor(room)
                    sc.make_notes(room)
                    sc.shuffle_players(room)

                    mongo_games.update_one({'_id': room_id}, {'$set': {'active': True}})
                    room = mongo_games.find_one({'_id': room_id})

                    settings = 'Выбранные настройки игры:\n\n' + sc.settings(room)

                    for player_id in room['players-ids']:
                        await bot.send_message(
                            player_id,
                            f'Игра началась, удачи!\n\n{settings}',
                            reply_markup=k.default_menu()
                        )

                    await sc.athanasius_early_check(room)
                    await sc.turn(room)
                case 'end':
                    await change_text(call, 'ТОЧНО????', k.leader_end(room_id))
                case 'delete':
                    for player_id in room['players-ids']:
                        player = mongo_users.find_one({'_id': player_id})
                        player['games'].pop(player['games'].index(room['_id']))
                        player['settings']['chosen-room'] = 0
                        mongo_users.update_one(
                            {'_id': player['_id']},
                            {'$set': {'games': player['games'], 'settings': player['settings']}}
                        )
                    mongo_games.delete_one({'_id': room['_id']})
                    await call.message.edit_text(f'Успешно удалил комнату <b>{room["title"]}</b>.')
    await call.answer()


def change_count(_game: {}, change: int):
    cfg = _game['config']
    cfg['count-of-decks'] += change
    mongo_games.update_one({'_id': _game['_id']}, {'$set': {'config': cfg}})


def change_hands(_game: {}, change: int):
    cfg = _game['config']
    cfg['count-of-hands'] = change
    mongo_games.update_one({'_id': _game['_id']}, {'$set': {'config': cfg}})


def change_type(_game: {}, change: int):
    cfg = _game['config']
    cfg['type-of-deck'] = change
    mongo_games.update_one({'_id': _game['_id']}, {'$set': {'config': cfg}})


def delete_player(_game: {}, player_id: int):
    _game['players-ids'].pop(_game['players-ids'].index(player_id))
    mongo_games.update_one({'_id': _game['_id']}, {'$set': {'players-ids': _game['players-ids']}})
    user = mongo_users.find_one({'_id': player_id})
    user['games'].pop(user['games'].index(_game['_id']))
    mongo_users.update_one({'id': player_id}, {'$set': {'games': user['games']}})


async def game_configuration(call: types.CallbackQuery):
    data = call.data.split('_')

    room_id = int(data[2])
    room = mongo_games.find_one({'_id': room_id})

    match len(data):
        case 3:
            await change_text(call, sc.settings(room) + '\n\n<b>Что меняем?</b>', k.leader_configuration_menu(room_id))
        case 4:
            match data[3]:
                case 'count':
                    await change_text(call, sc.settings(room), k.leader_configuration_count(room_id))
                case 'hands':
                    await change_text(call, sc.settings(room), k.leader_configuration_hands(room_id))
                case 'type':
                    await change_text(call, sc.settings(room), k.leader_configuration_type(room_id))
                case 'title':
                    user = mongo_users.find_one({'_id': call.message.chat.id})
                    user['settings']['changing-room-id'] = room_id
                    mongo_users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
                    await change_text(call, 'Введи новое название игры.')
                    await NewGameTitle.input_new_game_title.set()
                case 'delete':
                    await change_text(call, sc.settings(room),
                                      k.leader_configuration_delete(call.message.chat.id, room_id))
                case 'add':
                    await change_text(call, f'<b>{room["code-to-add"]}</b>', k.leader_configuration_add(room_id))
                case 'back':
                    await change_text(call, game_menu(room), k.leader_game_menu(room, call.message.chat.id))
        case 5:
            if data[4] == 'back':
                await change_text(call, sc.settings(room), k.leader_configuration_menu(room_id))
            else:
                match data[3]:
                    case 'count':
                        change_count(room, int(data[4]))
                        await change_text(call, sc.settings(room), k.leader_configuration_count(room_id))
                    case 'hands':
                        try:
                            change_hands(room, int(data[4]))
                            await change_text(call, sc.settings(room), k.leader_configuration_hands(room_id))
                        except MessageNotModified:
                            pass
                    case 'delete':
                        delete_player(room, int(data[4]))
                        await change_text(call, sc.settings(room),
                                          k.leader_configuration_delete(call.message.chat.id, room_id))
                    case 'code':
                        room['code-to-add'] = sc.generate_code_to_add()
                        mongo_games.update_one({'_id': room_id}, {'$set': {'code-to-add': room['code-to-add']}})
                        await change_text(call, f'<b>{room["code-to-add"]}</b>', k.leader_configuration_add(room_id))
                    case 'type':
                        try:
                            change_type(room, int(data[4]))
                            await change_text(call, sc.settings(room), k.leader_configuration_type(room_id))
                        except MessageNotModified:
                            pass
                    case 'back':
                        await change_text(call, game_menu(room), k.leader_game_menu(room, call.message.chat.id))
    await call.answer()


async def end(call: types.CallbackQuery):
    data = call.data.split('_')

    room_id = int(data[2])
    room = mongo_games.find_one({'_id': room_id})

    match data[3]:
        case 'yes':
            for player_id in room['players-ids'][1:]:
                await bot.send_message(
                    player_id,
                    text='Игра преждевременно закончена.',
                    reply_markup=types.ReplyKeyboardRemove()
                )
            sc.cleaning_the_room(room)
            await call.message.delete()
            await call.message.answer('Ну хули, закругляемся)', reply_markup=types.ReplyKeyboardRemove())
        case 'no':
            await call.message.edit_text('Ну хули, играем дальше')


def register_handlers_leader(dp: Dispatcher):
    dp.register_message_handler(start, commands="rooms")
    dp.register_callback_query_handler(game_configuration, Text(startswith='leader_configure_'))
    dp.register_callback_query_handler(end, Text(startswith='leader_end_'))
    dp.register_callback_query_handler(game, Text(startswith='leader_game_'))
    dp.register_callback_query_handler(start_menu, Text(startswith='leader_'))
    dp.register_message_handler(input_game_title, state=GameTitle.input_game_title)
    dp.register_message_handler(input_new_game_title, state=NewGameTitle.input_new_game_title)
