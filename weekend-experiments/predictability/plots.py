import matplotlib.pyplot as plt
import matplotlib
import os


def hist_plot(fname):
    with open(f"./data/hist/{fname}") as f:
        lines = f.readlines()

    floats = [float(x.strip()) for x in lines]

    doLog = True

    plt.grid()
    n, bins, bars = plt.hist(floats, 100, log=doLog)

    if doLog:
        target_name = f"{fname}_log"
    else:
        target_name = fname

    plt.xlabel("Время решения, с")
    plt.ylabel("Количество задач")
    plt.title(f"Тест: {fname[:-5]}")

    plt.savefig(f'./pics/{target_name}.png')
    plt.close()
    plt.cla()
    plt.clf()


def main():
    font = {'family': 'normal',
            'weight': 'normal',
            'size': 11}

    matplotlib.rc('font', **font)
    # matplotlib.rcParams['figure.figsize'] = (10, 5)
    matplotlib.rcParams['figure.dpi'] = 300

    for dirpath, dnames, fnames in os.walk("./data/hist"):
        for f in fnames:
            hist_plot(f)


if __name__ == "__main__":
    main()
