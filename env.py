import asyncio
import threading
import subprocess
import time
import os
import shutil
import traceback
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
        action = self._pending_action or "1"
        self._pending_action = None

        try:
            if isinstance(action, str) and action.startswith("switch:"):
                species = action.split("switch:")[1].strip().lower()
                for pokemon in battle.available_switches:
                    if pokemon.species.lower() == species:
                        return self.create_order(pokemon)
                if battle.available_switches:
                    return self.create_order(battle.available_switches[0])
            idx = int(str(action)) - 1
            if 0 <= idx < len(battle.available_moves):
                return self.create_order(battle.available_moves[idx])
            if battle.available_moves:
                return self.create_order(battle.available_moves[0])
            if battle.available_switches:
                return self.create_order(battle.available_switches[0])
        except Exception as e:
            print(f"choose_move error: {e}")
            traceback.print_exc()
            if battle.available_moves:
                return self.create_order(battle.available_moves[0])
            if battle.available_switches:
                return self.create_order(battle.available_switches[0])

    def set_action(self, action):
        self._pending_action = action
        self._action_event.set()


def find_executable(name):
    path = shutil.which(name)
    if path:
        return path
    common_paths = [
        r"C:\Program Files\nodejs\\" + name + ".cmd",
        r"C:\Program Files\nodejs\\" + name,
        f"/usr/bin/{name}",
        f"/usr/local/bin/{name}",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return name


def start_showdown_server():
    showdown_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pokemon-showdown")
    node = find_executable("node")
    npm = find_executable("npm")

    if not os.path.exists(showdown_path):
        print("Cloning Pokemon Showdown...")
        git = find_executable("git")
        subprocess.run([git, "clone", "https://github.com/smogon/pokemon-showdown.git", showdown_path], check=True)
        print("Running npm install...")
        subprocess.run([npm, "install"], cwd=showdown_path, check=True, shell=True)
        print("Building...")
        subprocess.run([node, "build"], cwd=showdown_path, check=True)

    print("Starting Pokemon Showdown server...")
    proc = subprocess.Popen(
        [node, "dist/server/index.js", "--no-security"],
        cwd=showdown_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(5)
    print("Showdown server started!")
    return proc


class ShowdownEnv:
    _server_proc = None
    _server_started = False

    def __init__(self):
        if not ShowdownEnv._server_started:
            ShowdownEnv._server_proc = start_showdown_server()
            ShowdownEnv._server_started = True

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
        try:
            self.player.current_battle_state = None
            self.player._state_event.clear()
            self._battle_future = asyncio.run_coroutine_threadsafe(
                self.player.battle_against(self.opponent, n_battles=1),
                self._loop
            )
            got = self.player._state_event.wait(timeout=60)
            print(f"reset: got_state={got}, state={self.player.current_battle_state}")
            return self.player.current_battle_state
        except Exception as e:
            print(f"RESET ERROR: {e}")
            traceback.print_exc()
            raise

    def step(self, action_id):
        try:
            self.player._state_event.clear()
            self.player.set_action(str(action_id))
            got = self.player._state_event.wait(timeout=30)
            print(f"step: action={action_id}, got_state={got}")
            done = self._battle_future.done()
            reward = 1.0 if (done and self.player.n_won_battles > 0) else 0.0
            state = self.player.current_battle_state
            print(f"step: returning state={state}, done={done}")
            return state, reward, done
        except Exception as e:
            print(f"STEP ERROR: {e}")
            traceback.print_exc()
            raise
