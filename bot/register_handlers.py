from aiogram import Dispatcher

from bot.handlers.registration import register_handlers_reg
from bot.handlers.leader import register_handlers_leader
from bot.handlers.common import register_handlers_common
from bot.handlers.turn import register_main_loop_handlers
from bot.handlers.settings import register_handlers_settings

from bot.config import config


def register_handlers(dp: Dispatcher):
    register_handlers_leader(dp)
    register_main_loop_handlers(dp)
    register_handlers_settings(dp)
    register_handlers_reg(dp)
    register_handlers_common(dp, config.Athanasius_bot.admin_ids)
