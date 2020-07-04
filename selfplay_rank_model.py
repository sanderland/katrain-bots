import json
import math
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


from sklearn.linear_model import LinearRegression

ranked = [ai for ai in ai_database if ai.strategy == AI_RANK]
calibrate = [ai for ai in ai_database if ai.strategy == AI_WEIGHTED]

kyu_elo = [(r.ai_settings["kyu_rank"], r.elo_comp.rating) for r in ranked]
wt_elo = [
    (
        [
            r.ai_settings["weaken_fac"],
            math.log(r.ai_settings["lower_bound"]),
            1 - r.ai_settings.get("pick_override", 1),
        ],
        r.elo_comp.rating,
    )
    for r in calibrate
]

x, y = zip(*wt_elo)
reg = LinearRegression().fit(x, y)
