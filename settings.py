import sys

from katrain.core.base_katrain import KaTrainBase, Player
from katrain.core.constants import *

DEFAULT_PORT = 8587



class Logger(KaTrainBase):
    def __init__(self, debug_level=0):
        super().__init__(force_package_config=True, debug_level=debug_level)

    def log(self, msg, level=OUTPUT_INFO):
        if level <= OUTPUT_INFO:
            print(msg, file=sys.stderr)


bot_strategies = {
    "dev": (AI_SCORELOSS, {"strength": 0.5}, {"max_visits": 500}),
    #    "dev": (AI_WEIGHTED, {"weaken_fac": 0.5},{}),
    "balanced": (AI_SCORELOSS, {"strength": 1.0}, {"max_visits": 500}),
    #    "dev": (AI_POLICY, {}, {}),
    "dev-beta": (AI_SCORELOSS, {"strength": 0.5}, {"max_visits": 500}),
    "strong": (AI_POLICY, {}, {}),
    "influence": (AI_INFLUENCE, {}, {}),
    "territory": (AI_TERRITORY, {}, {}),
    #    "balanced": (AI_PICK, {}, {}),
    "weighted": (AI_WEIGHTED, {}, {"weaken_fac": 1.0}),
    "local": (AI_LOCAL, {}, {}),
    "tenuki": (AI_TENUKI, {}, {}),
    "18k": (AI_RANK, {"kyu_rank": 18}, {}),
    "14k": (AI_RANK, {"kyu_rank": 14}, {}),
    "10k": (AI_RANK, {"kyu_rank": 10}, {}),
    "6k": (AI_RANK, {"kyu_rank": 6}, {}),
    "2k": (AI_RANK, {"kyu_rank": 2}, {}),
    "2d": (AI_RANK, {"kyu_rank": -1}, {}),
}

engine_overrides = {"dev": {"maxVisits": 500}}

greetings = {
    "dev": "Point loss-weighted random move.",
    "dev-beta": "Play a policy-weighted move.",
    "strong": "Play top policy move.",
    "influence": "Play an influential style.",
    "territory": "Play a territorial style.",
    "balanced": "Play the best move out of a random selection.",
    "weighted": "Play a policy-weighted move.",
    "local": "Prefer local responses.",
    "tenuki": "Prefer to tenuki.",
    "18k": "Calibrated version of katrain-balanced for ~18k",
    "14k": "Calibrated version of katrain-balanced for ~14k",
    "10k": "Calibrated version of katrain-balanced for ~10k",
    "6k": "Calibrated version of katrain-balanced for ~6k",
    "2k": "Calibrated version of katrain-balanced for ~2k",
    "2d": "Calibrated version of katrain-balanced for ~2d",
}
