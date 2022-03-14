from aiogram import Dispatcher

from bot.handlers.rules import register_handlers_rules
from bot.handlers.settings import register_handlers_settings
from bot.handlers.registration import register_handlers_reg
from bot.handlers.leader import register_handlers_leader
from bot.handlers.turn import register_handlers_turn
from bot.handlers.common import register_handlers_common

from bot.config import config


def register_handlers(dp: Dispatcher):
    register_handlers_rules(dp)
    register_handlers_settings(dp)
    register_handlers_reg(dp)
    register_handlers_leader(dp)
    register_handlers_turn(dp)
    register_handlers_common(dp, config.Athanasius_bot.admin_ids)
