from bot.config import mongo_users, mongo_games

if __name__ == '__main__':
    for user in mongo_users.find():
        pass
        # mongo_users.update_one({'_id': user['_id']}, {'$set': {'': }})
        # mongo_games.update_one({'_id': game['_id']}, {'$set': {'': }})
