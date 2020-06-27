import glob

from katrain.core.base_katrain import KaTrainBase
from katrain.core.game import Game, KaTrainSGF
from katrain.core.engine import KataGoEngine
from rank_utils import rank_game


def format_rank(rank):
    if rank <= 0:
        return f"{1-rank:5.1f}d"
    else:
        return f"{rank:5.1f}k"


if __name__ == "__main__":
    kt = KaTrainBase(force_package_config=True)
    e_config = kt.config("engine")
    e_config["max_visits"] = e_config["fast_visits"] = 1  # since it's just policy anyway
    engine = KataGoEngine(kt, e_config)

    for filename in glob.glob("sgf_ogs/*.sgf"):
        game = Game(kt, engine, move_tree=KaTrainSGF.parse_file(filename))
        size = game.board_size
        len_segment = 80

        ranks = rank_game(game, len_segment)
        if not ranks:
            continue
        print("* File name: {0:s}".format(filename))
        for start, end, rank in ranks:
            print(
                f"\tMove quality for moves {start:3d} to {end:3d}\tB: {format_rank(rank['B'])}\tW: {format_rank(rank['W'])}"
            )
