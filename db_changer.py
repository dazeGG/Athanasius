from bot.config import collection

if __name__ == '__main__':
    for user in collection.users.find():
        '''settings = user['settings']
        settings.pop('focus-mode')
        settings.pop('card-view')
        settings['focus-mode'] = False
        settings['focus-mode-message'] = ''
        settings['card-view'] = 'emoji'''
        print(user)
        # collection.users.update_one({'_id': user['_id']}, {'$set': {'settings': user['settings']}})
        # collection.games.update_one({'_id': game['_id']}, {'$set': {'': }})
