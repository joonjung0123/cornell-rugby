import json
import os
import random
import time
import fcntl
from typing import Dict, Any, List, Optional

# Paths
_BASE_DIR = os.path.dirname(__file__)
_WORDS_FILE = os.path.join(_BASE_DIR, "data", "wordle_words.json")
_STATE_FILE = os.path.join(_BASE_DIR, "data", "games_state.json")
_LOCK_FILE = os.path.join(_BASE_DIR, "data", "games_state.lock")

# Fallback words
_DEFAULT_TARGETS = [
    "rugby", "scrum", "tryee", "pitch", "match", "tackl", "score", "field",
    "touch", "point", "coach", "world", "sport", "plant", "crane", "slate"
]

try:
    with open(_WORDS_FILE, "r") as f:
        _WORD_DATA = json.load(f)
        TARGET_WORDS: List[str] = _WORD_DATA.get("targets", _DEFAULT_TARGETS)
        VALID_WORDS: set = set(_WORD_DATA.get("valid", _DEFAULT_TARGETS))
except Exception:
    TARGET_WORDS = _DEFAULT_TARGETS
    VALID_WORDS = set(_DEFAULT_TARGETS)


def evaluate_guess(guess: str, solution: str) -> List[str]:
    """
    Standard Wordle feedback algorithm.
    Returns a list of 5 results: 'correct' (green), 'present' (yellow), 'absent' (gray).
    Correctly handles duplicate letters according to official Wordle rules.
    """
    guess = guess.lower()
    solution = solution.lower()
    res = ["absent"] * 5
    sol_counts: Dict[str, int] = {}

    for ch in solution:
        sol_counts[ch] = sol_counts.get(ch, 0) + 1

    # Pass 1: exact matches
    for i in range(5):
        if guess[i] == solution[i]:
            res[i] = "correct"
            sol_counts[guess[i]] -= 1

    # Pass 2: present elsewhere
    for i in range(5):
        if res[i] != "correct" and sol_counts.get(guess[i], 0) > 0:
            res[i] = "present"
            sol_counts[guess[i]] -= 1

    return res


def _pick_word() -> str:
    return random.choice(TARGET_WORDS).upper()


def _initial_round_player_state() -> Dict[str, Any]:
    return {
        "guesses": [],
        "feedbacks": [],
        "finished": False,
        "won": False,
        "finish_time": None,
        "attempts": 0,
    }


def _initial_state() -> Dict[str, Any]:
    return {
        "players": {},  # session_id -> {name, slot, last_active}
        "scores": {"player1": 0, "player2": 0},
        "round_num": 1,
        "target_word": _pick_word(),
        "round_start_time": time.time(),
        "round_ended": False,
        "round_winner_slot": None,
        "round_reason": "",
        "next_round_ready": {"player1": False, "player2": False},
        "round_player_state": {
            "player1": _initial_round_player_state(),
            "player2": _initial_round_player_state()
        }
    }


class PersistentWordleSession:
    """
    File-backed cross-process Wordle state manager with inter-process file locking.
    Guarantees both players (across multiple Gunicorn worker processes or single Flask server)
    share the EXACT same target word, scores, and round state.
    """

    def _with_state(self, func):
        os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
        with open(_LOCK_FILE, "a+") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                state = None
                if os.path.exists(_STATE_FILE):
                    try:
                        with open(_STATE_FILE, "r") as f:
                            state = json.load(f)
                    except Exception:
                        state = None

                if not state or not isinstance(state, dict) or "target_word" not in state:
                    state = _initial_state()
                    self._save_raw(state)

                result, save_needed = func(state)
                if save_needed:
                    self._save_raw(state)
                return result
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _save_raw(self, state: Dict[str, Any]):
        tmp_file = f"{_STATE_FILE}.tmp.{os.getpid()}"
        with open(tmp_file, "w") as f:
            json.dump(state, f)
        os.replace(tmp_file, _STATE_FILE)

    def register_player(self, session_id: str, player_name: str) -> Dict[str, Any]:
        def _op(state):
            now = time.time()
            clean_name = player_name.strip()[:20] or "Anonymous"
            players = state.setdefault("players", {})

            if session_id in players:
                players[session_id]["name"] = clean_name
                players[session_id]["last_active"] = now
                return ({"slot": players[session_id]["slot"], "name": clean_name}, True)

            p1_entry = next((item for item in players.values() if item["slot"] == "player1"), None)
            p2_entry = next((item for item in players.values() if item["slot"] == "player2"), None)

            if p1_entry is None:
                assigned_slot = "player1"
            elif p2_entry is None:
                assigned_slot = "player2"
            else:
                # Replace the least recently active player slot
                if p1_entry.get("last_active", 0) <= p2_entry.get("last_active", 0):
                    assigned_slot = "player1"
                    players = {k: v for k, v in players.items() if v["slot"] != "player1"}
                else:
                    assigned_slot = "player2"
                    players = {k: v for k, v in players.items() if v["slot"] != "player2"}

            players[session_id] = {
                "name": clean_name,
                "slot": assigned_slot,
                "last_active": now
            }
            state["players"] = players
            return ({"slot": assigned_slot, "name": clean_name}, True)

        return self._with_state(_op)

    def unregister_player(self, session_id: str):
        def _op(state):
            players = state.get("players", {})
            if session_id in players:
                del players[session_id]
            state["players"] = players
            if len(players) == 0:
                # Reset all game state when everyone leaves
                fresh = _initial_state()
                state.clear()
                state.update(fresh)
            return (True, True)

        return self._with_state(_op)

    def ping(self, session_id: str):
        def _op(state):
            players = state.get("players", {})
            if session_id in players:
                players[session_id]["last_active"] = time.time()
                return (True, True)
            return (False, False)

        return self._with_state(_op)

    def submit_guess(self, session_id: str, guess: str) -> Dict[str, Any]:
        def _op(state):
            players = state.get("players", {})
            player = players.get(session_id)
            if not player:
                return ({"success": False, "error": "Player not registered"}, False)

            slot = player["slot"]
            pstate = state["round_player_state"].setdefault(slot, _initial_round_player_state())

            if state.get("round_ended", False) or pstate.get("finished", False):
                return ({"success": False, "error": "Round is already finished for you"}, False)

            guess_clean = guess.strip().upper()
            if len(guess_clean) != 5:
                return ({"success": False, "error": "Word must be 5 letters"}, False)

            guess_lower = guess_clean.lower()
            if guess_lower not in VALID_WORDS and guess_lower not in TARGET_WORDS:
                return ({"success": False, "error": "Not in word list"}, False)

            target = state["target_word"]
            feed = evaluate_guess(guess_clean, target)
            pstate["guesses"].append(guess_clean)
            pstate["feedbacks"].append(feed)
            pstate["attempts"] = len(pstate["guesses"])

            if guess_clean == target:
                pstate["finished"] = True
                pstate["won"] = True
                pstate["finish_time"] = time.time()
            elif len(pstate["guesses"]) >= 6:
                pstate["finished"] = True
                pstate["won"] = False
                pstate["finish_time"] = time.time()

            # Check if round should end now (both players finished)
            p1_state = state["round_player_state"]["player1"]
            p2_state = state["round_player_state"]["player2"]

            if p1_state.get("finished") and p2_state.get("finished") and not state.get("round_ended", False):
                state["round_ended"] = True
                p1_name = "Player 1"
                p2_name = "Player 2"
                for p in players.values():
                    if p["slot"] == "player1":
                        p1_name = p["name"]
                    elif p["slot"] == "player2":
                        p2_name = p["name"]

                if p1_state.get("won") and p2_state.get("won"):
                    if p1_state["attempts"] < p2_state["attempts"]:
                        state["round_winner_slot"] = "player1"
                        state["scores"]["player1"] += 1
                        state["round_reason"] = f"{p1_name} solved in fewer attempts ({p1_state['attempts']} vs {p2_state['attempts']})!"
                    elif p2_state["attempts"] < p1_state["attempts"]:
                        state["round_winner_slot"] = "player2"
                        state["scores"]["player2"] += 1
                        state["round_reason"] = f"{p2_name} solved in fewer attempts ({p2_state['attempts']} vs {p1_state['attempts']})!"
                    else:
                        p1_dur = p1_state["finish_time"] - state["round_start_time"]
                        p2_dur = p2_state["finish_time"] - state["round_start_time"]
                        if p1_dur < p2_dur:
                            state["round_winner_slot"] = "player1"
                            state["scores"]["player1"] += 1
                            state["round_reason"] = f"{p1_name} solved faster ({p1_dur:.1f}s vs {p2_dur:.1f}s)!"
                        elif p2_dur < p1_dur:
                            state["round_winner_slot"] = "player2"
                            state["scores"]["player2"] += 1
                            state["round_reason"] = f"{p2_name} solved faster ({p2_dur:.1f}s vs {p1_dur:.1f}s)!"
                        else:
                            state["round_winner_slot"] = "tie"
                            state["round_reason"] = "It's an exact tie in attempts and time!"
                elif p1_state.get("won") and not p2_state.get("won"):
                    state["round_winner_slot"] = "player1"
                    state["scores"]["player1"] += 1
                    state["round_reason"] = f"{p1_name} solved the word!"
                elif p2_state.get("won") and not p1_state.get("won"):
                    state["round_winner_slot"] = "player2"
                    state["scores"]["player2"] += 1
                    state["round_reason"] = f"{p2_name} solved the word!"
                else:
                    state["round_winner_slot"] = "tie"
                    state["round_reason"] = "Neither player solved the word. 0 points awarded."

            return ({
                "success": True,
                "guess": guess_clean,
                "feedback": feed,
                "finished": pstate["finished"],
                "won": pstate["won"]
            }, True)

        return self._with_state(_op)

    def request_next_round(self, session_id: str) -> Dict[str, Any]:
        def _op(state):
            players = state.get("players", {})
            player = players.get(session_id)
            if not player:
                return ({"success": False, "error": "Player not registered"}, False)

            slot = player["slot"]
            state["next_round_ready"][slot] = True

            other_slot = "player2" if slot == "player1" else "player1"
            now = time.time()
            other_connected = any(p["slot"] == other_slot and (now - p.get("last_active", 0) < 60) for p in players.values())

            if (state["next_round_ready"]["player1"] and state["next_round_ready"]["player2"]) or not other_connected:
                state["round_num"] += 1
                state["target_word"] = _pick_word()
                state["round_start_time"] = time.time()
                state["round_ended"] = False
                state["round_winner_slot"] = None
                state["round_reason"] = ""
                state["next_round_ready"] = {"player1": False, "player2": False}
                state["round_player_state"] = {
                    "player1": _initial_round_player_state(),
                    "player2": _initial_round_player_state()
                }

            return ({"success": True}, True)

        return self._with_state(_op)

    def reset_match(self):
        def _op(state):
            players = state.get("players", {})
            fresh = _initial_state()
            fresh["players"] = players
            state.clear()
            state.update(fresh)
            return (True, True)

        return self._with_state(_op)

    def get_state_for_player(self, session_id: str) -> Dict[str, Any]:
        def _op(state):
            now = time.time()
            players = state.get("players", {})
            player = players.get(session_id)
            if not player:
                return ({"registered": False}, False)

            player_slot = player["slot"]
            opponent_slot = "player2" if player_slot == "player1" else "player1"

            opponent_name = None
            opponent_online = False
            for p in players.values():
                if p["slot"] == opponent_slot:
                    opponent_name = p["name"]
                    opponent_online = (now - p.get("last_active", 0) < 15)

            p_state = state["round_player_state"].get(player_slot, _initial_round_player_state())
            opp_state = state["round_player_state"].get(opponent_slot, _initial_round_player_state())

            opponent_data = {
                "name": opponent_name or ("Player 2" if player_slot == "player1" else "Player 1"),
                "online": opponent_online,
                "ready_next": state["next_round_ready"].get(opponent_slot, False),
            }

            if state.get("round_ended", False):
                opponent_data["guesses"] = opp_state.get("guesses", [])
                opponent_data["feedbacks"] = opp_state.get("feedbacks", [])
                opponent_data["won"] = opp_state.get("won", False)
                opponent_data["attempts"] = opp_state.get("attempts", 0)
                if opp_state.get("finish_time"):
                    opponent_data["duration"] = round(opp_state["finish_time"] - state["round_start_time"], 1)
                else:
                    opponent_data["duration"] = None

            my_data = {
                "name": player["name"],
                "slot": player_slot,
                "guesses": p_state.get("guesses", []),
                "feedbacks": p_state.get("feedbacks", []),
                "finished": p_state.get("finished", False),
                "won": p_state.get("won", False),
                "attempts": p_state.get("attempts", 0),
                "ready_next": state["next_round_ready"].get(player_slot, False),
            }
            if p_state.get("finish_time"):
                my_data["duration"] = round(p_state["finish_time"] - state["round_start_time"], 1)
            else:
                my_data["duration"] = None

            solution_revealed = state["target_word"] if (state.get("round_ended") or p_state.get("finished")) else None

            payload = {
                "registered": True,
                "round_num": state.get("round_num", 1),
                "scores": {
                    "player1": state.get("scores", {}).get("player1", 0),
                    "player2": state.get("scores", {}).get("player2", 0),
                },
                "me": my_data,
                "opponent": opponent_data,
                "round_ended": state.get("round_ended", False),
                "round_winner_slot": state.get("round_winner_slot"),
                "round_reason": state.get("round_reason", ""),
                "target_word": solution_revealed,
            }
            return (payload, False)

        return self._with_state(_op)


GAME_SESSION = PersistentWordleSession()
