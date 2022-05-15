import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import math


def do_simulation(fname, floats):
    real_avg = np.average(floats)

    data_for_hist = []

    # nrml = np.random.normal(loc=np.average(floats), scale=np.std(floats), size=10000)
    # plt.hist(nrml, 100, density=True)

    # for i in range(50000):
    for i in range(10000):
        chosen = np.random.choice(floats, int(len(floats) / 50))
        chosen = np.average(chosen)

        chosen -= real_avg
        chosen /= real_avg
        chosen = abs(chosen)

        data_for_hist.append(chosen)

    data_for_hist = sorted(data_for_hist)
    plt.plot(data_for_hist, np.linspace(0, 1, len(data_for_hist)), label=fname[:-5])

        
    plt.xlabel("Величина P")
    plt.ylabel("Вероятность попасть в диапазон")
    # plt.title(fname)

    # plt.show()
    # plt.close()
    # plt.cla()
    # plt.clf()

    # exit(0)

def do_hist():
    plt.grid()
    n, bins, bars = plt.hist(floats, 100, density=True)

    plt.xlabel("Time")
    plt.ylabel("")
    plt.title(fname)

    plt.show()
    plt.close()
    plt.cla()
    plt.clf()


def calc_statistics(fname, floats):
    avg = np.average(floats)
    mean = np.mean(floats)
    max2 = np.max(floats)
    var = np.var(floats)
    total = np.sum(floats)
    std = np.std(floats)

    res = f"{fname} {2 ** (int(fname[4]) * int(fname[6]) / 2)} {avg:.2f} {mean:.2f} {max2:.2f}"
    print(res)

    # suppose n =
    # n = 1000
    # lambd = avg * 0.05 * math.sqrt(n) / std
    # ln = 2 ** 14 / 10
    # print(ln)

    # chebyshev = var / ((0.5 * avg) ** 2) / ln

    # print(0.05 * math.sqrt(8/3) / lambd)
    # print(f"{chebyshev:.8f}")
    # print()

    # 1. Используем хвостовые неравенства для оценки, сколько нам надо отрешать, чтобы
    #    предсказать оставшееся время.
    # 2. Посчитаем для каждого теста процент задач, который надо отрешать, чтобы ошибиться не более
    #    чем на 5 процентов (хотя в реальности нам ваще пофигу, даже точность в 20 процентов это очень
    #    и очень неплохо)
    # 2.5 На самом деле, точно эту оценку мы посчитаем только для тестов, где честно знаем общее время,
    #     а в боевых условиях (во всех остальных) мы его не знаем. То есть, мы немножко кривим душой и 
    #     говорим, что остальные тесты похожи на те, на которых мы все замерили. А потом мы скажем, что 
    #     вообщето остальные тесты похожи, давайте экстраполируем на тесты, из которых мы ничего не знаем
    # 3. Самый изи способ сделать какую-то оценку - это использовать неравенство Чебышева.
    #    var / ((0.1 * avg) ** 2 * n)    --- Chebyshev
    #    Мы получили какую-то оценку, 10 процентную погрешность, когда мы отрешали 1000 из 16000, но это 
    #    в общем-то уже неплохо.
    # 4. На самом деле, это прям ваще верхняя оценка на наших тестах, а в реальности получается еще и лучше.
    #    вставляем сюда картинку, говорим, что на самом деле на наших тестах все гораздо лучше.
    #
    #
    #
    #

def main():
    font = {'family': 'normal',
            'weight': 'normal',
            'size': 16}

    matplotlib.rc('font', **font)
    # matplotlib.rcParams['figure.figsize'] = (10, 5)
    # matplotlib.rcParams['figure.dpi'] = 300

    hist_dir = "./data/hist"
    # matstat_dir = "./data/matstat"

    for dirpath, dnames, fnames in os.walk(hist_dir):
        for fname in fnames:
            # if "PvS_7_4" in fname:
            if "and" in fname:
                continue
            # if "triples" in fname:
            #     continue

            hist_name = f"{hist_dir}/{fname}"

            with open(hist_name) as f:
                lines = f.readlines()

            floats = np.array([float(x.strip()) for x in lines])

            # do_simulation(fname, floats)

            calc_statistics(fname, floats)
            # exit(0)

    # plt.title("|S| = 1/50 |D|\n")
    # plt.grid()
    # plt.legend()
    # plt.show()

if __name__ == '__main__':
    main()
