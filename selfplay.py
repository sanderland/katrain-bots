# This is a script I use to test the performance of AIs
import json
import pickle
import sys
import threading
import time
import traceback
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor

from elote import EloCompetitor
from katrain.core.ai import generate_ai_move
from katrain.core.base_katrain import Player
from katrain.core.constants import (
    AI_LOCAL,
    AI_RANK,
    AI_TENUKI,
    AI_WEIGHTED,
    OUTPUT_ERROR,
    OUTPUT_INFO,
    AI_PICK,
    AI_TERRITORY,
    PLAYER_AI,
    AI_POLICY,
)
from katrain.core.engine import KataGoEngine
from katrain.core.game import Game

from settings import Logger


class SPLogger(Logger):
    def players_info(self):
        return {bw: Player(player=bw, player_type=PLAYER_AI) for bw in "BW"}


DB_FILENAME = "ai_performance.pickle"


logger = Logger()

with open("config.json") as f:
    settings = json.load(f)
    DEFAULT_AI_SETTINGS = settings["ai"]


class AI:
    DEFAULT_ENGINE_SETTINGS = {
        "katago": "katrain/KataGo/katago",
        "model": "katrain/models/g170e-b15c192-s1672170752-d466197061.bin.gz",
        #        "config": "lowmem.cfg",
        "config": "kata_config.cfg",
        "max_visits": 1,
        "max_time": 300.0,
        "_enable_ownership": False,
    }
    NUM_THREADS = 128
    IGNORE_SETTINGS_IN_TAG = {"threads", "_enable_ownership", "katago"}  # katago for switching from/to bs version
    ENGINES = []
    LOCK = threading.Lock()

    def __init__(self, strategy, ai_settings, engine_settings=None):
        self.elo_comp = EloCompetitor(initial_rating=1000)
        self.strategy = strategy
        self.ai_settings = ai_settings
        self.engine_settings = engine_settings or {}
        fmt_settings = [
            f"{k}={v}"
            for k, v in {**self.ai_settings, **self.engine_settings}.items()
            if k not in AI.IGNORE_SETTINGS_IN_TAG
        ]
        self.name = f"{strategy}({ ','.join(fmt_settings) })"
        self.fix_settings()

    def fix_settings(self):
        self.ai_settings = {**DEFAULT_AI_SETTINGS[self.strategy], **self.ai_settings}
        self.engine_settings = {**AI.DEFAULT_ENGINE_SETTINGS, **self.engine_settings, "threads": AI.NUM_THREADS}

    def get_engine(self):  # factory
        with AI.LOCK:
            for existing_engine_settings, engine in AI.ENGINES:
                if existing_engine_settings == self.engine_settings:
                    return engine
            engine = KataGoEngine(logger, self.engine_settings)
            AI.ENGINES.append((self.engine_settings, engine))
            print("Creating new engine for", self.engine_settings, "now have", len(AI.ENGINES), "engines up")
            return engine

    def __eq__(self, other):
        return self.name == other.name  # should capture all relevant setting differences


try:
    with open(DB_FILENAME, "rb") as f:
        ai_database_loaded, all_results = pickle.load(f)
        ai_database = []
        for ai in ai_database_loaded:
            try:
                ai.fix_settings()  # update as required
                ai_database.append(ai)
            except:
                print("Error loading AI", ai.strategy)
except FileNotFoundError:
    ai_database = []
    all_results = []


def add_ai(ai):
    if ai not in ai_database:
        ai_database.append(ai)
        print(f"Adding {ai.name}")
    else:
        print(f"AI {ai.name} already in DB")


def retrieve_ais(selected_ais):
    return [ai for ai in ai_database if ai in selected_ais]


reference_ais = [
    AI(AI_RANK, {"kyu_rank": 18}, {}),
    AI(AI_RANK, {"kyu_rank": 14}, {}),
    AI(AI_RANK, {"kyu_rank": 10}, {}),
    AI(AI_RANK, {"kyu_rank": 8}, {}),
    AI(AI_RANK, {"kyu_rank": 6}, {}),
    AI(AI_RANK, {"kyu_rank": 4}, {}),
    AI(AI_RANK, {"kyu_rank": 2}, {}),
    AI(AI_RANK, {"kyu_rank": -1}, {}),
    AI(AI_RANK, {"kyu_rank": -3}, {}),
    AI(AI_POLICY, {}, {}),
]

test_ais = []
test_type = AI_LOCAL

if test_type == AI_WEIGHTED:
    for wf in [0.5, 1.0, 1.25, 1.5, 1.75, 2, 2.25]:
        test_ais.append(AI(AI_WEIGHTED, {"weaken_fac": wf}, {}))
elif test_type == AI_LOCAL:
    for pf in [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]:
        for pn in [0, 5, 10, 15, 25, 50]:
            test_ais.append(AI(AI_LOCAL, {"pick_frac": pf, "pick_n": pn}, {}))
elif test_type == AI_TENUKI:
    for pf in [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]:
        for pn in [0, 5, 10, 15, 25, 50]:
            test_ais.append(AI(AI_TENUKI, {"pick_frac": pf, "pick_n": pn}, {}))

for ai in reference_ais + test_ais:
    add_ai(ai)


N_GAMES = 1
BOARDSIZE = 19

ais_to_test = retrieve_ais(test_ais + reference_ais)

results = defaultdict(list)


def play_game(black: AI, white: AI):
    players = {"B": black, "W": white}
    engines = {"B": black.get_engine(), "W": white.get_engine()}
    tag = f"{black.name} vs {white.name}"
    try:
        game = Game(Logger(), engines, game_properties={"SZ": BOARDSIZE, "PW": white.strategy, "PB": black.strategy})
        game.root.add_list_property("PW", [white.name])
        game.root.add_list_property("PB", [black.name])
        start_time = time.time()
        while not game.end_result and game.current_node.depth < 300:
            p = game.current_node.next_player
            move, node = generate_ai_move(game, players[p].strategy, players[p].ai_settings)
        while not game.current_node.analysis_complete:
            time.sleep(0.001)
        game.game_id += f"_{game.current_node.format_score()}"
        sgf_out_msg = game.write_sgf(
            "sgf_selfplay/", trainer_config={"eval_show_ai": True, "save_feedback": [True], "eval_thresholds": [0]}
        )
        print(
            f"{tag}\tGame finished in {time.time()-start_time:.1f}s @ move {game.current_node.depth} {game.current_node.format_score()} -> {sgf_out_msg}",
            file=sys.stderr,
        )
        score = game.current_node.score
        if score > 0.3:
            black.elo_comp.beat(white.elo_comp)
        elif score < -0.3:
            white.elo_comp.beat(black.elo_comp)
        else:
            black.elo_comp.tied(white.elo_comp)

        results[tag].append(score)
        all_results.append((black.name, white.name, score))

    except Exception as e:
        print(f"Exception in playing {tag}: {e}")
        print(f"Exception in playing {tag}: {e}", file=sys.stderr)
        traceback.print_exc()
        traceback.print_exc(file=sys.stderr)


def fmt_score(score):
    return f"{'B' if score >= 0 else 'W'}+{abs(score):.1f}"


print(len(ais_to_test), "ais to test")
global_start = time.time()

for n in range(N_GAMES):
    for _, e in AI.ENGINES:  # no caching/replays
        e.shutdown()
    AI.ENGINES = []

    with ThreadPoolExecutor(max_workers=4 * AI.NUM_THREADS) as threadpool:
        for b in ais_to_test:
            for w in ais_to_test:
                if b is not w:
                    threadpool.submit(play_game, b, w)
    print("POOL EXIT")

    print(f"---- RESULTS ({n}) ----")
    for k, v in results.items():
        b_win = sum([s > 0.3 for s in v])
        w_win = sum([s < -0.3 for s in v])
        print(f"{b_win} {k} {w_win} : {list(map(fmt_score,v))}")

    print("---- ELO ----")
    for ai in sorted(ai_database, key=lambda a: -a.elo_comp.rating):
        wins = [(b, w, s) for (b, w, s) in all_results if s > 0.3 and b == ai.name or w == ai.name and s < -0.3]
        losses = [(b, w, s) for (b, w, s) in all_results if s < -0.3 and b == ai.name or w == ai.name and s > -0.3]
        draws = [(b, w, s) for (b, w, s) in all_results if -0.3 <= s <= 0.3 and (b == ai.name or w == ai.name)]
        out = f"{'*' if ai in ais_to_test else ' '} {ai.name}: ELO {ai.elo_comp.rating:.1f} WINS {len(wins)} LOSSES {len(losses)} DRAWS {len(draws)}"
        #    print("Wins:",wins)
        print(out)
        print(out, file=sys.stderr)

    with open(DB_FILENAME, "wb") as f:
        pickle.dump((ai_database, all_results), f)
    print(f"Saving {len(all_results)} to pickle", file=sys.stderr)

print(f"Done!Time taken {time.time()-global_start:.1f}s", file=sys.stderr)
