import math, time


def gauss(data):
    return math.exp(-1 * (data) ** 2)


def median(data):
    sorteddata = sorted(data)
    lendata = len(data)
    index = (lendata - 1) // 2
    if lendata % 2:
        return sorteddata[index]
    else:
        return (sorteddata[index] + sorteddata[index + 1]) / 2.0


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
            -0.97222 * math.log(averagemod_rank) / (0.24634 + averagemod_rank * gauss(3.3208 * (norm_avemod_len_legal)))
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


def calculate_ranks(segment_stats, num_intersec):
    return {pl: calculate_rank_for_player(segment_stats, num_intersec, pl) for pl in "BW"}


def rank_game(game, len_segment):
    game.redo(999)
    moves = game.current_node.nodes_from_root[1:]  # without root
    if len(moves) < 1.5 * len_segment:
        return None

    while not all(m.analysis_complete for m in moves):
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
        if bounds[1] - bounds[0] >= 0.75 * len_segment:
            rank = calculate_ranks(policy_stats[bounds[0] : bounds[1]], num_intersec)
            ranks.append([bounds[0] + 1, bounds[1], rank])
    ranks[0][2]["B"] = median([sl[2]["B"] for sl in ranks[1:]])
    ranks[0][2]["W"] = median([sl[2]["W"] for sl in ranks[1:]])
    return ranks


# def calculate_rank_for_player_alternative_try(segment_stats, num_intersec, player):
#    non_obvious_moves = [
#        (nl, r, val)
#        for nl, r, val, pl in segment_stats
#        if val < (0.8 * (1 - (num_intersec - nl) / num_intersec * 0.5)) and pl == player
#    ]
#    num_legal, rank, value = zip(*non_obvious_moves)
#    # we expect r = (ll-npicked)/(npicked+1) so naively say npicked = (ll - r)/(r+1)
#    est_n_picked = [(nl - r) / (r + 1) for nl, r in zip(num_legal, rank)]
#    n_moves = np.mean(est_n_picked)
#    rank_kyu = (
#        math.log10(n_moves * 361 / num_intersec) - 1.9482
#    ) / -0.05737  # using the calibration curve of p:pick:rank
#    return rank_kyu
