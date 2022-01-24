import pysat
import time

from pysat.solvers import Maplesat as Solver

import aiger
from aiger_cnf import aig2cnf

import matplotlib.pyplot as plt
import numpy as np
import json

import formula_builder as FB
import graph as G

import main_equivalence as EQ

instances = []

def try_prune_all_pairs(g, formula, pool, last_min):
    global instances

    removed_set = set()
    with Solver(bootstrap_with=formula.clauses) as solver:
        for i in range(last_min, len(g.node_names)):
            name_1 = g.node_names[i]
            if name_1.startswith("v"):
                continue

            print(name_1)
            for j in range(i + 1, len(g.node_names)):
                name_2 = g.node_names[j]
                if name_2.startswith("v"):
                    continue

                # TODO this is temporary hack, because I forgot
                # to cut and replace, refer to another todo
                if name_1 == name_2:
                    continue

                results = []
                for modifier_i in [-1, 1]:
                    for modifier_j in [-1, 1]:
                        var_i = modifier_i * pool.v_to_id(name_1)
                        var_j = modifier_j * pool.v_to_id(name_2)
                        t1 = time.time()
                        results.append(solver.solve(
                            assumptions=[var_i, var_j]))
                        t2 = time.time()
                        instances.append(t2 - t1)

                if results == [True, False, False, True]:
                    assert name_2 not in removed_set
                    removed_set.add(name_2)
                    print("Found equivalent pair", name_1, name_2)
                    last_min = i
                    pruned = g.prune(name_1, name_2, True)
                    return g, True, last_min, pruned

                if results == [False, True, True, False] and not (name_1.startswith("i")) and not (name_2.startswith("i")):
                    assert name_2 not in removed_set
                    removed_set.add(name_2)
                    print("Found neg-equivalent pair", name_1, name_2)
                    last_min = i
                    pruned = g.prune(name_1, name_2, False)
                    return g, True, last_min, pruned

        return g, False, last_min, 0


def main():
    test_path_left = "./new_sorts/BubbleSort_4_3.aig"
    test_path_right = "./new_sorts/PancakeSort_4_3.aig"

    g1 = G.Graph(test_path_left)
    g2 = G.Graph(test_path_right)
     
    EQ.validate_naively(g1, g2)

    # t1 = time.time()
    # total_pruned = 0
    # last_min = 0
    # while True:
    #     formula = FB.make_formula_from_my_graph(g, pool)
    #     g, was_pruned, last_min, pruned_this_time = try_prune_all_pairs(
    #         g, formula, pool, last_min)
    #     total_pruned += pruned_this_time
    #     if not was_pruned:
    #         break

    # print(total_pruned)
    # t2 = time.time()
    # print(t2 - t1)


if __name__ == "__main__":
    main()
