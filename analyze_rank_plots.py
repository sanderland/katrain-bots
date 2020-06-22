import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import kde


# load the output of analyze_rank.py, which has different row lengths
textfile = open("quality-est.csv", "r")
listr = textfile.readlines()
textfile.close()
data = np.empty((len(listr) - 1, 30,))
data[:] = np.nan

i = 0
for line in listr:
    if i > 0:  # do not read first line
        lstr = line.strip().split(",")[1:]
        data[i - 1, : len(lstr)] = np.array([float(v) for v in lstr])[:30]
    i += 1


fig = plt.figure()
_, axs = plt.subplots(3, 3, figsize=(15, 15))

xy = [[0, 2], [2, 4], [2, 6], [2, 8], [2, 10], [2, 12], [2, 14], [2, 16], [2, 18]]
coord = [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2], [2, 0], [2, 1], [2, 2]]
label = [
    ["ogs_kyu_rank", "game_kyu_rank"],
    ["game_kyu_rank", "Move quality of 0 - 50 moves"],
    ["game_kyu_rank", "Move quality of 25 - 75 moves"],
    ["game_kyu_rank", "Move quality of 50 - 100 moves"],
    ["game_kyu_rank", "Move quality of 75 - 125 moves"],
    ["game_kyu_rank", "Move quality of 100 - 150 moves"],
    ["game_kyu_rank", "Move quality of 125 - 175 moves"],
    ["game_kyu_rank", "Move quality of 150 - 200 moves"],
    ["game_kyu_rank", "Move quality of 175 - 225 moves"],
]

i = 0
for xyel in xy:

    x = xyel[0]
    y = xyel[1]
    plo = data[:, [x, y]][~np.isnan(data[:, [x, y]]).any(axis=1)]

    nbins = 300
    k = kde.gaussian_kde([plo[:, 0], plo[:, 1]])
    xi, yi = np.mgrid[-10 : 30 : nbins * 1j, -10 : 30 : nbins * 1j]
    zi = k(np.vstack([xi.flatten(), yi.flatten()]))

    axs[coord[i][0]][coord[i][1]].set_aspect("equal", adjustable="box")
    axs[coord[i][0]][coord[i][1]].set_xlim(-10, 30)
    axs[coord[i][0]][coord[i][1]].set_ylim(-10, 30)
    axs[coord[i][0]][coord[i][1]].set_xlabel(label[i][0])
    axs[coord[i][0]][coord[i][1]].set_ylabel(label[i][1])
    axs[coord[i][0]][coord[i][1]].pcolormesh(xi, yi, zi.reshape(xi.shape), cmap=plt.cm.magma)
    axs[coord[i][0]][coord[i][1]].plot([-10, 30], [-10, 30], linewidth=0.5, c="m")
    i += 1


plt.tight_layout()
plt.savefig("move_quality.png")
plt.show()
