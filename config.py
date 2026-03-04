"""
Centralized configuration for the bot.
Loads secrets from .env and defines all tunable game parameters.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================
# SECRETS (from .env)
# =============================

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROUP_LINK = os.environ["GROUP_LINK"]
API_BASE_URL = os.environ["API_BASE_URL"]

# =============================
# API ROUTES
# =============================

CHALLENGE_API_URL = f"{API_BASE_URL}/get_image"
EVALUATE_API_URL = f"{API_BASE_URL}/play_round"

# =============================
# GAME SETTINGS
# =============================

LOBBY_DURATION = 30       # Total lobby countdown in seconds
LOBBY_TICK = 10            # Lobby countdown update interval in seconds
GUESS_DURATION = 30      # Total guess countdown in seconds
GUESS_TICK = 10            # Guess countdown update interval in seconds
MIN_PLAYERS = 1           # Minimum players required to start a game

# =============================
# API SETTINGS
# =============================

HEALTH_CHECK_ENABLED = True   # Set to False to skip /health check on startup
HEALTH_CHECK_URL = f"{API_BASE_URL}/health"
API_TIMEOUT_CHALLENGE = 30    # Timeout for challenge image API (seconds)
API_TIMEOUT_EVALUATE = 50     # Timeout for evaluation API (seconds)
