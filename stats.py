import os
from katrain.core.sgf_parser import SGF
from collections import defaultdict
from tqdm import tqdm

size = defaultdict(int)
player = defaultdict(int)
handicap = defaultdict(int)
weird_games = []
dir = 'sgf_ogs'
for root, dirs, files in os.walk(dir):
    for f in tqdm(files):
        try:
            game_tree = SGF.parse_file(os.path.join(dir,f))
            nmv = len(game_tree.nodes_in_tree)
            if nmv > 10:
                size[game_tree.get_property('SZ')] += 1
                player[game_tree.get_property('PW','').replace('+',':')] += 1
                player[game_tree.get_property('PB','').replace('+',':')] += 1
                handicap[len(game_tree.get_property('AB', []))] += 1

            if ":" in game_tree.get_property('SZ') or int(game_tree.get_property('SZ')) not in [9,13,19]:
                weird_games.append( (game_tree.get_property('SZ'),nmv,f) )
        except Exception as e:
            print(f"{f}: {e}")

for k,v in sorted(list(size.items()), key=lambda kv:-kv[1]):
    print(k,":",v)

print()
for k,v in sorted(list(player.items()), key=lambda kv:-kv[1]):
    print(k,":",v)

print()
for k,v in sorted(list(handicap.items()), key=lambda kv:-kv[1]):
    print(k,":",v)

print()
for t in weird_games:
    print(t)