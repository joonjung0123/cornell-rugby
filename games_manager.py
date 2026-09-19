import json
import os
import random
import time
import threading
from typing import Dict, Any, List, Optional

_LOCK = threading.Lock()

# Path to word data
_WORDS_FILE = os.path.join(os.path.dirname(__file__), "data", "wordle_words.json")

# Fallback basic list if file is ever missing
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

    # First pass: identify correct (green) matches
    for i in range(5):
        if guess[i] == solution[i]:
            res[i] = "correct"
            sol_counts[guess[i]] -= 1

    # Second pass: identify present (yellow) matches
    for i in range(5):
        if res[i] != "correct" and sol_counts.get(guess[i], 0) > 0:
            res[i] = "present"
            sol_counts[guess[i]] -= 1

    return res


class HeadToHeadWordleSession:
    def __init__(self):
        self.players: Dict[str, Dict[str, Any]] = {}  # session_id -> {name, slot: 1|2, last_active}
        self.scores: Dict[str, int] = {"player1": 0, "player2": 0}  # slot key -> score
        self.round_num = 1
        self.target_word = self._pick_word()
        self.round_start_time = time.time()
        self.round_ended = False
        self.round_winner_slot: Optional[str] = None  # "player1", "player2", or "tie"
        self.round_reason = ""
        self.next_round_ready: Dict[str, bool] = {"player1": False, "player2": False}
        
        # Player game state for the current round
        # slot: {guesses: [str], feedbacks: [[str]], finished: bool, won: bool, finish_time: float, attempts: int}
        self.round_player_state: Dict[str, Dict[str, Any]] = {
            "player1": self._init_player_round_state(),
            "player2": self._init_player_round_state()
        }

    def _pick_word(self) -> str:
        return random.choice(TARGET_WORDS).upper()

    def _init_player_round_state(self) -> Dict[str, Any]:
        return {
            "guesses": [],
            "feedbacks": [],
            "finished": False,
            "won": False,
            "finish_time": None,
            "attempts": 0,
        }

    def register_player(self, session_id: str, player_name: str) -> Dict[str, Any]:
        with _LOCK:
            now = time.time()
            clean_name = player_name.strip()[:20] or "Anonymous"

            # If session_id already registered, update name and activity
            if session_id in self.players:
                self.players[session_id]["name"] = clean_name
                self.players[session_id]["last_active"] = now
                return {"slot": self.players[session_id]["slot"], "name": clean_name}

            # Check if player1 or player2 slot is taken
            p1_entry = next((item for item in self.players.values() if item["slot"] == "player1"), None)
            p2_entry = next((item for item in self.players.values() if item["slot"] == "player2"), None)

            if p1_entry is None:
                assigned_slot = "player1"
            elif p2_entry is None:
                assigned_slot = "player2"
            else:
                # Both slots exist: replace the one that was least recently active
                if p1_entry["last_active"] <= p2_entry["last_active"]:
                    assigned_slot = "player1"
                    self.players = {k: v for k, v in self.players.items() if v["slot"] != "player1"}
                else:
                    assigned_slot = "player2"
                    self.players = {k: v for k, v in self.players.items() if v["slot"] != "player2"}

            self.players[session_id] = {
                "name": clean_name,
                "slot": assigned_slot,
                "last_active": now
            }
            return {"slot": assigned_slot, "name": clean_name}

    def unregister_player(self, session_id: str):
        with _LOCK:
            if session_id in self.players:
                del self.players[session_id]

    def get_player_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with _LOCK:
            return self.players.get(session_id)

    def ping(self, session_id: str):
        with _LOCK:
            if session_id in self.players:
                self.players[session_id]["last_active"] = time.time()

    def submit_guess(self, session_id: str, guess: str) -> Dict[str, Any]:
        with _LOCK:
            player = self.players.get(session_id)
            if not player:
                return {"success": False, "error": "Player not registered"}
            
            slot = player["slot"]
            pstate = self.round_player_state[slot]

            if self.round_ended or pstate["finished"]:
                return {"success": False, "error": "Round is already finished for you"}

            guess = guess.strip().upper()
            if len(guess) != 5:
                return {"success": False, "error": "Word must be 5 letters"}

            guess_lower = guess.lower()
            if guess_lower not in VALID_WORDS and guess_lower not in TARGET_WORDS:
                return {"success": False, "error": "Not in word list"}

            feed = evaluate_guess(guess, self.target_word)
            pstate["guesses"].append(guess)
            pstate["feedbacks"].append(feed)
            pstate["attempts"] += 1

            # Check if solved or reached max attempts
            if guess == self.target_word:
                pstate["finished"] = True
                pstate["won"] = True
                pstate["finish_time"] = time.time()
            elif len(pstate["guesses"]) >= 6:
                pstate["finished"] = True
                pstate["won"] = False
                pstate["finish_time"] = time.time()

            # Check if round should end now
            self._evaluate_round_completion()

            return {
                "success": True,
                "guess": guess,
                "feedback": feed,
                "finished": pstate["finished"],
                "won": pstate["won"]
            }

    def _evaluate_round_completion(self):
        """Called with lock held."""
        p1_state = self.round_player_state["player1"]
        p2_state = self.round_player_state["player2"]

        # Only evaluate if both players have finished their board
        if p1_state["finished"] and p2_state["finished"] and not self.round_ended:
            self.round_ended = True
            
            # Outcome logic according to user requirements:
            # 1. If both get it, the one who got it in fewer attempts wins.
            # 2. If both get it in the same number of attempts, the one who finished quicker wins.
            # 3. If only one gets it, that one wins.
            # 4. If neither gets it, 0 points for both (tie).
            p1_name = self._get_slot_name("player1")
            p2_name = self._get_slot_name("player2")

            if p1_state["won"] and p2_state["won"]:
                if p1_state["attempts"] < p2_state["attempts"]:
                    self.round_winner_slot = "player1"
                    self.scores["player1"] += 1
                    self.round_reason = f"{p1_name} solved in fewer attempts ({p1_state['attempts']} vs {p2_state['attempts']})!"
                elif p2_state["attempts"] < p1_state["attempts"]:
                    self.round_winner_slot = "player2"
                    self.scores["player2"] += 1
                    self.round_reason = f"{p2_name} solved in fewer attempts ({p2_state['attempts']} vs {p1_state['attempts']})!"
                else:
                    # Same attempts, tiebreaker is time taken
                    p1_duration = p1_state["finish_time"] - self.round_start_time
                    p2_duration = p2_state["finish_time"] - self.round_start_time
                    if p1_duration < p2_duration:
                        self.round_winner_slot = "player1"
                        self.scores["player1"] += 1
                        self.round_reason = f"{p1_name} solved faster ({p1_duration:.1f}s vs {p2_duration:.1f}s)!"
                    elif p2_duration < p1_duration:
                        self.round_winner_slot = "player2"
                        self.scores["player2"] += 1
                        self.round_reason = f"{p2_name} solved faster ({p2_duration:.1f}s vs {p1_duration:.1f}s)!"
                    else:
                        self.round_winner_slot = "tie"
                        self.round_reason = "It's an exact tie in attempts and time!"
            elif p1_state["won"] and not p2_state["won"]:
                self.round_winner_slot = "player1"
                self.scores["player1"] += 1
                self.round_reason = f"{p1_name} solved the word!"
            elif p2_state["won"] and not p1_state["won"]:
                self.round_winner_slot = "player2"
                self.scores["player2"] += 1
                self.round_reason = f"{p2_name} solved the word!"
            else:
                self.round_winner_slot = "tie"
                self.round_reason = "Neither player solved the word. 0 points awarded."

    def _get_slot_name(self, slot: str) -> str:
        for p in self.players.values():
            if p["slot"] == slot:
                return p["name"]
        return "Player 1" if slot == "player1" else "Player 2"

    def request_next_round(self, session_id: str) -> Dict[str, Any]:
        with _LOCK:
            player = self.players.get(session_id)
            if not player:
                return {"success": False, "error": "Player not registered"}
            
            slot = player["slot"]
            self.next_round_ready[slot] = True

            # If both players are ready (or if only 1 player is connected), start next round
            other_slot = "player2" if slot == "player1" else "player1"
            other_connected = any(p["slot"] == other_slot and (time.time() - p["last_active"] < 60) for p in self.players.values())

            if (self.next_round_ready["player1"] and self.next_round_ready["player2"]) or not other_connected:
                self._start_new_round()

            return {"success": True}

    def _start_new_round(self):
        """Called with lock held."""
        self.round_num += 1
        self.target_word = self._pick_word()
        self.round_start_time = time.time()
        self.round_ended = False
        self.round_winner_slot = None
        self.round_reason = ""
        self.next_round_ready = {"player1": False, "player2": False}
        self.round_player_state = {
            "player1": self._init_player_round_state(),
            "player2": self._init_player_round_state()
        }

    def reset_match(self):
        with _LOCK:
            self.scores = {"player1": 0, "player2": 0}
            self.round_num = 1
            self.target_word = self._pick_word()
            self.round_start_time = time.time()
            self.round_ended = False
            self.round_winner_slot = None
            self.round_reason = ""
            self.next_round_ready = {"player1": False, "player2": False}
            self.round_player_state = {
                "player1": self._init_player_round_state(),
                "player2": self._init_player_round_state()
            }

    def get_state_for_player(self, session_id: str) -> Dict[str, Any]:
        with _LOCK:
            now = time.time()
            player = self.players.get(session_id)
            if not player:
                return {"registered": False}

            player_slot = player["slot"]
            opponent_slot = "player2" if player_slot == "player1" else "player1"

            # Find opponent name and online status
            opponent_name = None
            opponent_online = False
            for p in self.players.values():
                if p["slot"] == opponent_slot:
                    opponent_name = p["name"]
                    opponent_online = (now - p["last_active"] < 15)

            p_state = self.round_player_state[player_slot]
            opp_state = self.round_player_state[opponent_slot]

            # In accordance with requirement #4:
            # "No, they should NOT be able to see each other's live progress, only find out after each round"
            # We only send opponent guesses and final target word if round_ended is True.
            opponent_data = {
                "name": opponent_name or ("Player 2" if player_slot == "player1" else "Player 1"),
                "online": opponent_online,
                "ready_next": self.next_round_ready.get(opponent_slot, False),
            }

            if self.round_ended:
                opponent_data["guesses"] = opp_state["guesses"]
                opponent_data["feedbacks"] = opp_state["feedbacks"]
                opponent_data["won"] = opp_state["won"]
                opponent_data["attempts"] = opp_state["attempts"]
                if opp_state["finish_time"]:
                    opponent_data["duration"] = round(opp_state["finish_time"] - self.round_start_time, 1)
                else:
                    opponent_data["duration"] = None

            my_data = {
                "name": player["name"],
                "slot": player_slot,
                "guesses": p_state["guesses"],
                "feedbacks": p_state["feedbacks"],
                "finished": p_state["finished"],
                "won": p_state["won"],
                "attempts": p_state["attempts"],
                "ready_next": self.next_round_ready.get(player_slot, False),
            }
            if p_state["finish_time"]:
                my_data["duration"] = round(p_state["finish_time"] - self.round_start_time, 1)
            else:
                my_data["duration"] = None

            # Only expose solution word when round is ended or when player has completed 6 attempts/solved
            solution_revealed = self.target_word if (self.round_ended or p_state["finished"]) else None

            return {
                "registered": True,
                "round_num": self.round_num,
                "scores": {
                    "player1": self.scores["player1"],
                    "player2": self.scores["player2"],
                },
                "me": my_data,
                "opponent": opponent_data,
                "round_ended": self.round_ended,
                "round_winner_slot": self.round_winner_slot,
                "round_reason": self.round_reason,
                "target_word": solution_revealed,
            }


# Global game session singleton
GAME_SESSION = HeadToHeadWordleSession()
