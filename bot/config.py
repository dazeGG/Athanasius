from pymongo import MongoClient

from aiogram import Bot, Dispatcher
from aiogram.types import ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from bot.config_reader import load_config


config = load_config("config/bot.ini")

bot = Bot(token=config.Athanasius_bot.token, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())

collection = MongoClient(config.Athanasius_bot.cluster_link)['athanasius']
mongo_users = collection['mongo_users']
mongo_games = collection['mongo_games']
