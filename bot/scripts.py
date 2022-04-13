import codecs

from aiogram import types
from random import shuffle, randint

from bot.keyboards import choose_player
from bot.config import bot, mongo_users, mongo_games


get_player_by_id = lambda player_id: mongo_users.find({'_id': player_id})


'''    ROOM SETTINGS SCRIPTS   '''


def set_new_game_id() -> int:
    last_game = mongo_games.find_one({'$query': {}, '$orderby': {'_id': -1}})
    if last_game is None:
        return 1
    return last_game['_id'] + 1


def generate_part_of_code_to_add() -> str:
    alphabet = 'ABCEHKMOPTXY0123456789'
    alphabet_len = len(alphabet)
    return ''.join([alphabet[randint(0, alphabet_len - 1)] for _ in range(5)])


def generate_code_to_add() -> str:
    while True:
        code = '-'.join([generate_part_of_code_to_add() for _ in range(4)])
        if mongo_games.find_one({'code-to-add': code}) is None:
            break
    return code


'''    LEADER SCRIPTS   '''


def make_notes(room: {}):
    cards = ''
    match room['config']['type-of-deck']:
        case 36:
            cards += '6789XJQKA'
        case 52:
            cards += '23456789XJQKA'
        case 54:
            cards += '23456789XJQKAW'
    d = {}
    for player_id in room['players-ids']:
        d[str(player_id)] = {}
        for card in cards:
            d[str(player_id)][card] = [['♥', '♦', '♠', '♣']]
            for j in range(room['config']['count-of-decks']):
                d[str(player_id)][card].append([])
                for k in range(4):
                    d[str(player_id)][card][j + 1].append('-')
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'notes': d}})


async def athanasius_early_check(room: {}):
    cards = ['6', '7', '8', '9', 'X', 'J', 'Q', 'K', 'A']

    if room['config']['type-of-deck'] == 52 or room['config']['type-of-deck'] == 54:
        for _card in '2345':
            cards.append(_card)
        if room['config']['type-of-deck'] == 54:
            cards.append('W')

    all_found_athanasias = []

    for player_id in room['cards'].keys():
        athanasias = []
        for card in cards:
            if unique_owner(room, card, player_id) and card not in all_found_athanasias:
                for hand in room['cards'][player_id].keys():
                    delete_cards(room, player_id, card, hand)
                athanasias.append(card)
                all_found_athanasias.append(card)
        if len(athanasias) != 0:
            if len(athanasias) == 1:
                await bot.send_message(
                    player_id,
                    'Поздравляю! У тебя с самого начала есть Афанасий. '
                    'Посмотреть его можно, нажав на кнопку Афанасии'
                )
            else:
                await bot.send_message(
                    player_id,
                    'Поздравляю! У тебя с самого начала есть несколько Афанасиев. '
                    'Посмотреть их можно, нажав на кнопку Афанасии'
                )
            room['athanasias'][player_id] = athanasias
        mongo_games.update_one(
            {'_id': room['_id']},
            {'$set': {'athanasias': room['athanasias'], 'cards': room['cards']}}
        )


def card_distributor(room: {}):
    players_ids = [player_id for player_id in map(str, room['players-ids'])]

    count_of_decks = room['config']['count-of-decks']
    count_of_hands = room['config']['count-of-hands']

    deck = []

    for value in '6789XJQKA':
        for suit in 'ЧБПК':
            deck.append(value + suit)

    if room['config']['type-of-deck'] == 52 or room['config']['type-of-deck'] == 54:
        for value in '2345':
            for suit in 'ЧБПК':
                deck.append(value + suit)
        if room['config']['type-of-deck'] == 54:
            for suit in 'ЧК':
                deck.append('W' + suit)

    general_deck = []

    for number_of_deck in range(int(count_of_decks)):
        for card in deck:
            general_deck.append(card)

    shuffle(general_deck)

    players_decks = {}
    athanasias = {}

    for player_id in players_ids:
        players_decks[player_id] = {}
        athanasias[player_id] = []
        for number_of_hand in range(count_of_hands):
            players_decks[player_id][f'hand-{number_of_hand + 1}'] = []

    while len(general_deck) != 0:
        for number_of_hand in range(count_of_hands):
            for player_id in players_ids:
                players_decks[player_id][f'hand-{number_of_hand + 1}'].append(general_deck.pop(0))
                if len(general_deck) == 0:
                    break
            if len(general_deck) == 0:
                break

    for player_id in players_ids:
        for number_of_hand in range(count_of_hands):
            players_decks[player_id][f'hand-{number_of_hand + 1}'].sort()

    mongo_games.update_one({'_id': room['_id']}, {'$set': {'cards': players_decks, 'athanasias': athanasias}})


def shuffle_players(room: {}):
    queue = room['players-ids']
    shuffle(queue)
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'queue': queue}})


'''    IN GAME SCRIPTS    '''


async def turn(room: {}):
    try:
        user = mongo_users.find_one({'_id': room['queue'][0]})
        if user['settings']['focus-mode']:
            await bot.send_message(room['queue'][0], get_focus_mode_message(user, room))
    except KeyError:
        pass
    message = 'Твой ход!\nУ кого спросим карты?'
    await bot.send_message(room['queue'][0], message, reply_markup=choose_player(room['queue'][0], room))


def get_focus_mode_message(user: {}, room: {}) -> str:
    message = f'Игра: <b>{room["title"]}</b>\n\n' + user['settings']['focus-mode-messages'][room['title']]
    user['settings']['focus-mode-messages'].pop(room['title'])
    mongo_users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
    return message


def player_available_cards(room: {}, player_id: int) -> tuple:
    available_cards = {'nums': [], 'letters': []}
    for value in ['2', '3', '4', '5', '6', '7', '8', '9', 'X', 'J', 'Q', 'K', 'A', 'W']:
        for hand in room['cards'][str(player_id)].keys():
            for card in room['cards'][str(player_id)][hand]:
                if value in card and value not in available_cards['nums'] and (value.isdigit() or value == 'X'):
                    available_cards['nums'].append(value)
                if value in card and value not in available_cards['letters'] and not (value.isdigit() or value == 'X'):
                    available_cards['letters'].append(value)
    return available_cards['nums'], available_cards['letters']


def change_player(room: {}):
    room['queue'].append(room['queue'].pop(0))
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'queue': room['queue']}})


def find_cards(room: {}, card: bool = False, count: bool = False, count_red: bool = False, suits: bool = False) -> bool:
    is_true = False
    keys_to_delete = []
    if card:
        for hand in room['cards'][str(room['chosen']['player-id'])].keys():
            room['chosen']['suitable-cards'][hand] = []
            for card in room['cards'][str(room['chosen']['player-id'])][hand]:
                if room['chosen']['card'] in card:
                    is_true = True
                    room['chosen']['suitable-cards'][hand].append(card)
            if len(room['chosen']['suitable-cards'][hand]) == 0:
                room['chosen']['suitable-cards'].pop(hand)
    elif count:
        for hand in room['chosen']['suitable-cards'].keys():
            if len(room['chosen']['suitable-cards'][hand]) == room['chosen']['count']:
                is_true = True
            else:
                keys_to_delete.append(hand)
    elif count_red:
        for hand in room['chosen']['suitable-cards'].keys():
            count_of_red = 0
            if room['chosen']['card'] == 'W':
                for card in room['chosen']['suitable-cards'][hand]:
                    if 'К' in card:
                        count_of_red += 1
            else:
                for card in room['chosen']['suitable-cards'][hand]:
                    if 'Ч' in card or 'Б' in card:
                        count_of_red += 1
            if count_of_red == room['chosen']['count-red']:
                is_true = True
            else:
                keys_to_delete.append(hand)
    elif suits:
        for hand in room['chosen']['suitable-cards'].keys():
            counter = {'Червы': 0, 'Буби': 0, 'Пики': 0, 'Крести': 0}
            for card in room['chosen']['suitable-cards'][hand]:
                if 'Ч' in card:
                    counter['Червы'] += 1
                elif 'Б' in card:
                    counter['Буби'] += 1
                elif 'П' in card:
                    counter['Пики'] += 1
                elif 'К' in card:
                    counter['Крести'] += 1
            if counter == room['chosen']['suits']:
                is_true = True
            else:
                keys_to_delete.append(hand)
    for key_to_delete in keys_to_delete:
        room['chosen']['suitable-cards'].pop(key_to_delete)
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'chosen': room['chosen']}})
    return is_true


async def message_to_all(room: {}, player: {}, asked_player: {}, request: str = ''):
    message = f'<b>{player["name"]} -> {asked_player["name"]}</b> - {change(room["chosen"]["card"])} - {request}'

    for _player in mongo_users.find({'_id': {'$in': room['players-ids']}}):
        if _player['_id'] == player['_id']:
            m = f'Игра: <b>{room["title"]}</b> - ' + message.replace(player["name"], 'Ты')
            await bot.send_message(_player['_id'], m)
        else:
            if _player['_id'] == asked_player["_id"]:
                m = message.replace(asked_player["name"], 'Ты')
            else:
                m = message
            if _player['settings']['focus-mode']:
                _player['settings']['focus-mode-messages'][room["title"]] = \
                    _player['settings']['focus-mode-messages'].get(room["title"], '') + m + '\n'
                mongo_users.update_one({'_id': _player['_id']}, {'$set': {'settings': _player['settings']}})
            else:
                m = f'Игра: <b>{room["title"]}</b> - ' + m
                await bot.send_message(_player['_id'], m)

    '''
    with open('log.txt', 'a', encoding="utf-8") as file:
        file.write(message.replace('<b>', '').replace('</b>', '') + '\n')
    '''


def unique_owner(room: {}, card: str, player_id: str) -> bool:
    for _player_id in room['cards'].keys():
        if _player_id != player_id:
            for hand in room['cards'][_player_id].keys():
                for _card in room['cards'][_player_id][hand]:
                    if card in _card:
                        return False
    return True


def delete_player_if_hands_empty(room: {}, player_id: int) -> bool:
    for hand in room['cards'][str(player_id)].keys():
        if len(room['cards'][str(player_id)][hand]) != 0:
            return False
    room['queue'].pop(room['queue'].index(player_id))
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'queue': room['queue']}})
    return True


def athanasius_check(room: {}, player_id: str) -> bool:
    if unique_owner(room, room['chosen']['card'], player_id):
        for hand in room['cards'][player_id].keys():
            delete_cards(room, player_id, room['chosen']['card'], hand)
        return True
    return False


def add_athanasius(room: {}, player_id: str):
    room['athanasias'][player_id].append(room['chosen']['card'])
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'athanasias': room['athanasias']}})


def delete_cards(room: {}, player_id: str, card: str, hand_key: str):
    room['cards'][player_id][hand_key] = [_card for _card in room['cards'][player_id][hand_key] if card not in _card]
    mongo_games.update_one({'_id': room['_id']}, {'$set': {'cards': room['cards']}})


'''    CARD INFO    '''


def get_card_info(room: {}, player_id: int, card: str) -> str:
    user = mongo_users.find_one({'_id': player_id})
    cards = {}
    for hand in room['cards'][str(player_id)].keys():
        cards[hand] = [_card for _card in room['cards'][str(player_id)][hand] if card in _card]

    if card != 'W':
        categories = ['Количество', 'Красные', 'Червы', 'Буби', 'Чёрные', 'Пики', 'Крести']
    else:
        categories = ['Количество', 'Красные', 'Чёрные']

    counter = {}
    for hand in cards.keys():
        counter[hand] = {}
        for category in categories:
            counter[hand][category] = 0

    if card == 'W':
        for hand in cards.keys():
            for _card in cards[hand]:
                counter[hand]['Количество'] += 1
                if _card[1] == 'К':
                    counter[hand]['Красные'] += 1
                else:
                    counter[hand]['Чёрные'] += 1
    else:
        for hand in cards.keys():
            for _card in cards[hand]:
                counter[hand]['Количество'] += 1
                match _card[1]:
                    case 'Ч':
                        counter[hand]['Красные'] += 1
                        counter[hand]['Червы'] += 1
                    case 'Б':
                        counter[hand]['Красные'] += 1
                        counter[hand]['Буби'] += 1
                    case 'П':
                        counter[hand]['Чёрные'] += 1
                        counter[hand]['Пики'] += 1
                    case 'К':
                        counter[hand]['Чёрные'] += 1
                        counter[hand]['Крести'] += 1

    card_info = ''

    match user['settings']['card-view']:
        case 'text':
            pass
        case 'emoji':
            hands_with_card = []
            for hand in cards.keys():
                if counter[hand]['Количество'] > 0:
                    hands_with_card.append(hand)
            card_info += f'Карта: {change(card)}\n\n'
            for hand in hands_with_card:
                if len(hands_with_card) > 1:
                    card_info += f'<b>Рука {hand.split("-")[1]}</b>\n'
                if card == 'W':
                    card_info += f'{change("Красные")}: <b>{counter[hand]["Красные"]}</b>'
                    card_info += f'{change("Чёрные")}: <b>{counter[hand]["Чёрные"]}</b>\n\n'
                else:
                    card_info += f'{change("Красные")}: <b>{counter[hand]["Красные"]}</b>    '
                    card_info += f'{change("Червы")}: <b>{counter[hand]["Червы"]}</b> '
                    card_info += f'{change("Буби")}: <b>{counter[hand]["Буби"]}</b>\n'
                    card_info += f'{change("Чёрные")}: <b>{counter[hand]["Чёрные"]}</b>    '
                    card_info += f'{change("Пики")}: <b>{counter[hand]["Пики"]}</b> '
                    card_info += f'{change("Крести")}: <b>{counter[hand]["Крести"]}</b>\n'
        case 'minimal':
            pass
            # todo дописать минималистичный вид карты
    return card_info


'''    ENDING SCRIPTS    '''


def end_check(room: {}) -> bool:
    for player_id in room['cards']:
        for hand in room['cards'][player_id]:
            if len(room['cards'][player_id][hand]) != 0:
                return False
    return True


async def end_message(room: {}):
    message = 'Игра закончилась!\n\nВот они, победители, слева на право:\n'

    players = []
    for player_id in room['players-ids']:
        player_name = mongo_users.find_one({'_id': player_id})['name']
        players.append((player_id, player_name, len(room['athanasias'][str(player_id)])))
    players.sort(reverse=True, key=lambda x: x[2])

    medal_owners = 0
    print_left_results = False
    printed_left_results = False

    for i in range(len(players) - 1):
        if print_left_results:
            message += '\n\nОстальные результаты:\n'
            print_left_results = False
            printed_left_results = True

        match medal_owners:
            case 0:
                message += f'\n🥇 '
            case 1:
                message += f'\n🥈 '
            case 2:
                message += f'\n🥉 '
            case _:
                message += f'\n🦧 '

        message += f'{players[i][1]} - {players[i][2]} {get_right_athanasius(players[i][2])}'

        if players[i][2] != players[i + 1][2] and medal_owners < 3:
            medal_owners += 1
            if medal_owners == 3:
                print_left_results = True

    if not printed_left_results:
        message += '\n\nОстальные результаты:\n'

    message += f'\n🦧 {players[-1][1]} - {players[-1][2]} {get_right_athanasius(players[-1][2])}'

    for player in players:
        await bot.send_message(player[0], message, reply_markup=types.ReplyKeyboardRemove())


'''    MISC    '''


def name_by_id(player_id: int) -> str:
    return mongo_users.find_one({'_id': player_id})['name']


def cleaning_the_room(room: {}):
    room['chosen']['card'] = ''
    room['chosen']['count'] = 1
    room['chosen']['count-red'] = 0
    room['chosen']['suits'] = {'Червы': 0, 'Буби': 0, 'Пики': 0, 'Крести': 0}
    room['chosen']['suitable-cards'] = {}

    mongo_games.update_one({'_id': room['_id']}, {'$set': {
        'chosen': room['chosen'],
        'active': False,
        'notes': {},
        'cards': {},
        'athanasias': {},
    }})


def cleaning_the_focus_mode_message(player_id):
    player = get_player_by_id(player_id)


def list_of_players(players_ids: []) -> str:
    players = mongo_users.find({'_id': {'$in': players_ids}})
    message_to_out = ''
    for player_index, player in enumerate(players, 1):
        message_to_out += f'\n<b>{player_index}. {player["name"]}</b>'
    return message_to_out


def suits_to_emoji(suits: {}) -> str:
    return suits['Червы'] * '♥' + suits['Буби'] * '♦' + suits['Пики'] * '♠' + suits['Крести'] * '♣'


def jokers(count: int, count_red: int) -> str:
    return change('Красные') * count_red + change('Чёрные') * (count - count_red)


def settings(room: {}) -> str:
    cfg = room['config']

    match cfg['type-of-deck']:
        case 36:
            type_of_deck = 'Неполная колода(<b>36</b> карт)'
        case 52:
            type_of_deck = 'Полная колода(<b>52</b> карты)'
        case _:
            type_of_deck = 'Колода с джокерами(<b>54</b> карты)'

    return 'Список игроков:\n' \
           + list_of_players(room["players-ids"]) + f'\n\nЧисло колод: <b>{cfg["count-of-decks"]}</b>\n' \
                                                    f'Число рук: <b>{cfg["count-of-hands"]}</b>\n' \
                                                    f'Тип колоды: {type_of_deck}'


def change(str_or_emoji: str) -> str:
    match str_or_emoji:
        case 'Красные' | 'Красный':
            return '🔴'
        case 'Чёрные' | 'Чёрный' | 'Черные' | 'Черный':
            return '⚫'
        case 'Червы':
            return '♥'
        case 'Буби':
            return '♦'
        case 'Пики':
            return '♠'
        case 'Крести':
            return '♣'
        case '2':
            return '2️⃣'
        case '3':
            return '3️⃣'
        case '4':
            return '4️⃣'
        case '5':
            return '5️⃣'
        case '6':
            return '6️⃣'
        case '7':
            return '7️⃣'
        case '8':
            return '8️⃣'
        case '9':
            return '9️⃣'
        case 'X':
            return '🔟'
        case 'J':
            return '🙎🏻‍♂J'
        case 'Q':
            return '👸🏻Q'
        case 'K':
            return '🤴🏻K'
        case 'A':
            return '♠A'
        case 'W':
            return '🃏Joker'
        case '♥':
            return 'Червы'
        case '♦':
            return 'Буби'
        case '♠':
            return 'Пики'
        case '♣':
            return 'Крести'
        case '2️⃣':
            return '2'
        case '3️⃣':
            return '3'
        case '4️⃣':
            return '4'
        case '5️⃣':
            return '5'
        case '6️⃣':
            return '6'
        case '7️⃣':
            return '7'
        case '8️⃣':
            return '8'
        case '9️⃣':
            return '9'
        case '🔟':
            return 'X'
        case '🙎🏻‍♂ J':
            return 'J'
        case '👸🏻 Q':
            return 'Q'
        case '🤴🏻 K':
            return 'K'
        case '♠ A':
            return 'A'
        case '🃏 Joker':
            return 'W'
        case _:
            return 'ERROR'


def get_rules(room: bool = True) -> str:
    file = 'rules/game.txt' if room else 'rules/bot.txt'
    rules = ''
    with codecs.open(file, 'r', 'utf_8_sig') as rules_file:
        rules += rules_file.read()
        return rules


def get_right_athanasius(count: int) -> str:
    if count == 1:
        return 'Афанасий'
    elif 5 > count > 1:
        return 'Афанасия'
    else:
        return 'Афанасиев'
