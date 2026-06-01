"""
Your benchmark logic — implement reset() and step().

Required: reset(), step()
Optional: parse_action(), close(), render()

parse_action(action) — override when your step() needs a different
representation than the JSON Schema you declare in benchanything.json.
The platform always delivers what the schema describes; use parse_action
to remap it before step() sees it.  Default is an identity (no-op).
"""
import asyncio
import threading
from poke_env.player import Player, RandomPlayer
from poke_env import LocalhostServerConfiguration


class LLMPlayer(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._action_event = threading.Event()
        self._pending_action = None
        self.current_battle_state = None
        self._state_event = threading.Event()

    def choose_move(self, battle):
        self.current_battle_state = {
            "active_pokemon": battle.active_pokemon.species,
            "active_hp": battle.active_pokemon.current_hp_fraction,
            "active_moves": [
                {"id": m.id, "type": str(m.type), "base_power": m.base_power}
                for m in battle.available_moves
            ],
            "available_switches": [p.species for p in battle.available_switches],
            "opponent_pokemon": battle.opponent_active_pokemon.species,
            "opponent_hp": battle.opponent_active_pokemon.current_hp_fraction,
        }
        self._state_event.set()
        self._action_event.clear()
        self._action_event.wait(timeout=30)
        action = self._pending_action
        self._pending_action = None
        return self.create_order(action)

    def set_action(self, action):
        self._pending_action = action
        self._action_event.set()


class ShowdownEnv:
    def __init__(self):
        self.player = LLMPlayer(
            server_configuration=LocalhostServerConfiguration,
            battle_format="gen9randombattle"
        )
        self.opponent = RandomPlayer(
            server_configuration=LocalhostServerConfiguration,
            battle_format="gen9randombattle"
        )
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._battle_future = None

    def reset(self, seed=None):
        self.player.current_battle_state = None
        self.player._state_event.clear()
        self._battle_future = asyncio.run_coroutine_threadsafe(
            self.player.battle_against(self.opponent, n_battles=1),
            self._loop
        )
        # Wait up to 30s for first state
        got_state = self.player._state_event.wait(timeout=30)

    def step(self, action_id):
        self.player._state_event.clear()
        self.player.set_action(action_id)
        self.player._state_event.wait(timeout=30)
        done = self._battle_future.done()
        reward = 1.0 if (done and self.player.n_won_battles > 0) else 0.0
        return self.player.current_battle_state, reward, done
