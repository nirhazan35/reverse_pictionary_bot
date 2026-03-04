"""
Telegram bot handlers.
Call register_handlers(bot) to wire up all command and message handlers.
"""

import logging
import math
import time
import threading

import config
from game_state import game_state, game_lock
from game_logic import lobby_countdown, evaluate_guess_async
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


def register_handlers(bot):
    """Register all Telegram handlers on the given bot instance."""

    # =============================
    # /start
    # =============================

    @bot.message_handler(commands=["start"])
    def handle_start(message):
        display_name = message.from_user.username or message.from_user.first_name or message.from_user.id
        logger.info(f"+ Start chat #{message.chat.id} from {display_name}")

        if message.chat.type != "private":
            logger.info(f"  /start received in non-private chat, ignoring")
            bot.reply_to(message, "Please DM me to interact with the bot.")
            return

        parts = message.text.split()
        if len(parts) > 1 and parts[1] == "guess":
            logger.info(f"  Deep link guess detected, routing to guess handler")
            handle_guess_command(message)
            return

        logger.info(f"  Sending welcome message with group link")

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Join Official Group", url=config.GROUP_LINK))

        bot.send_message(
            message.chat.id,
            "🎮 *Welcome to Reverse Pictionary!*\n\n"
            "🖼 An AI-generated image is shown in the group.\n"
            "✍️ Your goal: describe it as accurately as you can!\n"
            "🧠 The AI scores how close your prompt is to the original.\n"
            "🏆 The best description wins!\n\n"
            "*How to play:*\n"
            "1️⃣ Join the group below\n"
            "2️⃣ Someone starts a game with /start\\_game\n"
            "3️⃣ Click *Join Game* in the group\n"
            "4️⃣ When the image appears, DM me your best prompt\n"
            "5️⃣ Results are revealed when the timer ends!\n\n"
            "👇 *Join the group to get started:*",
            reply_markup=markup,
            parse_mode="Markdown",
        )

    # =============================
    # /guess
    # =============================

    @bot.message_handler(commands=["guess"])
    def handle_guess_command(message):
        user_id = message.from_user.id
        logger.info(f"Guess command from user {user_id}")

        if message.chat.type != "private":
            logger.info(f"  Rejected: not a private chat")
            bot.reply_to(message, "Please DM me to submit your guess.")
            return

        with game_lock:
            if game_state["status"] != "GUESSING":
                logger.info(f"  Rejected: no active guessing phase (status={game_state['status']})")
                bot.reply_to(message, "There is no active guessing phase.")
                return

            if user_id not in game_state["players"]:
                logger.info(f"  Rejected: user not in player list")
                bot.reply_to(message, "You are not part of this game.")
                return

            if user_id in game_state["guesses"]:
                logger.info(f"  Rejected: already submitted a guess")
                bot.reply_to(message, "You already submitted your guess.")
                return

            game_state["waiting_for_guess"].add(user_id)
            file_id = game_state.get("challenge_image_file_id")
            remaining = max(0, math.ceil(game_state["guess_end_time"] - time.time()))

        logger.info(f"  Waiting for guess prompt from user {user_id}")

        # Send challenge image and timer in DM
        if file_id:
            try:
                sent_dm = bot.send_photo(
                    message.chat.id,
                    photo=file_id,
                    caption=f"🖼 *Describe this image!*\n\n⏱ Time remaining: {remaining}s",
                    parse_mode="Markdown",
                )
                # Track this DM message so the countdown loop can update it
                with game_lock:
                    game_state["dm_challenge_messages"][user_id] = {
                        "chat_id": message.chat.id,
                        "message_id": sent_dm.message_id,
                    }
            except Exception as e:
                logger.warning(f"Failed to send challenge image in DM: {e}")

        bot.send_message(message.chat.id, "✍️ Send me your prompt now.")

    # =============================
    # /start_game
    # =============================

    @bot.message_handler(commands=["start_game"])
    def start_game(message):
        logger.info(f"start_game command in chat {message.chat.id} (type={message.chat.type})")

        if message.chat.type not in ["group", "supergroup"]:
            logger.info(f"  Rejected: not a group chat")
            bot.reply_to(message, "This command can only be used in a group.")
            return

        with game_lock:
            if game_state["status"] != "IDLE":
                logger.info(f"  Rejected: game already in progress (status={game_state['status']})")
                bot.reply_to(message, "⚠️ A game is already running.")
                return

            game_state["status"] = "LOBBY"
            game_state["group_id"] = message.chat.id
            game_state["players"] = {message.from_user.id}

        starter_name = message.from_user.username or message.from_user.first_name or message.from_user.id
        logger.info(f"  Lobby created in group {message.chat.id}, duration={config.LOBBY_DURATION}s")
        logger.info(f"  Game starter {starter_name} (id={message.from_user.id}) auto-joined")

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎮 Join Game", callback_data="join_game"))

        sent = bot.send_message(
            message.chat.id,
            "🎮 *New Game Starting!*\n\n"
            f"Time to join: {config.LOBBY_DURATION} s\n"
            "Players joined: 1",
            reply_markup=markup,
            parse_mode="Markdown",
        )

        with game_lock:
            game_state["lobby_message_id"] = sent.message_id
            game_state["lobby_end_time"] = time.time() + config.LOBBY_DURATION

        logger.info(f"  Lobby countdown thread started")
        threading.Thread(target=lobby_countdown, args=(bot,)).start()

    # =============================
    # JOIN BUTTON
    # =============================

    @bot.callback_query_handler(func=lambda call: call.data == "join_game")
    def handle_join(call):
        user_id = call.from_user.id
        logger.info(f"Join button pressed by user {user_id}")

        with game_lock:
            if game_state["status"] != "LOBBY":
                logger.info(f"  Rejected: lobby is closed (status={game_state['status']})")
                bot.answer_callback_query(call.id, "Lobby closed.")
                return

            if user_id in game_state["players"]:
                logger.info(f"  Rejected: user already joined")
                bot.answer_callback_query(call.id, "Already joined.")
                return

            game_state["players"].add(user_id)
            player_count = len(game_state["players"])
            group_id = game_state["group_id"]
            message_id = game_state["lobby_message_id"]

        logger.info(f"  User {user_id} joined the game (total players: {player_count})")
        bot.answer_callback_query(call.id, "You joined!")

        remaining = max(0, math.ceil(game_state.get("lobby_end_time", 0) - time.time()))

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎮 Join Game", callback_data="join_game"))

        try:
            bot.edit_message_text(
                "🎮 *New Game Starting!*\n\n"
                f"Time to join: {remaining}s\n"
                f"Players joined: {player_count}",
                chat_id=group_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=markup,
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Join edit error: {e}")

    # =============================
    # DM MESSAGE HANDLER
    # =============================

    @bot.message_handler(func=lambda m: True)
    def handle_messages(message):
        if message.chat.type != "private":
            return

        user_id = message.from_user.id

        with game_lock:
            if game_state["status"] != "GUESSING":
                bot.reply_to(message, "There is no active guessing phase.")
                return

            if time.time() > game_state["guess_end_time"]:
                logger.info(f"DM from user {user_id}: rejected, time is up")
                bot.reply_to(message, "⏰ Time is up! You can no longer submit a guess.")
                return

            if user_id not in game_state["waiting_for_guess"]:
                return

            if user_id in game_state["guesses"]:
                logger.info(f"DM from user {user_id}: rejected, already submitted")
                bot.reply_to(message, "You already submitted your guess.")
                return

            game_state["guesses"][user_id] = message.text
            game_state["waiting_for_guess"].remove(user_id)
            guess_count = len(game_state["guesses"])

        logger.info(f"Guess received from user {user_id}: \"{message.text}\" (total guesses: {guess_count})")

        # Evaluate immediately in background
        threading.Thread(target=evaluate_guess_async, args=(bot, user_id, message.text)).start()

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Return to Group", url=config.GROUP_LINK))

        bot.reply_to(message, "✅ Guess received!", reply_markup=markup)
