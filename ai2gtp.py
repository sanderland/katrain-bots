# This is a script that turns a KaTrain AI into a sort-of GTP compatible bot
import json
import math
import os
import random
import sys
import time
import traceback

from katrain.core.ai import generate_ai_move
from katrain.core.base_katrain import KaTrainBase
from katrain.core.constants import *
from katrain.core.constants import OUTPUT_ERROR, OUTPUT_INFO
from katrain.core.engine import EngineDiedException, KataGoEngine
from katrain.core.game import Game
from katrain.core.sgf_parser import Move

from rank_utils import rank_game
from settings import DEFAULT_PORT, Logger, bot_strategies

os.environ["KCFG_KIVY_LOG_LEVEL"] = os.environ.get("KCFG_KIVY_LOG_LEVEL", "warning")


bot = sys.argv[1].strip()
port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
REPORT_SCORE_THRESHOLD = 1.5
MAX_WAIT_ANALYSIS = 10
MAX_PASS = 3  # after opponent passes this many times, we always pass
len_segment = 80

logger = Logger(output_level=OUTPUT_INFO)


with open("config.json") as f:
    settings = json.load(f)
    all_ai_settings = settings["ai"]
ai_strategy, x_ai_settings, x_engine_settings = bot_strategies[bot]

ENGINE_SETTINGS = {
    "katago": "",  # actual engine settings in engine_server.py
    "model": "",
    "config": "",
    "threads": "",
    "max_visits": 5,
    "max_time": 5.0,
    "_enable_ownership": ai_strategy in [AI_SIMPLE_OWNERSHIP],
    "altcommand": f"python engine_connector.py {port}",
}

engine = KataGoEngine(logger, ENGINE_SETTINGS)


sgf_dir = "sgf_ogs/"

ai_settings = {**all_ai_settings[ai_strategy], **x_ai_settings}

ENGINE_SETTINGS.update(x_engine_settings)

print(f"starting bot {bot} using server port {port}", file=sys.stderr)
print("setup: ", ai_strategy, ai_settings, engine.override_settings, file=sys.stderr)
print(ENGINE_SETTINGS, file=sys.stderr)
print(ai_strategy, ai_settings, file=sys.stderr)

game = Game(Logger(), engine, game_properties={"SZ": 19, "PW": "OGS", "PB": "OGS", "AP": "katrain ogs bot"})


def rank_to_string(r):
    r = math.floor(r)
    if r >= 30:
        return f"{r - 30 + 1}d"
    else:
        return f"{30 - r}k"


def format_rank(rank):
    if rank <= 0:
        return f"{1 - rank:.1f}d"
    else:
        return f"{rank:.1f}k"


def malkovich_analysis(cn):
    start = time.time()
    while not cn.analysis_complete:
        time.sleep(0.001)
        if engine.katago_process.poll() is not None:  # TODO: clean up
            raise EngineDiedException(f"Engine for {cn.next_player} ({engine.config}) died")
        if time.time() - start > MAX_WAIT_ANALYSIS:
            logger.log(f"Waiting for analysis timed out!", OUTPUT_ERROR)
            return
    if cn.analysis_complete and cn.parent and cn.parent.analysis_complete:
        dscore = cn.analysis["root"]["scoreLead"] - cn.parent.analysis["root"]["scoreLead"]
        logger.log(
            f"dscore {dscore} = {cn.analysis['root']['scoreLead']} {cn.parent.analysis['root']['scoreLead']} at {move}...",
            OUTPUT_ERROR,
        )
        if cn.ai_thoughts:
            logger.log(
                f"AI thoughts: {cn.ai_thoughts} at move {cn.player} {cn.move.gtp()}",
                OUTPUT_INFO,
            )
        if abs(dscore) > REPORT_SCORE_THRESHOLD and (
            cn.player == "B" and dscore < 0 or cn.player == "W" and dscore > 0
        ):  # relevant mistakes
            favpl = "B" if dscore > 0 else "W"
            msg = f"MALKOVICH:{cn.player} {cn.move.gtp()} caused a significant score change ({favpl} gained {abs(dscore):.1f} points)"
            if cn.ai_thoughts:
                msg += f" -> Win Rate {cn.format_winrate()} Score {cn.format_score()} AI Thoughts: {cn.ai_thoughts}"
            else:
                comment = (
                    cn.comment(sgf=True, interactive=False)
                    .replace("\n", " ")
                    .replace("PV: B", "PV: ")
                    .replace("PV: W", "PV: ")
                )
                msg += f" -> Detailed move analysis: {comment}"
            print(msg, file=sys.stderr)
            sys.stderr.flush()


while True:
    line = input().strip()
    logger.log(f"GOT INPUT {line}", OUTPUT_ERROR)
    if line.startswith("boardsize"):
        _, *size = line.strip().split(" ")
        if len(size) > 1:
            size = f"{size[0]}:{size[1]}"
        else:
            size = int(size[0])
        game = Game(Logger(), engine, game_properties={"SZ": size, "PW": "OGS", "PB": "OGS", "AP": "katrain ogs bot"})
        logger.log(f"Init game {game.root.properties}", OUTPUT_ERROR)
    elif line.startswith("komi"):
        _, komi = line.split(" ")
        game.root.set_property("KM", komi.strip())
        game.root.set_property("RU", "chinese")
        logger.log(f"Setting komi {game.root.properties}", OUTPUT_ERROR)
    elif line.startswith("place_free_handicap"):
        _, n = line.split(" ")
        n = int(n)
        game.root.place_handicap_stones(n)
        handicaps = set(game.root.get_list_property("AB"))
        bx, by = game.board_size
        while len(handicaps) < min(n, bx * by):  # really obscure cases
            handicaps.add(
                Move((random.randint(0, bx - 1), random.randint(0, by - 1)), player="B").sgf(board_size=game.board_size)
            )
        game.root.set_property("AB", list(handicaps))
        game._calculate_groups()
        gtp = [Move.from_sgf(m, game.board_size, "B").gtp() for m in handicaps]
        logger.log(f"Chose handicap placements as {gtp}", OUTPUT_ERROR)
        print(f"= {' '.join(gtp)}\n")
        sys.stdout.flush()
        game.analyze_all_nodes()  # re-evaluate root
        while engine.queries:  # and make sure this gets processed
            time.sleep(0.001)
        continue
    elif line.startswith("set_free_handicap"):
        _, *stones = line.split(" ")
        game.root.set_property("AB", [Move.from_gtp(move.upper()).sgf(game.board_size) for move in stones])
        game._calculate_groups()
        game.analyze_all_nodes()  # re-evaluate root
        while engine.queries:  # and make sure this gets processed
            time.sleep(0.001)
        logger.log(f"Set handicap placements to {game.root.get_list_property('AB')}", OUTPUT_ERROR)
    elif line.startswith("genmove"):
        _, player = line.strip().split(" ")
        if player[0].upper() != game.current_node.next_player:
            logger.log(
                f"ERROR generating move: UNEXPECTED PLAYER {player} != {game.current_node.next_player}.", OUTPUT_ERROR
            )
            print(f"= ??\n")
            sys.stdout.flush()
            continue
        logger.log(f"{ai_strategy} generating move", OUTPUT_ERROR)
        game.current_node.analyze(engine)
        malkovich_analysis(game.current_node)
        game.root.properties[f"P{game.current_node.next_player}"] = [f"KaTrain {ai_strategy}"]
        num_passes = sum(
            [int(n.is_pass or False) for n in game.current_node.nodes_from_root[::-1][0 : 2 * MAX_PASS : 2]]
        )
        bx, by = game.board_size
        if num_passes >= MAX_PASS and game.current_node.depth - 2 * MAX_PASS >= bx + by:
            logger.log(f"Forced pass as opponent is passing {MAX_PASS} times", OUTPUT_ERROR)
            pol = game.current_node.policy
            if not pol:
                pol = ["??"]
            print(
                f"DISCUSSION:OK, since you passed {MAX_PASS} times after the {bx+by}th move, I will pass as well [policy {pol[-1]:.3%}].",
                file=sys.stderr,
            )
            move = game.play(Move(None, player=game.current_node.next_player)).move
        else:
            move, node = generate_ai_move(game, ai_strategy, ai_settings)
            logger.log(f"Generated move {move}", OUTPUT_ERROR)
        print(f"= {move.gtp()}\n")
        sys.stdout.flush()
        malkovich_analysis(game.current_node)
        continue
    elif line.startswith("play"):
        _, player, move = line.split(" ")
        node = game.play(Move.from_gtp(move.upper(), player=player[0].upper()), analyze=False)
        logger.log(f"played {player} {move}", OUTPUT_ERROR)
    elif line.startswith("final_score"):
        logger.log("line=" + line, OUTPUT_ERROR)
        if "{" in line:
            gamedata_str = line[12:]
            game.root.set_property("C", f"AI {ai_strategy} {ai_settings}\nOGS Gamedata: {gamedata_str}")
            try:
                gamedata = json.loads(gamedata_str)
                game.root.set_property(
                    "PW",
                    f"{gamedata['players']['white']['username']} ({rank_to_string(gamedata['players']['white']['rank'])})",
                )
                game.root.set_property(
                    "PB",
                    f"{gamedata['players']['black']['username']} ({rank_to_string(gamedata['players']['black']['rank'])})",
                )
                if any(gamedata["players"][p]["username"] == "katrain-dev-beta" for p in ["white", "black"]):
                    sgf_dir = "sgf_ogs_beta/"

            except Exception as e:
                _, _, tb = sys.exc_info()
                logger.log(f"error while processing gamedata: {e}\n{traceback.format_tb(tb)}", OUTPUT_ERROR)
        score = game.current_node.format_score()
        game.game_id += f"_{score}"
        logger.log(f"PROPERTIES {game.root.properties}", OUTPUT_ERROR)
        game.external_game = True
        filename = os.path.join(sgf_dir, game.generate_filename())
        sgf = game.write_sgf(
            filename, trainer_config={"eval_show_ai": True, "save_feedback": [True], "eval_thresholds": []}
        )
        logger.log(f"Game ended. Score was {score} -> saved sgf to {sgf}", OUTPUT_ERROR)
        sys.stderr.flush()
        sys.stdout.flush()
        time.sleep(0.1)  # ensure our logging gets handled
        print(f"= {score}\n")
        sys.stdout.flush()
        continue
    elif line.startswith("quit"):
        print(f"= \n")
        break
    print(f"= \n")
    sys.stdout.flush()
    sys.stderr.flush()
