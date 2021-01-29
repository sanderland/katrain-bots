# This is a script I use to test the performance of AIs
import json
import pickle
import random
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
    AI_INFLUENCE,
    AI_LOCAL,
    AI_PICK,
    AI_POLICY,
    AI_RANK,
    AI_TENUKI,
    AI_TERRITORY,
    AI_WEIGHTED,
    OUTPUT_ERROR,
    OUTPUT_INFO,
    PLAYER_AI,
    AI_SCORELOSS,
)
from katrain.core.engine import KataGoEngine
from katrain.core.game import Game

from settings import Logger


class SPLogger(Logger):
    pass

SAVE_RESULTS_FILENAME = "calibrated_ai_performance.scoreloss.pickle"
REFERENCE_DB_FILENAME = "calibrated_ai_performance.scoreloss.pickle"


logger = SPLogger()

with open("config.json") as f:
    settings = json.load(f)
    DEFAULT_AI_SETTINGS = settings["ai"]

INIT_RATING = 1000


class FixedEloCompetitor(EloCompetitor):  # rating doesn't update on wins/losses
    def __init__(self, initial_rating: float = 400, fixed: bool = False):
        super().__init__(initial_rating)
        self.fixed = fixed

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, value):
        if not self.fixed:
            self._rating = value

    def beat(self, competitor):
        win_es = self.expected_score(competitor)
        lose_es = competitor.expected_score(self)
        # update the winner's rating
        self.rating = self.rating + self._k_factor * (1 - win_es)
        # update the loser's rating
        competitor.rating = competitor.rating + self._k_factor * (0 - lose_es)

    def tied(self, competitor):
        self.verify_competitor_types(competitor)
        win_es = self.expected_score(competitor)
        lose_es = competitor.expected_score(self)
        # update the winner's rating
        self.rating = self.rating + self._k_factor * (0.5 - win_es)
        # update the loser's rating
        competitor.rating = competitor.rating + self._k_factor * (0.5 - lose_es)


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

    def __init__(self, strategy, ai_settings, engine_settings=None, rating=INIT_RATING, fixed_rating=False):
        self.elo_comp = FixedEloCompetitor(initial_rating=rating, fixed=fixed_rating)
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

    def __repr__(self):
        return f"{self.strategy}({self.ai_settings})"

    def __eq__(self, other):
        return self.name == other.name  # should capture all relevant setting differences


with open(REFERENCE_DB_FILENAME, "rb") as f:
    init_rating_db, _ = pickle.load(f)


pure_policy_ai = AI(AI_POLICY, {"opening_moves": 0}, {}, rating=1800, fixed_rating=True)
default_policy_ai = AI(AI_POLICY, {}, {}, rating=1700, fixed_rating=True)
random_ai = AI(AI_PICK, {"pick_frac": 0, "pick_n": 1}, {}, rating=-450, fixed_rating=True)

CALIBRATED_ELO = [
 (-2, 1263.9588011299913),
 (-1, 1199.6768869623193),
 (0, 1135.3949727946472),
 (1, 1071.113058626975),
 (2, 1006.8311444593029),
 (3, 942.5492302916308),
 (4, 878.2673161239586),
 (5, 813.9854019562865),
 (6, 749.7034877886144),
 (7, 685.4215736209424),
 (8, 621.1396594532702),
 (9, 556.8577452855981),
 (10, 492.5758311179259),
 (11, 428.2939169502538),
 (12, 364.0120027825817),
 (13, 299.7300886149095),
 (14, 235.44817444723742),
 (15, 171.16626027956522),
 (16, 106.88434611189314),
 (17, 42.60243194422105),
 (18, -21.679482223451032)]


fixed_ais = [pure_policy_ai, default_policy_ai] + [
    AI(AI_RANK, {"kyu_rank": kyu}, {}, rating=elo, fixed_rating=True) for kyu, elo in CALIBRATED_ELO
]

test_types = [AI_SCORELOSS]

test_ais = []
for test_type in test_types:
    if test_type == AI_WEIGHTED:
        for wf in [0.5, 1.0, 1.25, 1.5, 1.75, 2, 2.5, 3.0]:
            test_ais.append(AI(AI_WEIGHTED, {"weaken_fac": wf}, {}))
    elif test_type in [AI_LOCAL, AI_TENUKI, AI_TERRITORY, AI_INFLUENCE, AI_PICK]:
        for pf in [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0]:
            for pn in [0, 5, 10, 15, 25, 50]:
                test_ais.append(AI(test_type, {"pick_frac": pf, "pick_n": pn}, {}))
    elif test_type == AI_SCORELOSS:
        for str in [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
            test_ais.append(AI(AI_SCORELOSS, {"strength": str}, {"max_visits": 500, "max_time": 100}))


for ai in test_ais:
    find = [ref_ai for ref_ai in init_rating_db if ai == ref_ai]  # load ratings
    if len(find) != 1:
        print(ai, "not found")
        continue
    print(ai, "rating", find[0].elo_comp.rating)
    ai.elo_comp.rating = find[0].elo_comp.rating

BOARDSIZE = 19
N_ROUNDS = 50
N_GAMES_PER_PLAYER = 4
RATING_NOISE = 200
SIMUL_GAMES = 32  # 4 * AI.NUM_THREADS
OUTPUT_SGF = False
all_results = []


def play_game(black: AI, white: AI):
    players = {"B": black, "W": white}
    engines = {"B": black.get_engine(), "W": white.get_engine()}
    tag = f"{black.name} vs {white.name}"
    try:
        game = Game(SPLogger(), engines, game_properties={"SZ": BOARDSIZE, "PW": white.strategy, "PB": black.strategy})
        game.root.add_list_property("PW", [white.name])
        game.root.add_list_property("PB", [black.name])
        start_time = time.time()
        while not game.end_result and game.current_node.depth < 300:
            p = game.current_node.next_player
            move, node = generate_ai_move(game, players[p].strategy, players[p].ai_settings)
        while not game.current_node.analysis_complete:
            time.sleep(0.001)
        game.game_id += f"_{game.current_node.format_score()}"
        if OUTPUT_SGF:
            sgf_out_msg = game.write_sgf(
                "sgf_selfplay/", trainer_config={"eval_show_ai": True, "save_feedback": [True], "eval_thresholds": [0]}
            )
        else:
            sgf_out_msg = "<not saved>"
        print(
            f"{tag}\tGame finished in {time.time()-start_time:.1f}s @ move {game.current_node.depth} {game.current_node.format_score()} -> {sgf_out_msg}"
        )
        score = game.current_node.score
        if score > 0.3:
            black.elo_comp.beat(white.elo_comp)
        elif score < -0.3:
            white.elo_comp.beat(black.elo_comp)
        else:
            black.elo_comp.tied(white.elo_comp)
        all_results.append((black.name, white.name, score))

    except Exception as e:
        print(f"Exception in playing {tag}: {e}")
        print(f"Exception in playing {tag}: {e}", file=sys.stderr)
        traceback.print_exc()
        traceback.print_exc(file=sys.stderr)


def fmt_score(score):
    return f"{'B' if score >= 0 else 'W'}+{abs(score):.1f}"


global_start = time.time()

for n in range(N_ROUNDS):
    for _, e in AI.ENGINES:  # no caching/replays
        e.shutdown()
    AI.ENGINES = []

    with ThreadPoolExecutor(max_workers=SIMUL_GAMES) as threadpool:
        n_games = 0
        for b in test_ais:
            if b.elo_comp.rating > default_policy_ai.elo_comp.rating:
                continue  # bunch of near-identical policy ais
            ws = sorted(
                fixed_ais,
                key=lambda opp: abs(
                    (b.elo_comp.rating + (random.random() - 0.5) * 2 * RATING_NOISE) - opp.elo_comp.rating
                )
                + (b is opp) * 1e9,
            )[:N_GAMES_PER_PLAYER]
            for w in ws:
                if random.random() < 0.5:
                    threadpool.submit(play_game, w, b)
                else:
                    threadpool.submit(play_game, b, w)
                n_games += 1
        print(f"Playing {n_games} games")
    print("POOL EXIT")

    print("---- ELO ----")
    for ai in sorted(fixed_ais + test_ais, key=lambda a: -a.elo_comp.rating):
        wins = [(b, w, s) for (b, w, s) in all_results if s > 0.3 and b == ai.name or w == ai.name and s < -0.3]
        losses = [(b, w, s) for (b, w, s) in all_results if s < -0.3 and b == ai.name or w == ai.name and s > -0.3]
        draws = [(b, w, s) for (b, w, s) in all_results if -0.3 <= s <= 0.3 and (b == ai.name or w == ai.name)]
        out = f"{ai.name}: ELO {ai.elo_comp.rating:.1f} WINS {len(wins)} LOSSES {len(losses)} DRAWS {len(draws)}"
        print(out)

    with open(SAVE_RESULTS_FILENAME, "wb") as f:
        pickle.dump((test_ais, []), f)
    print(f"Saving {len(test_ais)} ais to pickle", file=sys.stderr)

print(f"Done!Time taken {time.time()-global_start:.1f}s", file=sys.stderr)
