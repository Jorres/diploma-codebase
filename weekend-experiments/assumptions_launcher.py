from pycryptosat import Solver
from pysat.solvers import Maplesat
import json
import os
import pysat
import time

# task: print a comparison of:
# time solving with my program, tasks
# time solving with unit clauses, pycryptosat
# time solving with tasks, pycryptosat


def launch_comparison(tasks_file, cnf_file):
    cnf = pysat.formula.CNF(from_file=cnf_file)

    with open(tasks_file, "r") as f:
        tasks = json.load(f)['tasks']

    results = list()
    for (task_time, task_id, assumptions) in tasks:
        s = Solver()
        s.add_clauses(cnf.clauses)
        for assumption in assumptions:
            s.add_clause([assumption])
        t_st = time.time()
        s.solve()
        t_fn = time.time()
        results.append((task_time, t_fn - t_st))

    for (task_time, crypto_time) in list(reversed(sorted(results)))[:3]:
        print(f"My time: {task_time}, crypto clause time: {crypto_time}")


def main():
    for root, dirs, files in os.walk("./hard-instances/assumptions"):
        for file in files:
            launch_comparison(f"{root}/{file}", f"./hard-instances/cnf/{file[:-4]}.cnf")


if __name__ == "__main__":
    main()
