"""
Game state management.
Holds the shared game state dictionary, lock, and reset function.
"""

import threading

game_lock = threading.Lock()

game_state = {
    "status": "IDLE",  # IDLE | LOBBY | GUESSING
    "group_id": None,
    "players": set(),
    "guesses": {},
    "waiting_for_guess": set(),
    "lobby_message_id": None,
    "guess_message_id": None,
    "guess_end_time": None,
    "challenge_image_id": None,
    "challenge_image_file_id": None,
    "dm_challenge_messages": {},  # {user_id: {"chat_id": ..., "message_id": ...}}
    "lobby_end_time": None,
    "evaluation_results": {},  # {user_id: {"score": ..., "image_bytes": ...}}
}


def _reset_game_state():
    """Reset game state. Caller MUST already hold game_lock."""
    game_state.update({
        "status": "IDLE",
        "group_id": None,
        "players": set(),
        "guesses": {},
        "waiting_for_guess": set(),
        "lobby_message_id": None,
        "guess_message_id": None,
        "guess_end_time": None,
        "challenge_image_id": None,
        "challenge_image_file_id": None,
        "dm_challenge_messages": {},
        "lobby_end_time": None,
        "evaluation_results": {},
    })


def reset_game():
    """Reset the game state back to IDLE (acquires lock)."""
    with game_lock:
        _reset_game_state()
