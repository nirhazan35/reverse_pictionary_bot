"""
Bot entry point — initializes the bot and starts polling.
"""

import logging
import sys
import telebot
import requests

from config import BOT_TOKEN, HEALTH_CHECK_ENABLED, HEALTH_CHECK_URL
from handlers import register_handlers

logging.basicConfig(
    format="[%(levelname)s %(asctime)s %(module)s:%(lineno)d] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

register_handlers(bot)

if HEALTH_CHECK_ENABLED:
    try:
        resp = requests.get(HEALTH_CHECK_URL, timeout=5)
        resp.raise_for_status()
        logger.info(f"Health check passed: {HEALTH_CHECK_URL}")
    except Exception as e:
        logger.error(f"Health check failed ({HEALTH_CHECK_URL}): {e}")
        sys.exit(1)

logger.info("> Starting bot")
bot.infinity_polling()
logger.info("< Goodbye!")