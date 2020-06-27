import math, glob, time, os
import numpy as np

from katrain.core.base_katrain import KaTrainBase
from katrain.core.game import Game, KaTrainSGF
from katrain.core.engine import KataGoEngine

def gauss(data):
    return math.exp(-1 * (data) ** 2)

def median(data):
    sorteddata = sorted(data)
    lendata = len(data)
    index = (lendata - 1) // 2
    if (lendata % 2):
        return sorteddata[index]
    else:
        return (sorteddata[index] + sorteddata[index + 1])/2.0

def averagemod(data):
    sorteddata = sorted(data)
    lendata = len(data)
    return sum(sorteddata[int(lendata * 0.2) : int(lendata * 0.8) + 1]) / (
        (int(lendata * 0.8) + 1) - int(lendata * 0.2)
    )  # average without the best and worst 20% of ranks


def calculate_rank_for_player(segment_stats, num_intersec, player):
        non_obvious_moves = [
            (nl, r, val)
            for nl, r, val, pl in segment_stats
            if nl is not None and val < (0.8 * (1 - (num_intersec - nl) / num_intersec * 0.5)) and pl == player
        ]
        num_legal, rank, value = zip(*non_obvious_moves)
        rank = list(rank)
        for (i, item) in enumerate(rank):
            if item > num_legal[i] * 0.09:
                rank[i] = num_legal[i] * 0.09
        rank = tuple(rank)
        averagemod_rank = averagemod(rank)
        averagemod_len_legal = averagemod(num_legal)
        norm_avemod_len_legal = averagemod_len_legal / num_intersec
        if averagemod_rank > 0.1:
            rank_kyu = (
                -0.97222
                * math.log(averagemod_rank)
                / (0.24634 + averagemod_rank * gauss(3.3208 * (norm_avemod_len_legal)))
                + 12.703 * (norm_avemod_len_legal)
                + 11.198 * math.log(averagemod_rank)
                + 12.28 * gauss(2.379 * (norm_avemod_len_legal))
                - 16.544
            )
        else:
            rank_kyu = -4
        if rank_kyu < -4:
            rank_kyu = -4
        return rank_kyu  # dan rank


def calculate_rank_for_player_alternative_try(segment_stats, num_intersec, player):
    non_obvious_moves = [
        (nl, r, val)
        for nl, r, val, pl in segment_stats
        if val < (0.8 * (1 - (num_intersec - nl) / num_intersec * 0.5)) and pl == player
    ]
    num_legal, rank, value = zip(*non_obvious_moves)
    # we expect r = (ll-npicked)/(npicked+1) so naively say npicked = (ll - r)/(r+1)
    est_n_picked = [(nl - r) / (r + 1) for nl, r in zip(num_legal, rank)]
    n_moves = np.mean(est_n_picked)
    rank_kyu = (
        math.log10(n_moves * 361 / num_intersec) - 1.9482
    ) / -0.05737  # using the calibration curve of p:pick:rank
    return rank_kyu


def calculate_ranks(segment_stats, num_intersec):
    return {pl: calculate_rank_for_player(segment_stats, num_intersec, pl) for pl in "BW"}


def rank_game(game, len_segment):
    game.redo(999)
    moves = game.current_node.nodes_from_root[1:]  # without root
    while not all(m.analysis_ready for m in moves):
        time.sleep(0.01)

    parent_policy_per_move = [move.parent.policy_ranking for move in moves]
    num_legal_moves = [sum(pv >= 0 for pv, _ in policy_ranking) for policy_ranking in parent_policy_per_move]
    policy_stats = [
        [(num_mv, rank, value, mv.player) for rank, (value, mv) in enumerate(policy_ranking) if mv == move.move][0]
        for move, policy_ranking, num_mv in zip(moves, parent_policy_per_move, num_legal_moves)
    ]
    size = game.board_size
    num_intersec = size[0] * size[1]
    half_seg = len_segment // 2

    ranks = [[1, len(moves), {}]]  # entire game
    for segment_mid in range(half_seg, len(moves), half_seg):
        bounds = (segment_mid - half_seg, min(segment_mid + half_seg, len(moves)))
        rank = calculate_ranks(policy_stats[bounds[0] : bounds[1]], num_intersec)
        ranks.append([bounds[0] + 1, bounds[1], rank])
    ranks[0][2]['B'] = median([sl[2]['B'] for sl in ranks[1:]])
    ranks[0][2]['W'] = median([sl[2]['W'] for sl in ranks[1:]])
    return ranks


if __name__ == "__main__":
    kt = KaTrainBase()
    e_config = kt.config("engine")
    e_config["max_visits"] = e_config["fast_visits"] = 1  # since it's just policy anyway
    engine = KataGoEngine(kt, e_config)

    for filename in [
        "sgf_ogs\katrain_tsstaff (6k) vs katrain-weighted (6k) 2020-06-09 15 52 45_W+72.9.sgf"
    ]:  # glob.glob("sgf_ogs/*.sgf"):
        game = Game(kt, engine, move_tree=KaTrainSGF.parse_file(filename))
        size = game.board_size
        len_segment = round(50 * size[0] * size[1] / 361)

        ranks = rank_game(game, len_segment)
        print("* File name: {0:s}".format(filename))
        for start, end, rank in ranks:
            print(f"\tMove quality for moves {start:3d} to {end:3d}\tB: {rank['B']:5.1f}k\tW: {rank['W']:5.1f}k")
