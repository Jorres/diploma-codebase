import sys
import os
import json
import random
import seaborn as sns

import numpy as np
import matplotlib.pyplot as plt

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import utils as U


def scatter_plot_fraction_of(experiment):
    result_file = f"./experiments/data_dist/{experiment}.txt"
    data = list()
    with open(result_file, "r") as f:
        for line in f.readlines():
            time, bits, dist, a, b, c, d = line.strip().split(" ")
            data.append((float(time), int(dist)))

    data = sorted(data)

    data = random.sample(data, 20) + data[:-20]

    times = list()
    dists = list()
    for time, dist in data:
        times.append(time)
        dists.append(dist)

    manager = plt.get_current_fig_manager()
    manager.resize(*manager.window.maxsize())
    fig, ax = plt.subplots()
    ax.scatter(dists, times) 

    ax.set_xlabel(r'Distance between nodes', fontsize=11)
    ax.set_ylabel(r'Time in seconds', fontsize=11)

    fig.suptitle(f"{experiment}", fontsize=15)

    fig.tight_layout()
    result_file = f"./experiments/data_dist/{experiment}.png"

    # if "4_3" not in experiment:
    #     plt.show()
    plt.savefig(result_file, dpi=500)

# def density_plot(experiment):
#     result_file = f"./experiments/data_dist/{experiment}.txt"
#     data = list()
#     with open(result_file, "r") as f:
#         for line in f.readlines():
#             time, bits, dist, a, b, c, d = line.strip().split(" ")
#             data.append((float(time), int(dist)))

#     data = random.sample(data, 1000)

#     times = list()
#     dists = list()
#     for time, dist in data:
#         times.append(time)
#         dists.append(dist)

#     sns.set_style('whitegrid')
#     sns.kdeplot(np.array(times), bw=0.5)


def main():
    experiments = ["BubbleSort_4_3", "BubbleSort_7_4", "BvP_4_3", "BvP_6_4","BvP_7_4"]
    for experiment in experiments:
        scatter_plot_fraction_of(experiment)


if __name__ == "__main__":
    main()
