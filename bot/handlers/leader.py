from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters.state import State, StatesGroup

import bot.scripts as sc
import bot.keyboards as k

from bot.config import bot, mongo_users, mongo_games


class GameName(StatesGroup):
    input_game_name = State()


def game_menu(_game: {}) -> str:
    is_playing = 'Now playing' if _game['active'] else 'Not started'
    return f'**{_game["title"]}**>\n{is_playing}\n\n**Настройки: **\n\n' + sc.settings(_game)


async def change_text(call: types.CallbackQuery, new_text: str, reply_markup: types.InlineKeyboardMarkup):
    try:
        await call.message.edit_text(text=new_text, reply_markup=reply_markup)
    except MessageNotModified:
        pass


async def start(message: types.Message):
    playing_games_ids = mongo_users.find_one({'_id': message.from_user.id})['games']
    leader_games = [mongo_games.find_one({'_id': game_id}) for game_id in playing_games_ids]
    if len(leader_games) == 0:
        await message.answer('У тебя пока нет комнат. Хочешь создать?', reply_markup=k.leader_create())
    else:
        await message.answer('Выбери комнату.', reply_markup=k.leader_choose_game(leader_games))


async def start_menu(call: types.CallbackQuery):
    data = call.data.split('_')
    match data[1]:
        case 'yes' | 'create':
            await call.message.edit_text('Хорошо напиши мне какое название ты хочешь дать комнате.')
            await GameName.input_game_name.set()
        case 'no' | 'out':
            await call.message.edit_text('Ладно.')
    await call.answer()


async def input_game_title(message: types.Message, state: FSMContext):
    game_id = sc.set_new_game_id()
    games = mongo_users.find_one({'_id': message.from_user.id})['games']
    games.append(game_id)
    mongo_users.update_one({'_id': message.from_user.id}, {'$set': {'games': games}})
    mongo_games.insert_one({
        '_id': game_id,
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
        },
    })
    await message.answer('Успешно создал комнату. Нажми /rooms чтобы посмотреть список своих комнат.')
    await state.finish()


async def game(call: types.CallbackQuery):
    data = call.data.split('_')

    game_id = int(data[2])
    _game = mongo_games.find_one({'_id': game_id})

    match len(data):
        case 3:
            await change_text(call, game_menu(_game), k.leader_game_menu(_game, call.message.chat.id))
        case 4:
            match data[3]:
                case 'back':
                    playing_games_ids = mongo_users.find_one({'_id': call.message.chat.id})['games']
                    leader_games = [mongo_games.find_one({'_id': game_id}) for game_id in playing_games_ids]
                    await change_text(call, 'Выбери комнату.', k.leader_choose_game(leader_games))
                case 'start':
                    await call.message.delete()

                    sc.card_distributor(_game)
                    sc.shuffle_players(_game)

                    mongo_games.update_one({'_id': game_id}, {'$set': {'active': True}})
                    _game = mongo_games.find_one({'_id': game_id})

                    settings = 'Выбранные настройки игры:\n\n' + sc.settings(_game)

                    for player_id in _game['players-ids']:
                        await bot.send_message(
                            player_id,
                            f'Игра началась, удачи!\n\n{settings}',
                            reply_markup=k.default_menu()
                        )

                    await sc.athanasius_early_check(_game)
                    await sc.turn(_game)
                case 'end':
                    await change_text(call, 'ТОЧНО????', k.leader_end(game_id))
                case 'delete':
                    for player_id in _game['players-ids']:
                        player = mongo_users.find_one({'_id': player_id})
                        player['mongo_games'].pop(player['games'].index(_game['_id']))
                        player['settings']['chosen-room'] = 0
                        mongo_users.update_one(
                            {'_id': player['_id']},
                            {'$set': {'games': player['games'], 'settings': player['settings']}}
                        )
                    mongo_games.delete_one({'_id': _game['_id']})
                    await call.message.edit_text(f'Успешно удалил комнату **{_game["title"]}**.')
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

    game_id = int(data[2])
    _game = mongo_games.find_one({'_id': game_id})

    match len(data):
        case 3:
            await change_text(call, sc.settings(_game) + '\n\n**Что меняем?**', k.leader_configuration_menu(game_id))
        case 4:
            match data[3]:
                case 'count':
                    await change_text(call, sc.settings(_game), k.leader_configuration_count(game_id))
                case 'hands':
                    await change_text(call, sc.settings(_game), k.leader_configuration_hands(game_id))
                case 'delete':
                    await change_text(
                        call,
                        sc.settings(_game),
                        k.leader_configuration_delete(call.message.chat.id, game_id)
                    )
                case 'add':
                    await change_text(call, f'**{_game["code-to-add"]}**', k.leader_configuration_add(game_id))
                case 'type':
                    await change_text(call, sc.settings(_game), k.leader_configuration_type(game_id))
                case 'back':
                    await change_text(call, game_menu(_game), k.leader_game_menu(_game, call.message.chat.id))
        case 5:
            if data[4] == 'back':
                await change_text(call, sc.settings(_game), k.leader_configuration_menu(game_id))
            else:
                match data[3]:
                    case 'count':
                        change_count(_game, int(data[4]))
                        await change_text(call, sc.settings(_game), k.leader_configuration_count(game_id))
                    case 'hands':
                        try:
                            change_hands(_game, int(data[4]))
                            await change_text(call, sc.settings(_game), k.leader_configuration_hands(game_id))
                        except MessageNotModified:
                            pass
                    case 'delete':
                        delete_player(_game, int(data[4]))
                        await change_text(
                            call,
                            sc.settings(_game),
                            k.leader_configuration_delete(call.message.chat.id, game_id)
                        )
                    case 'code':
                        _game['code-to-add'] = sc.generate_code_to_add()
                        mongo_games.update_one({'_id': game_id}, {'$set': {'code-to-add': _game['code-to-add']}})
                        await change_text(call, f'**{_game["code-to-add"]}**', k.leader_configuration_add(game_id))
                    case 'type':
                        try:
                            change_type(_game, int(data[4]))
                            await change_text(call, sc.settings(_game), k.leader_configuration_type(game_id))
                        except MessageNotModified:
                            pass
                    case 'back':
                        await change_text(call, game_menu(_game), k.leader_game_menu(_game, call.message.chat.id))
    await call.answer()


async def end(call: types.CallbackQuery):
    data = call.data.split('_')

    game_id = int(data[2])
    _game = mongo_games.find_one({'_id': game_id})

    match data[3]:
        case 'yes':
            _game['active'] = False
            for player_id in _game['players-ids'][1:]:
                await bot.send_message(
                    player_id,
                    text='Игра преждевременно закончена.',
                    reply_markup=types.ReplyKeyboardRemove()
                )
            mongo_games.update_one({'_id': _game['_id']}, {'$set': {'active': _game['active']}})
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
    dp.register_message_handler(input_game_title, state=GameName.input_game_name)
