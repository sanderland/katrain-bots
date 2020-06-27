from katrain.core.base_katrain import Player

DEFAULT_PORT = 8587
import sys

from katrain.core.constants import *


class Logger:
    def log(self, msg, level=OUTPUT_INFO):
        if level <= OUTPUT_INFO:
            print(msg, file=sys.stderr)

    CONFIG = {"game/size": 19, "game/komi": 6.5}

    def config(self, key, default=None):
        return self.CONFIG.get(key, default)


bot_strategies = {
    "dev": (AI_SCORELOSS, {}, {"maxVisits": 500}),
    #    "dev": (AI_POLICY, {}, {}),
    "dev-beta": (AI_WEIGHTED, {}, {}),
    "strong": (AI_POLICY, {}, {}),
    "influence": (AI_INFLUENCE, {}, {}),
    "territory": (AI_TERRITORY, {}, {}),
    "balanced": (AI_PICK, {}, {}),
    "weighted": (AI_WEIGHTED, {}, {}),
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
