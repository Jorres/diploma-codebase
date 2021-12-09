import matplotlib.pyplot as plt
import numpy as np
import json


def plot_bars():
    test_path_1 = "benchmark_results/results_suite_4npn_2"
    test_path_2 = "benchmark_results/results_suite_4npn_1_fastest_fences"

    data1 = dict()
    data2 = dict()
    with open(test_path_1) as f:
        data1 = json.load(f)
    with open(test_path_2) as f:
        data2 = json.load(f)

    plt.title("Top 30 functions from 4NPN, filtered by time to solve")

    plt.xlabel("Instance number")
    plt.ylabel("Time, (s)")

    data = []

    for i in range(1, 223):  # 4NPN dataset
        data.append((data1[str(i)]["total_runtime"],
                    data2[str(i)]["total_runtime"]))

    n_top_complex = 30
    x = np.arange(n_top_complex)

    s = sorted(data)
    x_data = []
    y_data = []
    for i in range(1, n_top_complex + 1):
        x_data.append(s[-i][0])
        y_data.append(s[-i][1])

    ax = plt.subplot(111)
    ax.bar(x - 0.1, x_data, width=0.2, color='r',
           align='center', label='naive')
    ax.bar(x + 0.1, y_data, width=0.2, color='b',
           align='center', label='DAG')
    ax.legend()

    plt.savefig("benchmark_results/plots/4npn_top_selected.png")
    plt.show()


def plot_scatter_total():
    test_path_1 = "benchmark_results/results_suite_4npn_2"
    test_path_2 = "benchmark_results/results_suite_4npn_1_fastest_fences"

    brute_data = dict()
    fence_data = dict()
    with open(test_path_1) as f:
        brute_data = json.load(f)
    with open(test_path_2) as f:
        fence_data = json.load(f)

    plt.title(
        "Sum of SAT + UNSAT on 4NPN, searching from size 1 until solution found")
    plt.xlabel("Naive encoding, time in seconds")
    plt.ylabel("DAG enumeration, time in seconds")

    plt.xscale('log')
    plt.yscale('log')
    plt.xlim(1, 150)
    plt.ylim(1, 150)
    # plt.axis('equal')

    x_data = []
    y_data = []

    for i in range(1, 223):  # 4NPN dataset
        brute_time = brute_data[str(i)]["total_runtime"]
        fence_time = fence_data[str(i)]["total_runtime"]
        if float(brute_time) > 1 and float(fence_time) > 1:
            x_data.append(brute_time)
            y_data.append(fence_time)

    plt.scatter(x_data, y_data)

    x = np.linspace(0, 200, 100)
    y = x
    plt.plot(x, y, "-r", label="y = x")
    plt.legend()

    plt.savefig("benchmark_results/plots/4npn_total.png")
    plt.show()

def plot_scatter_sat():
    test_path_1 = "benchmark_results/results_suite_4npn_2"
    test_path_2 = "benchmark_results/results_suite_4npn_1_fastest_fences"

    brute_data = dict()
    fence_data = dict()
    with open(test_path_1) as f:
        brute_data = json.load(f)
    with open(test_path_2) as f:
        fence_data = json.load(f)

    plt.title(
        "SAT times on 4NPN, run on minimum schema size possible")
    plt.xlabel("Naive encoding, time in seconds")
    plt.ylabel("DAG enumeration, time in seconds")

    plt.xscale('log')
    plt.yscale('log')
    plt.xlim(1, 150)
    plt.ylim(1, 150)
    # plt.axis('equal')

    x_data = []
    y_data = []

    for i in range(1, 223):  # 4NPN dataset
        brute_time = brute_data[str(i)]["sat_runtime"]
        fence_time = fence_data[str(i)]["sat_runtime"]
        if float(brute_time) > 1 and float(fence_time) > 1:
            x_data.append(brute_time)
            y_data.append(fence_time)

    plt.scatter(x_data, y_data)

    x = np.linspace(0, 200, 100)
    y = x
    plt.plot(x, y, "-r", label="y = x")
    plt.legend()

    plt.savefig("benchmark_results/plots/4npn_sat.png")
    plt.show()


if __name__ == "__main__":
    manager = plt.get_current_fig_manager()
    manager.resize(*manager.window.maxsize())
    plot_scatter_total()

    manager = plt.get_current_fig_manager()
    manager.resize(*manager.window.maxsize())
    plot_scatter_sat()

    manager = plt.get_current_fig_manager()
    manager.resize(*manager.window.maxsize())
    plot_bars()
