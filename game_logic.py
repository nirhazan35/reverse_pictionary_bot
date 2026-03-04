"""
Game logic — lobby countdown, guess countdown, and phase transitions.
All functions accept a `bot` instance to avoid circular imports.
"""

import logging
import time
import threading

import config
from game_state import game_state, game_lock, reset_game, _reset_game_state
from challenge_api import fetch_challenge_image
from evaluation_api import evaluate_prompt
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


def lobby_countdown(bot):
    """Count down the lobby timer, updating the message periodically."""
    logger.info(f"Lobby countdown started ({config.LOBBY_DURATION}s, tick={config.LOBBY_TICK}s)")
    remaining = config.LOBBY_DURATION

    while remaining >= 0:
        with game_lock:
            if game_state["status"] != "LOBBY":
                return
            group_id = game_state["group_id"]
            message_id = game_state["lobby_message_id"]
            player_count = len(game_state["players"])

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
                logger.warning(f"Lobby edit error: {e}")

        if remaining == 0:
            break

        time.sleep(config.LOBBY_TICK)
        remaining -= config.LOBBY_TICK

    logger.info("Lobby countdown finished")
    end_lobby(bot)


def end_lobby(bot):
    """Transition from LOBBY to GUESSING phase."""
    with game_lock:
        group_id = game_state["group_id"]
        player_count = len(game_state["players"])

        if player_count < config.MIN_PLAYERS:
            logger.info(f"Lobby ended with {player_count} players (min={config.MIN_PLAYERS}), cancelling game")
            bot.send_message(group_id, "❌ No players joined.")
            _reset_game_state()
            return

        logger.info(f"Lobby ended with {player_count} players, transitioning to GUESSING phase")

        game_state["status"] = "GUESSING"
        game_state["guesses"] = {}
        game_state["waiting_for_guess"] = set()
        game_state["guess_end_time"] = time.time() + config.GUESS_DURATION

    # Prepare deep link
    bot_username = bot.get_me().username
    deep_link = f"https://t.me/{bot_username}?start=guess"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✍️ Submit Guess Privately", url=deep_link))

    # Fetch image from API (outside lock)
    logger.info("Fetching challenge image...")
    try:
        image_bytes, image_id = fetch_challenge_image(config.CHALLENGE_API_URL)
    except Exception as e:
        logger.error(f"Failed to fetch challenge image: {e}")
        bot.send_message(group_id, f"⚠️ Failed to fetch challenge image: {e}")
        reset_game()
        return

    # Store image_id safely
    with game_lock:
        game_state["challenge_image_id"] = image_id

    # Send image
    logger.info(f"Sending challenge image to group {group_id}")
    try:
        sent = bot.send_photo(
            group_id,
            photo=image_bytes,
            caption=f"🖼 *Describe this image!*\n\n"
                    f"You have {config.GUESS_DURATION} seconds.",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    except Exception as e:
        logger.error(f"Failed to send challenge image: {e}")
        bot.send_message(group_id, f"⚠️ Failed to send image: {e}")
        reset_game()
        return

    with game_lock:
        game_state["guess_message_id"] = sent.message_id
        game_state["challenge_image_file_id"] = sent.photo[-1].file_id

    logger.info(f"Guess countdown started ({config.GUESS_DURATION}s, tick={config.GUESS_TICK}s)")
    threading.Thread(target=guess_countdown, args=(bot,)).start()


def guess_countdown(bot):
    """Count down the guess timer, updating the caption periodically."""
    remaining = config.GUESS_DURATION
    bot_username = bot.get_me().username
    deep_link = f"https://t.me/{bot_username}?start=guess"

    while remaining >= 0:
        with game_lock:
            if game_state["status"] != "GUESSING":
                return
            group_id = game_state["group_id"]
            message_id = game_state["guess_message_id"]
            guess_count = len(game_state["guesses"])
            dm_messages = dict(game_state["dm_challenge_messages"])

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✍️ Submit Guess Privately", url=deep_link))

        # Update group caption
        try:
            bot.edit_message_caption(
                caption="🖼 *Describe this image!*\n\n"
                        f"Time remaining: {remaining}s\n"
                        f"Guesses: {guess_count}",
                chat_id=group_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=markup,
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Guess edit error: {e}")

        # Update DM captions with live timer
        for uid, dm_info in dm_messages.items():
            try:
                bot.edit_message_caption(
                    caption=f"🖼 *Describe this image!*\n\n⏱ Time remaining: {remaining}s",
                    chat_id=dm_info["chat_id"],
                    message_id=dm_info["message_id"],
                    parse_mode="Markdown",
                )
            except Exception as e:
                if "message is not modified" not in str(e):
                    logger.warning(f"DM timer edit error for user {uid}: {e}")

        if remaining == 0:
            break

        time.sleep(config.GUESS_TICK)
        remaining -= config.GUESS_TICK

    logger.info("Guess countdown finished")
    end_guess_phase(bot)


def evaluate_guess_async(bot, user_id, prompt):
    """Evaluate a single guess in a background thread and store the result."""
    with game_lock:
        image_id = game_state.get("challenge_image_id")

    logger.info(f"  Async evaluation started for user {user_id}: \"{prompt}\"")

    try:
        score, image_bytes = evaluate_prompt(
            config.EVALUATE_API_URL, image_id, prompt
        )
        logger.info(f"  Async evaluation complete for user {user_id}: score={score}")

        with game_lock:
            game_state["evaluation_results"][user_id] = {
                "score": score,
                "image_bytes": image_bytes,
            }
            all_guessed = len(game_state["guesses"]) == len(game_state["players"])
            all_evaluated = len(game_state["evaluation_results"]) == len(game_state["guesses"])
            should_end_early = all_guessed and all_evaluated and game_state["status"] == "GUESSING"
            if should_end_early:
                game_state["status"] = "EVALUATING"  # Prevent countdown from also calling end_guess_phase

        if should_end_early:
            logger.info("All players submitted and evaluated — ending guess phase early")
            end_guess_phase(bot)
    except Exception as e:
        logger.warning(f"  Async evaluation failed for user {user_id}: {e}")


def end_guess_phase(bot):
    """Collect pre-evaluated results and announce them."""
    with game_lock:
        group_id = game_state["group_id"]
        guesses_copy = dict(game_state["guesses"])

    logger.info(f"Guess phase ended: {len(guesses_copy)} guesses received")

    if not guesses_copy:
        logger.info("No guesses submitted, resetting game")
        bot.send_message(group_id, "⏰ Guess phase ended!\nNo guesses submitted.")
        reset_game()
        return

    # Wait for any in-flight evaluations to finish (poll up to 10s)
    bot.send_message(group_id, "🧠 Finalizing results... Please wait.")
    waited = 0
    while waited < 10:
        with game_lock:
            done_count = len(game_state["evaluation_results"])
        if done_count >= len(guesses_copy):
            break
        logger.info(f"  Waiting for evaluations: {done_count}/{len(guesses_copy)} complete")
        time.sleep(1)
        waited += 1

    # Collect results
    with game_lock:
        eval_results = dict(game_state["evaluation_results"])

    logger.info(f"  {len(eval_results)}/{len(guesses_copy)} evaluations completed")

    results = []
    for user_id, prompt in guesses_copy.items():
        if user_id not in eval_results:
            logger.warning(f"  Skipping user {user_id}: evaluation not ready")
            continue

        try:
            user = bot.get_chat(user_id)
            username = user.username or user.first_name or str(user_id)
        except Exception:
            username = str(user_id)

        results.append({
            "user_id": user_id,
            "username": username,
            "prompt": prompt,
            "score": eval_results[user_id]["score"],
            "image_bytes": eval_results[user_id]["image_bytes"],
        })

    if not results:
        bot.send_message(group_id, "⚠️ Evaluation failed for all players.")
        reset_game()
        return

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"All evaluations complete. Winner: {results[0]['username']} with score {results[0]['score']}")

    # Build result summary
    result_text = "🏆 *Game Results*\n\n"
    for i, r in enumerate(results):
        rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔹"
        result_text += (
            f"{rank_emoji} *{r['username']}* — "
            f"*{round(r['score'], 2)}*\n"
        )

    bot.send_message(group_id, result_text, parse_mode="Markdown")
    logger.info("Results and generated images sent to group")

    # Send generated images
    for r in results:
        caption = (
            f"👤 *{r['username']}*\n"
            f"Score: *{round(r['score'], 2)} % *\n\n"
            f"Prompt:\n{r['prompt']}"
        )
        try:
            bot.send_photo(
                group_id,
                photo=r["image_bytes"],
                caption=caption,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Failed to send generated image: {e}")

    logger.info("Game complete, resetting state")
    reset_game()
