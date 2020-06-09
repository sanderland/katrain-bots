import os
import sys
import time
from collections import defaultdict

from tqdm import tqdm

from katrain.core.sgf_parser import SGF

mode = "all"
mode_window = {"day": 24 * 3600, "week": 24 * 3600 * 7}
if len(sys.argv) > 1:
    mode = sys.argv[1]

size = defaultdict(int)
player = defaultdict(int)
handicap = defaultdict(int)
weird_games = []
dir = "sgf_ogs"
for root, dirs, files in os.walk(dir):
    for f in tqdm(files):
        try:
            filename = os.path.join(dir, f)
            if os.path.getmtime(filename) < time.time() - mode_window.get(mode, 4e9):
                continue
            game_tree = SGF.parse_file(filename)
            nmv = len(game_tree.nodes_in_tree)
            if nmv > 10:
                size[game_tree.get_property("SZ")] += 1
                player[game_tree.get_property("PW", "").replace("+", ":")] += 1
                player[game_tree.get_property("PB", "").replace("+", ":")] += 1
                handicap[len(game_tree.get_property("AB", []))] += 1

            if ":" in game_tree.get_property("SZ") or int(game_tree.get_property("SZ")) not in [9, 13, 19]:
                weird_games.append((game_tree.get_property("SZ"), nmv, f))
        except Exception as e:
            print(f"{f}: {e}")

for k, v in sorted(list(size.items()), key=lambda kv: -kv[1]):
    print(k, ":", v)

print()
for k, v in sorted(list(player.items()), key=lambda kv: -kv[1]):
    print(k, ":", v)

print()
for k, v in sorted(list(handicap.items()), key=lambda kv: -kv[1]):
    print(k, ":", v)

print()
for t in weird_games:
    print(t)
