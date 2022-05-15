import matplotlib.pyplot as plt
import matplotlib
import os


def hist_plot():
    with open("./icnf_data/icnfs/PvS_8_4_13_1_1.hist") as f:
        lines = f.readlines()
    floats = [float(x.strip()) for x in lines]
    print(floats)
    plt.grid()
    n, bins, bars = plt.hist(floats, 100, log=True)

    plt.xlabel("Время решения, с")
    plt.ylabel("Количество задач")
    plt.title("Тест: PancakeSort_SelectionSort_8_4")

    # plt.show()
    plt.savefig('./experiments/ganak_data/results/simple_hist_2.png')


def scat_plot():
    filenames = [
        "./experiments/ganak_data/results/BubbleSort_6_4_PancakeSort_6_4",
        "./experiments/ganak_data/results/BubbleSort_6_4_SelectionSort_6_4",
        "./experiments/ganak_data/results/BubbleSort_7_4_PancakeSort_7_4",
    ]
    colors = ["g", "b", "r"]
    labels = ["BvP_6_4", "BvS_6_4", "BvP_7_4", "PvS_6_4"]
    for filename, color, label in zip(filenames, colors, labels):
        with open(filename) as f:
            lines = f.readlines()
        xs = []
        ys = []
        for line in lines:
            print(line.strip().split())
            sz, t_ganak, t_sat_solve = list(map(float, line.strip().split()))
            xs.append(sz)
            ys.append(t_sat_solve)

        plt.scatter(xs, ys, color=color, label=label, s=6)

    plt.xlim([0, 6600])
    plt.ylim([0, 40])
    plt.xlabel("Количество входных комбинаций")
    plt.ylabel("Время решения, с")
    plt.legend()
    plt.grid()
    # plt.show()
    plt.savefig('./experiments/ganak_data/results/random_cubes.png')


def mass_scat_plot():
    # s pmc 784 c time: 15.9407s 11.968829870223999
    for dirpath, dnames, fnames in os.walk("./experiments/ganak_data/results/paired_sources/"):
        for fname in fnames:
            with open(f"./experiments/ganak_data/results/paired_sources/{fname}") as f:
                lines = f.readlines()
            xs = []
            ys = []
            for line in lines:
                split = line.strip().split()
                sz, t_sat_solve = list(map(float, [split[2], split[-1]]))
                xs.append(sz)
                ys.append(t_sat_solve)

            plt.scatter(xs, ys, label=fname, s=6)

            plt.ylim([0, 40])
            plt.xlabel("Число входных комбинаций")
            plt.ylabel("Время решения, с")
            plt.legend()
            plt.grid()
            # plt.show()
            
            print(fname)
            if "6_4" in fname:
                print(sum(xs), 2 ** 24)
            if "7_4" in fname:
                print(sum(xs), 2 ** 28)
            if "8_4" in fname:
                print(sum(xs), 2 ** 32)
                
            plt.savefig(f'./experiments/ganak_data/results/raired_pics/{fname}.png')
            plt.close()
            plt.cla()
            plt.clf()


def main():
    font = {'family' : 'normal',
            'weight' : 'normal',
            'size'   : 11}


    matplotlib.rc('font', **font)
    matplotlib.rcParams['figure.figsize'] = (10, 5)
    matplotlib.rcParams['figure.dpi'] = 300

    # scat_plot()
    # hist_plot()
    mass_scat_plot()


if __name__ == "__main__":
    main()
