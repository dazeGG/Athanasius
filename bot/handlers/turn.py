from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.utils.exceptions import MessageNotModified, MessageToEditNotFound, MessageCantBeDeleted

import bot.scripts as sc
import bot.keyboards as k

from bot.config import collection


def delete_chosen(game: {}):
    game['chosen']['card'] = ''
    game['chosen']['count'] = 1
    game['chosen']['count-red'] = 0
    game['chosen']['suits'] = {'Червы': 0, 'Буби': 0, 'Пики': 0, 'Крести': 0}
    game['chosen']['suitable-cards'] = {}
    collection.games.update_one({'_id': game['_id']}, {'$set': {'chosen': game["chosen"]}})


def get_p(player: {}) -> str:
    return f'Игрок: **{player["name"]}**\n'


def get_pc(player: {}, chosen: {}) -> str:
    return get_p(player) + f'Карта: {sc.change(chosen["card"])}\n'


def get_pcc(player: {}, chosen: {}) -> str:
    return get_pc(player, chosen) + f'Количество: **{chosen["count"]}**\n'


def get_pccr(player: {}, chosen: {}) -> str:
    return get_pcc(player, chosen) + f'Красных: **{chosen["count-red"]}**\n'


async def choose_player(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    asked_user = collection.users.find_one({'_id': int(data[2])})

    game = collection.games.find_one({'_id': game_id})
    game['chosen']['player-id'] = asked_user['_id']

    collection.games.update_one({'_id': game_id}, {'$set': {'chosen': game['chosen']}})

    await call.message.edit_text(
        text=get_p(collection.users.find_one({'_id': asked_user['_id']})) + '\nКакую карту хочешь спросить?',
        reply_markup=k.card_menu(game, call.message.chat.id, f'turnCard_{game_id}', with_back=True)
    )

    await call.answer()


async def card(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    game = collection.games.find_one({'_id': game_id})
    user = collection.users.find_one({'_id': call.message.chat.id})
    asked_user = collection.users.find_one({'_id': game['chosen']['player-id']})
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
            collection.games.update_one({'_id': game_id}, {'$set': {'chosen': game['chosen']}})
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
            ) + f'\nКак думаешь, сколько их?\n\nКоличество: **{game["chosen"]["count"]}**',
            reply_markup=k.make_counter(callback=f'cardsCount_{game_id}')
        )
    else:
        try:
            await call.message.delete()
        except MessageCantBeDeleted:
            await call.message.edit_text(
                'Не смог удалить это сообщение, поэтому ты видишь этот текст.\n'
                'Не пугайся, ничего не сломалось, просто ты ходил больше дня)')
        await sc.message_to_all(game, user, asked_user, 'Их **нет**)')
        sc.change_player(game)
        await sc.turn(game)
        delete_chosen(game)


async def cards_count(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    game = collection.games.find_one({'_id': game_id})
    user = collection.users.find_one({'_id': call.message.chat.id})
    asked_user = collection.users.find_one({'_id': game['chosen']['player-id']})
    match data[2]:
        case 'yes':
            pass
        case 'no':
            await call.message.edit_text(
                text=get_pc(asked_user, game['chosen']) + f'\nКак думаешь, сколько их?\n\n'
                                                          f'Количество: **{game["chosen"]["count"]}**',
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
                    f'Количество: **{game["chosen"]["count"]}**',
                    reply_markup=k.make_counter(callback=f'cardsCount_{game_id}')
                )
                collection.games.update_one({'_id': game['_id']}, {'$set': {'chosen': game["chosen"]}})
            await call.answer()
            return
    if sc.find_cards(game, count=True):
        await call.message.edit_text(
            text=get_pcc(asked_user, game['chosen']) + f'\nКак думаешь, сколько из них красных?\n\n'
                                                       f'Количество красных: **{game["chosen"]["count-red"]}**',
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
            f'Их не **{game["chosen"]["count"]}**.'
        )
        sc.change_player(game)
        await sc.turn(game)
        delete_chosen(game)


async def cards_red(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    game = collection.games.find_one({'_id': game_id})
    user = collection.users.find_one({'_id': call.message.chat.id})
    asked_user = collection.users.find_one({'_id': game['chosen']['player-id']})
    match data[2]:
        case 'yes':
            pass
        case 'no':
            await call.message.edit_text(
                text=get_pcc(asked_user, game['chosen']) + f'\nКак думаешь, сколько из них красных?\n\n'
                                                           f'Количество красных: **{game["chosen"]["count-red"]}**',
                reply_markup=k.make_counter(callback=f'cardsRed_{game_id}')
            )
            await call.answer()
            return
        case 'apply':
            if user['settings']['applies']['count-red']:
                await call.message.edit_text(
                    text=get_pcc(asked_user, game['chosen']) + f'\nСпрашиваем {game["chosen"]["count-red"]}?',
                    reply_markup=k.apply_red(game_id)
                )
                await call.answer()
                return
        case _:
            if game['chosen']['count-red'] + int(data[2]) >= 0:
                game['chosen']['count-red'] += int(data[2])
                await call.message.edit_text(
                    f'{get_pcc(asked_user, game["chosen"])}\nКак думаешь, сколько из них красных?\n\n'
                    f'Количество красных: **{game["chosen"]["count-red"]}**',
                    reply_markup=k.make_counter(callback=f'cardsRed_{game_id}')
                )
                collection.games.update_one({'_id': game['_id']}, {'$set': {'chosen': game['chosen']}})
            await call.answer()
            return
    if sc.find_cards(game, count_red=True):
        if game['chosen']['card'] == 'W':
            await call.message.delete()
            for key in game["chosen"]["suitable-cards"].keys():
                sc.delete_cards(game, str(asked_user['_id']), game['chosen']['card'], key)
                break
            collection.games.update_one({'_id': game['_id']}, {'$set': {'cards': game['cards']}})
            game = collection.games.find_one({'_id': game_id})
            if sc.athanasius_check(game, str(user['_id'])):
                await call.message.answer(
                    f'Поздравляю!\nНи у кого больше нет {sc.change(game["chosen"]["card"])}. Добавил тебе Афанасия.'
                )
                sc.add_athanasius(game, str(user['_id']))
            await sc.message_to_all(
                game,
                user,
                asked_user,
                f'**Выкинул**. Они {sc.jokers(game["chosen"]["count"], game["chosen"]["count-red"])}'
            )
            if sc.end_check(game):
                await sc.end_message(game)
                await call.answer()
                return
            if sc.delete_player_if_hands_empty(game, user['_id']):
                sc.change_player(game)
            sc.delete_player_if_hands_empty(game, asked_user['_id'])
            delete_chosen(game)
            await sc.turn(game)
        else:
            await call.message.edit_text(
                text=get_pccr(asked_user, game['chosen']) + f'\nХорошо, осталось угадать масти:\n\n'
                                                            f'♥: **0**    ♦: **0**    ♠: **0**    ♣: **0**',
                reply_markup=k.choose_suits(game_id)
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
            f'Их **{game["chosen"]["count"]}**, красных не **{game["chosen"]["count-red"]}**.'
        )
        sc.change_player(game)
        delete_chosen(game)
        await sc.turn(game)
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
        collection.games.update_one({'_id': game['_id']}, {'$set': {'chosen': game['chosen']}})


async def suits(call: types.CallbackQuery):
    data = call.data.split('_')
    game_id = int(data[1])
    game = collection.games.find_one({'_id': game_id})
    user = collection.users.find_one({'_id': call.message.chat.id})
    asked_user = collection.users.find_one({'_id': game['chosen']['player-id']})
    match data[2]:
        case 'yes':
            pass
        case 'no':
            await call.message.edit_text(
                text=get_pccr(asked_user, game['chosen']) + f'\nХорошо, осталось угадать масти:\n\n'
                                                            f'♥: **{game["chosen"]["suits"]["Червы"]}**    '
                                                            f'♦: **{game["chosen"]["suits"]["Буби"]}**    '
                                                            f'♠: **{game["chosen"]["suits"]["Пики"]}**    '
                                                            f'♣: **{game["chosen"]["suits"]["Крести"]}**',
                reply_markup=k.choose_suits(game_id)
            )
            await call.answer()
            return
        case 'apply':
            if user['settings']['applies']['suits']:
                await call.message.edit_text(
                    text=get_pccr(asked_user, game['chosen']) + f'Спрашиваем '
                                                                f'♥: **{game["chosen"]["suits"]["Червы"]}**    '
                                                                f'♦: **{game["chosen"]["suits"]["Буби"]}**    '
                                                                f'♠: **{game["chosen"]["suits"]["Пики"]}**    '
                                                                f'♣: **{game["chosen"]["suits"]["Крести"]}**?',
                    reply_markup=k.apply_suits(game_id)
                )
                await call.answer()
                return
        case _:
            await change_suits(game, data[2][0], data[2][1])
            try:
                await call.message.edit_text(
                    text=get_pccr(asked_user, game['chosen']) + f'\nХорошо, осталось угадать масти:\n\n'
                                                                f'♥: **{game["chosen"]["suits"]["Червы"]}**    '
                                                                f'♦: **{game["chosen"]["suits"]["Буби"]}**    '
                                                                f'♠: **{game["chosen"]["suits"]["Пики"]}**    '
                                                                f'♣: **{game["chosen"]["suits"]["Крести"]}**',
                    reply_markup=k.choose_suits(game_id)
                )
            except MessageNotModified:
                pass
            except MessageToEditNotFound:
                pass
            await call.answer()
            return
    if sc.find_cards(game, suits=True):
        await call.message.delete()
        for key in game["chosen"]["suitable-cards"].keys():
            sc.delete_cards(game, str(asked_user['_id']), game['chosen']['card'], key)
            break
        await sc.message_to_all(
            game,
            user,
            asked_user,
            f'**Выкинул**. Они {sc.suits_to_emoji(game["chosen"]["suits"])}'
        )
        collection.games.update_one({'_id': game['_id']}, {'$set': {'cards': game['cards']}})
        game = collection.games.find_one({'_id': game_id})
        if sc.athanasius_check(game, str(user['_id'])):
            await call.message.answer(
                f'Поздравляю!\nНи у кого больше нет {sc.change(game["chosen"]["card"])}. Добавил тебе Афанасия.'
            )
            sc.add_athanasius(game, str(user['_id']))
        if sc.end_check(game):
            await sc.end_message(game)
            await call.answer()
            return
        if sc.delete_player_if_hands_empty(game, user['_id']):
            sc.change_player(game)
        sc.delete_player_if_hands_empty(game, asked_user['_id'])
    else:
        await sc.message_to_all(
            game,
            user,
            asked_user,
            f'Их **{game["chosen"]["count"]}**, красных **{game["chosen"]["count-red"]}**. '
            f'Они не {sc.suits_to_emoji(game["chosen"]["suits"])}'
        )
        try:
            await call.message.delete()
        except MessageCantBeDeleted:
            await call.message.edit_text(
                'Не смог удалить это сообщение, поэтому ты видишь этот текст.\n'
                'Не пугайся, ничего не сломалось, просто ты ходил больше дня)')
        sc.change_player(game)
    delete_chosen(game)
    await sc.turn(game)
    await call.answer()


def register_main_loop_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(choose_player, Text(startswith="ask_"))
    dp.register_callback_query_handler(card, Text(startswith="turnCard"))
    dp.register_callback_query_handler(cards_count, Text(startswith="cardsCount"))
    dp.register_callback_query_handler(cards_red, Text(startswith="cardsRed"))
    dp.register_callback_query_handler(suits, Text(startswith="suits"))
