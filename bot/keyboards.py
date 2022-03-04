from bot.config import mongo_users, mongo_games
from aiogram import types
import bot.scripts as sc


def default_menu() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(*['Чей ход', 'Афанасии', 'Мои карты'])


def admin_focus_mode() -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Вкл', 'Выкл'],
        ['admin_vkl', 'admin_vikl']
    )


'''    LEADER    '''


def leader_create() -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Да', 'Нет'],
        ['leader_yes', 'leader_no']
    )


def leader_choose_game(leader_games: []) -> types.InlineKeyboardMarkup:
    keyboard = make_menu(
        [game['title'] for game in leader_games],
        [f'leader_game_{_id}' for _id in [game['_id'] for game in leader_games]],
        3
    )
    return keyboard.add(*[
        types.InlineKeyboardButton(text='Создать', callback_data='leader_create'),
        types.InlineKeyboardButton(text='Выйти', callback_data='leader_out'),
    ])


def leader_game_menu(game: {}, user_id: int) -> types.InlineKeyboardMarkup:
    if game['leader-id'] == user_id:
        if game['active']:
            return make_menu(
                ['Закончить игру', 'Назад'],
                [f'leader_game_{game["_id"]}_end', f'leader_game_{game["_id"]}_back'],
            )
        else:
            return make_menu(
                ['Удалить', 'Настроить', 'Начать', 'Назад'],
                [
                    f'leader_game_{game["_id"]}_delete',
                    f'leader_configure_{game["_id"]}',
                    f'leader_game_{game["_id"]}_start',
                    f'leader_game_{game["_id"]}_back',
                ],
                3
            )
    else:
        return make_menu(['Назад'], [f'leader_game_{game["_id"]}_back'])


def leader_configuration_menu(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Число колод', 'Число рук', 'Тип колоды', 'Название комнаты', 'Удалить игроков', 'Добавить игроков', 'Назад'],
        [f'leader_configure_{game_id}_' + i for i in ['count', 'hands', 'type', 'title', 'delete', 'add', 'back']]
    )


def leader_configuration_count(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['-1', '+1', '-2', '+2', '-5', '+5', 'Назад'],
        [f'leader_configure_{game_id}_count_' + i for i in ['-1', '1', '-2', '2', '-5', '5', 'back']],
    )


def leader_configuration_hands(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['1', '2', 'Назад'],
        [f'leader_configure_{game_id}_hands_' + i for i in ['1', '2', 'back']],
    )


def leader_configuration_delete(player_id: int, game_id: int) -> types.InlineKeyboardMarkup:
    players_to_choose = []
    for game_player_id in mongo_games.find_one({'_id': game_id})['players-ids']:
        if game_player_id != player_id:
            player = mongo_users.find_one({'_id': game_player_id})
            players_to_choose.append(
                types.InlineKeyboardButton(
                    text=f"{player['name']}",
                    callback_data=f"leader_configure_{game_id}_delete_{game_player_id}")
            )
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(*players_to_choose)
    keyboard.add(types.InlineKeyboardButton(text="Назад", callback_data=f"leader_configure_{game_id}_delete_back"))
    return keyboard


def leader_configuration_add(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Поменять код', 'Назад'],
        [f'leader_configure_{game_id}_code_' + i for i in ['change', 'back']]
    )


def leader_configuration_type(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['36', '52', '54', 'Назад'],
        [f'leader_configure_{game_id}_type_' + i for i in ['36', '52', '54', 'back']],
        3
    )


def leader_end(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Да', 'Нет'],
        [f'leader_end_{game_id}_yes', f'leader_end_{game_id}_no']
    )


'''    SETTINGS    '''


def settings_menu() -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Имя', 'Подтверждения', 'Вид карт', 'Фокус-мод', 'Комнату', 'Выйти'],
        ['settings_name', 'settings_applies', 'settings_cardsView',
         'settings_focusMode', 'settings_room', 'settings_exit']
    )


def settings_applies() -> types.InlineKeyboardMarkup:
    keyboard = make_menu(
        ['Включить все', 'Выключить все', 'Включить/Выключить'],
        ['settings_applies_onAll', 'settings_applies_offAll', 'settings_applies_toggle']
    )
    keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='settings_applies_back'))
    return keyboard


def settings_cards_view() -> types.InlineKeyboardMarkup:
    return make_menu(
        ['text', 'emoji', 'Назад'],
        ['settings_cardsView_text', 'settings_cardsView_emoji', 'settings_cardsView_back']
    )


def settings_room(player_id: int) -> types.InlineKeyboardMarkup:
    user_games_ids = mongo_users.find_one({'_id': player_id})['games']
    games_titles = []
    for user_game_id in user_games_ids:
        games_titles.append(mongo_games.find_one({'_id': user_game_id})['title'])
    for i in range(len(user_games_ids)):
        user_games_ids[i] = 'settings_room_' + str(user_games_ids[i])
    keyboard = make_menu(games_titles, user_games_ids, 3)
    return keyboard.add(types.InlineKeyboardButton(text='Назад', callback_data='settings_room_back'))


def settings_applies_toggle() -> types.InlineKeyboardMarkup:
    return make_menu(
        ['1', '2', '3', '4', 'Назад'],
        ['settings_applies_toggle_card', 'settings_applies_toggle_count',
         'settings_applies_toggle_red-count', 'settings_applies_toggle_suits',
         'settings_applies_toggle_back'],
        4
    )


'''    TURN    '''


def choose_player(player_id: int, game: {}) -> types.InlineKeyboardMarkup:
    players_to_choose = []
    for player in mongo_users.find({'_id': {'$ne': player_id}}):
        if player['_id'] in game['queue']:
            players_to_choose.append(
                types.InlineKeyboardButton(
                    text=f"{player['name']}",
                    callback_data=f"ask_{game['_id']}_{player['_id']}")
            )
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(*players_to_choose)
    return keyboard


def card_menu(game: {}, player_id: int, callback: str, with_back: bool = False) -> types.InlineKeyboardMarkup:
    available_cards = sc.player_available_cards(game, player_id)

    row_width = 5
    if 4 > len(available_cards[0]) % 5 > 0:
        if len(available_cards[1]) <= 4:
            row_width = 4

    buttons = [[], []]

    for num in available_cards[0]:
        buttons[0].append(
            types.InlineKeyboardButton(text=sc.change(num), callback_data=f'{callback}_{num}'))

    for letter in available_cards[1]:
        buttons[1].append(types.InlineKeyboardButton(text=sc.change(letter), callback_data=f'{callback}_{letter}'))

    keyboard = types.InlineKeyboardMarkup(row_width=row_width)
    keyboard.add(*buttons[0])
    keyboard.add(*buttons[1])

    if with_back:
        keyboard.add(types.InlineKeyboardButton(text='Выбрать другого игрока', callback_data=f'{callback}_back'))

    return keyboard


def make_counter(callback: str) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['-1', '+1', '-2', '+2', '-5', '+5', 'Подтвердить'],
        [f'{callback}_-1', f'{callback}_1',
         f'{callback}_-2', f'{callback}_2',
         f'{callback}_-5', f'{callback}_5',
         f'{callback}_apply']
    )


def choose_suits(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['➕♥', '➕♦', '➕♠', '➕♣', '➖♥', '➖♦', '➖♠', '➖♣', 'Подтвердить'],
        [f'suits_{game_id}_' + i for i in ['h+', 'd+', 's+', 'c+', 'h-', 'd-', 's-', 'c-', 'apply']],
        4
    )


'''    APPLIES    '''


def apply_card(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Да', 'Нет'],
        [f'turnCard_{game_id}_' + i for i in ['yes', 'no']],
    )


def apply_count(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Да', 'Нет'],
        [f'cardsCount_{game_id}_' + i for i in ['yes', 'no']],
    )


def apply_red(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Да', 'Нет'],
        [f'cardsRed_{game_id}_' + i for i in ['yes', 'no']],
    )


def apply_suits(game_id: int) -> types.InlineKeyboardMarkup:
    return make_menu(
        ['Да', 'Нет'],
        [f'suits_{game_id}_' + i for i in ['yes', 'no']],
    )


'''    NOTES    '''


def notes_card_choose(game: {}) -> types.InlineKeyboardMarkup:
    cards = []
    match game['config']['type-of-deck']:
        case 36:
            for card in '6789XJQKA':
                cards.append(card)
        case 52:
            for card in '23456789XJQKA':
                cards.append(card)
        case 54:
            for card in '23456789XJQKAW':
                cards.append(card)
    buttons = []
    for card in cards:
        buttons.append(types.InlineKeyboardButton(text=sc.change(card), callback_data=f'notes_{game["_id"]}_{card}'))
    return types.InlineKeyboardMarkup().add(*buttons)


def notes(room: {}, player_id: int, card: str) -> types.InlineKeyboardMarkup:
    buttons = []
    _notes = room['notes'][f'{player_id}'][card]
    for i in range(len(_notes)):
        for j in range(4):
            buttons.append(types.InlineKeyboardButton(
                text=room['notes'][f'{player_id}'][card][i][j],
                callback_data=f'notes_{room["_id"]}_{card}_{i}_{j}'
            ))
    return types.InlineKeyboardMarkup(row_width=4).add(*buttons).add(
        types.InlineKeyboardButton(text='Назад', callback_data=f'notes_{room["_id"]}_back'))


'''    MENU CONSTRUCTOR    '''


def make_menu(
        buttons_texts: list,
        callbacks: list,
        row_width: int = 2,
        is_url: bool = False) -> types.InlineKeyboardMarkup:

    keyboard = types.InlineKeyboardMarkup(row_width=row_width)
    buttons = []

    if is_url:
        for button_text, url in zip(buttons_texts, callbacks):
            buttons.append(types.InlineKeyboardButton(text=button_text, url=url))
    else:
        for button_text, callback in zip(buttons_texts, callbacks):
            buttons.append(types.InlineKeyboardButton(text=button_text, callback_data=callback))

    return keyboard.add(*buttons)
