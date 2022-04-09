from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified, MessageToEditNotFound, MessageCantBeDeleted

import bot.scripts as sc
import bot.keyboards as k

from bot.config import mongo_users, mongo_games


def delete_chosen(game: {}):
    game['chosen']['card'] = ''
    game['chosen']['count'] = 1
    game['chosen']['count-red'] = 0
    game['chosen']['suits'] = {'Червы': 0, 'Буби': 0, 'Пики': 0, 'Крести': 0}
    game['chosen']['suitable-cards'] = {}
    mongo_games.update_one({'_id': game['_id']}, {'$set': {'chosen': game["chosen"]}})
    


def get_p(player: {}) -> str:
    return f'Игрок: <b>{player["name"]}</b>\n'


def get_pc(player: {}, chosen: {}) -> str:
    return get_p(player) + f'Карта: {sc.change(chosen["card"])}\n'


def get_pcc(player: {}, chosen: {}) -> str:
    return get_pc(player, chosen) + f'Количество: <b>{chosen["count"]}</b>\n'


def get_pccr(player: {}, chosen: {}) -> str:
    return get_pcc(player, chosen) + f'Красных: <b>{chosen["count-red"]}</b>\n'


async def choose_player(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    asked_user = mongo_users.find_one({'_id': int(data[2])})

    game = mongo_games.find_one({'_id': game_id})
    game['chosen']['player-id'] = asked_user['_id']

    mongo_games.update_one({'_id': game_id}, {'$set': {'chosen': game['chosen']}})

    await call.message.edit_text(
        text=get_p(mongo_users.find_one({'_id': asked_user['_id']})) + '\nКакую карту хочешь спросить?',
        reply_markup=k.card_menu(game, call.message.chat.id, f'turnCard_{game_id}', with_back=True)
    )
    await call.answer()


async def card(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    game = mongo_games.find_one({'_id': game_id})
    user = mongo_users.find_one({'_id': call.message.chat.id})
    asked_user = mongo_users.find_one({'_id': game['chosen']['player-id']})
    match data[2]:
        case 'yes':
            pass
        case 'no':
            await call.message.edit_text(
                text=get_p(asked_user) + '\nКакую карту хочешь спросить?',
                reply_markup=k.card_menu(game, call.message.chat.id, f'turnCard_{game_id}', with_back=True)
            )
            await call.answer()
            return
        case 'back':
            await call.message.edit_text(
                text='Хорошо, кого спросим?',
                reply_markup=k.choose_player(call.message.chat.id, game),
            )
            await call.answer()
            return
        case _:
            game['chosen']['card'] = data[2]
            mongo_games.update_one({'_id': game_id}, {'$set': {'chosen': game['chosen']}})
            if user['settings']['applies']['card']:
                await call.message.edit_text(
                    text=get_p(asked_user) + f'\nСпрашиваем {sc.change(data[2])}?',
                    reply_markup=k.apply_card(game_id)
                )
                await call.answer()
                return
    if sc.find_cards(game, card=True):
        await call.message.edit_text(
            text=get_pc(
                asked_user,
                game['chosen']
            ) + f'\nКак думаешь, сколько их?\n\nКоличество: <b>{game["chosen"]["count"]}</b>',
            reply_markup=k.make_counter(callback=f'cardsCount_{game_id}')
        )
    else:
        try:
            await call.message.delete()
        except MessageCantBeDeleted:
            await call.message.edit_text(
                'Не смог удалить это сообщение, поэтому ты видишь этот текст.\n'
                'Не пугайся, ничего не сломалось, просто ты ходил больше дня)')
        await sc.message_to_all(game, user, asked_user, 'Их <b>нет</b>)')
        sc.change_player(game)
        await sc.turn(game)
        delete_chosen(game)


async def cards_count(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    game = mongo_games.find_one({'_id': game_id})
    user = mongo_users.find_one({'_id': call.message.chat.id})
    asked_user = mongo_users.find_one({'_id': game['chosen']['player-id']})
    match data[2]:
        case 'yes':
            pass
        case 'no':
            await call.message.edit_text(
                text=get_pc(asked_user, game['chosen']) + f'\nКак думаешь, сколько их?\n\n'
                                                          f'Количество: <b>{game["chosen"]["count"]}</b>',
                reply_markup=k.make_counter(callback=f'cardsCount_{game_id}')
            )
            await call.answer()
            return
        case 'apply':
            if user['settings']['applies']['count']:
                await call.message.edit_text(
                    text=get_pc(asked_user, game['chosen']) + f'\nСпрашиваем {game["chosen"]["count"]}?',
                    reply_markup=k.apply_count(game_id)
                )
                await call.answer()
                return
        case _:
            if game["chosen"]["count"] + int(data[2]) >= 1:
                game["chosen"]["count"] += int(data[2])
                await call.message.edit_text(
                    f'{get_pc(asked_user, game["chosen"])}\nКак думаешь, сколько их?\n\n'
                    f'Количество: <b>{game["chosen"]["count"]}</b>',
                    reply_markup=k.make_counter(callback=f'cardsCount_{game_id}')
                )
                mongo_games.update_one({'_id': game['_id']}, {'$set': {'chosen': game["chosen"]}})
            await call.answer()
            return
    if sc.find_cards(game, count=True):
        await call.message.edit_text(
            text=get_pcc(asked_user, game['chosen']) + f'\nКак думаешь, сколько из них красных?\n\n'
                                                       f'Количество красных: <b>{game["chosen"]["count-red"]}</b>',
            reply_markup=k.make_counter(callback=f'cardsRed_{game_id}')
        )
    else:
        try:
            await call.message.delete()
        except MessageCantBeDeleted:
            await call.message.edit_text(
                'Не смог удалить это сообщение, поэтому ты видишь этот текст.\n'
                'Не пугайся, ничего не сломалось, просто ты ходил больше дня)')
        await sc.message_to_all(
            game,
            user,
            asked_user,
            f'Их не <b>{game["chosen"]["count"]}</b>.'
        )
        sc.change_player(game)
        await sc.turn(game)
        delete_chosen(game)


async def cards_red(call: types.CallbackQuery):
    data = call.data.split('_')
    room_id = int(data[1])
    room = mongo_games.find_one({'_id': room_id})
    user = mongo_users.find_one({'_id': call.message.chat.id})
    asked_user = mongo_users.find_one({'_id': room['chosen']['player-id']})
    match data[2]:
        case 'yes':
            pass
        case 'no':
            await call.message.edit_text(
                text=get_pcc(asked_user, room['chosen']) + f'\nКак думаешь, сколько из них красных?\n\n'
                                                           f'Количество красных: <b>{room["chosen"]["count-red"]}</b>',
                reply_markup=k.make_counter(callback=f'cardsRed_{room_id}')
            )
            await call.answer()
            return
        case 'apply':
            if user['settings']['applies']['count-red']:
                await call.message.edit_text(
                    text=get_pcc(asked_user, room['chosen']) + f'\nСпрашиваем {room["chosen"]["count-red"]}?',
                    reply_markup=k.apply_red(room_id)
                )
                await call.answer()
                return
        case _:
            if room['chosen']['count-red'] + int(data[2]) >= 0:
                room['chosen']['count-red'] += int(data[2])
                await call.message.edit_text(
                    f'{get_pcc(asked_user, room["chosen"])}\nКак думаешь, сколько из них красных?\n\n'
                    f'Количество красных: <b>{room["chosen"]["count-red"]}</b>',
                    reply_markup=k.make_counter(callback=f'cardsRed_{room_id}')
                )
                mongo_games.update_one({'_id': room['_id']}, {'$set': {'chosen': room['chosen']}})
            await call.answer()
            return
    if sc.find_cards(room, count_red=True):
        if room['chosen']['card'] == 'W':
            await call.message.delete()
            for key in room["chosen"]["suitable-cards"].keys():
                sc.delete_cards(room, str(asked_user['_id']), room['chosen']['card'], key)
                break
            mongo_games.update_one({'_id': room['_id']}, {'$set': {'cards': room['cards']}})
            room = mongo_games.find_one({'_id': room_id})
            if sc.athanasius_check(room, str(user['_id'])):
                await call.message.answer(
                    f'Поздравляю!\nНи у кого больше нет {sc.change(room["chosen"]["card"])}. Добавил тебе Афанасия.'
                )
                sc.add_athanasius(room, str(user['_id']))
            await sc.message_to_all(
                room,
                user,
                asked_user,
                f'<b>Выкинул</b>. Они {sc.jokers(room["chosen"]["count"], room["chosen"]["count-red"])}'
            )
            if sc.end_check(room):
                sc.cleaning_the_room(room)
                await sc.end_message(room)
                await call.answer()
                return
            if sc.delete_player_if_hands_empty(room, user['_id']):
                sc.change_player(room)
            sc.delete_player_if_hands_empty(room, asked_user['_id'])
            delete_chosen(room)
            await sc.turn(room)
        else:
            await call.message.edit_text(
                text=get_pccr(asked_user, room['chosen']) + f'\nХорошо, осталось угадать масти:\n\n'
                                                            f'♥: <b>0</b>    ♦: <b>0</b>    ♠: <b>0</b>    ♣: <b>0</b>',
                reply_markup=k.choose_suits(room_id)
            )
    else:
        try:
            await call.message.delete()
        except MessageCantBeDeleted:
            await call.message.edit_text(
                'Не смог удалить это сообщение, поэтому ты видишь этот текст.\n'
                'Не пугайся, ничего не сломалось, просто ты ходил больше дня)')
        await sc.message_to_all(
            room,
            user,
            asked_user,
            f'Их <b>{room["chosen"]["count"]}</b>, красных не <b>{room["chosen"]["count-red"]}</b>.'
        )
        sc.change_player(room)
        delete_chosen(room)
        await sc.turn(room)
    await call.answer()


async def change_suits(game: {}, what_suit: str, what_to_do: str):
    match what_suit:
        case 'h':
            suit = 'Червы'
        case 'd':
            suit = 'Буби'
        case 's':
            suit = 'Пики'
        case _:
            suit = 'Крести'
    delta = 1 if what_to_do == '+' else -1
    if game['chosen']['suits'][suit] + delta >= 0:
        game['chosen']['suits'][suit] += delta
        mongo_games.update_one({'_id': game['_id']}, {'$set': {'chosen': game['chosen']}})


async def suits(call: types.CallbackQuery):
    data = call.data.split('_')
    room_id = int(data[1])
    room = mongo_games.find_one({'_id': room_id})
    user = mongo_users.find_one({'_id': call.message.chat.id})
    asked_user = mongo_users.find_one({'_id': room['chosen']['player-id']})
    match data[2]:
        case 'yes':
            pass
        case 'no':
            await call.message.edit_text(
                text=get_pccr(asked_user, room['chosen']) + f'\nХорошо, осталось угадать масти:\n\n'
                                                            f'♥: <b>{room["chosen"]["suits"]["Червы"]}</b>    '
                                                            f'♦: <b>{room["chosen"]["suits"]["Буби"]}</b>    '
                                                            f'♠: <b>{room["chosen"]["suits"]["Пики"]}</b>    '
                                                            f'♣: <b>{room["chosen"]["suits"]["Крести"]}</b>',
                reply_markup=k.choose_suits(room_id)
            )
            await call.answer()
            return
        case 'apply':
            if user['settings']['applies']['suits']:
                await call.message.edit_text(
                    text=get_pccr(asked_user, room['chosen']) + f'Спрашиваем '
                                                                f'♥: <b>{room["chosen"]["suits"]["Червы"]}</b>    '
                                                                f'♦: <b>{room["chosen"]["suits"]["Буби"]}</b>    '
                                                                f'♠: <b>{room["chosen"]["suits"]["Пики"]}</b>    '
                                                                f'♣: <b>{room["chosen"]["suits"]["Крести"]}</b>?',
                    reply_markup=k.apply_suits(room_id)
                )
                await call.answer()
                return
        case _:
            await change_suits(room, data[2][0], data[2][1])
            try:
                await call.message.edit_text(
                    text=get_pccr(asked_user, room['chosen']) + f'\nХорошо, осталось угадать масти:\n\n'
                                                                f'♥: <b>{room["chosen"]["suits"]["Червы"]}</b>    '
                                                                f'♦: <b>{room["chosen"]["suits"]["Буби"]}</b>    '
                                                                f'♠: <b>{room["chosen"]["suits"]["Пики"]}</b>    '
                                                                f'♣: <b>{room["chosen"]["suits"]["Крести"]}</b>',
                    reply_markup=k.choose_suits(room_id)
                )
            except MessageNotModified:
                pass
            except MessageToEditNotFound:
                pass
            await call.answer()
            return
    if sc.find_cards(room, suits=True):
        await call.message.delete()
        for key in room["chosen"]["suitable-cards"].keys():
            sc.delete_cards(room, str(asked_user['_id']), room['chosen']['card'], key)
            break
        await sc.message_to_all(
            room,
            user,
            asked_user,
            f'<b>Выкинул</b>. Они {sc.suits_to_emoji(room["chosen"]["suits"])}'
        )
        mongo_games.update_one({'_id': room['_id']}, {'$set': {'cards': room['cards']}})
        room = mongo_games.find_one({'_id': room_id})
        if sc.athanasius_check(room, str(user['_id'])):
            await call.message.answer(
                f'Поздравляю!\nНи у кого больше нет {sc.change(room["chosen"]["card"])}. Добавил тебе Афанасия.'
            )
            sc.add_athanasius(room, str(user['_id']))
        if sc.end_check(room):
            sc.cleaning_the_room(room)
            await sc.end_message(room)
            await call.answer()
            return
        if sc.delete_player_if_hands_empty(room, user['_id']):
            sc.change_player(room)
        sc.delete_player_if_hands_empty(room, asked_user['_id'])
    else:
        await sc.message_to_all(
            room,
            user,
            asked_user,
            f'Их <b>{room["chosen"]["count"]}</b>, красных <b>{room["chosen"]["count-red"]}</b>. '
            f'Они не {sc.suits_to_emoji(room["chosen"]["suits"])}'
        )
        try:
            await call.message.delete()
        except MessageCantBeDeleted:
            await call.message.edit_text(
                'Не смог удалить это сообщение, поэтому ты видишь этот текст.\n'
                'Не пугайся, ничего не сломалось, просто ты ходил больше дня)')
        sc.change_player(room)
    delete_chosen(room)
    await sc.turn(room)
    await call.answer()


def register_handlers_turn(dp: Dispatcher):
    dp.register_callback_query_handler(choose_player, Text(startswith="ask_"))
    dp.register_callback_query_handler(card, Text(startswith="turnCard"))
    dp.register_callback_query_handler(cards_count, Text(startswith="cardsCount"))
    dp.register_callback_query_handler(cards_red, Text(startswith="cardsRed"))
    dp.register_callback_query_handler(suits, Text(startswith="suits"))
