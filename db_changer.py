from bot.config import mongo_users

if __name__ == '__main__':
    for user in mongo_users.find():
        settings = user['settings']
        # settings.pop('focus-mode-message')
        settings['focus-mode'] = False
        settings['focus-mode-messages'] = {}
        settings['card-view'] = 'emoji'
        print(user)
        # collection.mongo_users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
        # collection.mongo_games.update_one({'_id': game['_id']}, {'$set': {'': }})
