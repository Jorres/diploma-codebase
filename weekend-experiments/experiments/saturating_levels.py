import sys
import os
import copy
import time
from tqdm import tqdm
from collections import defaultdict

import pysat
from pysat.solvers import Maplesat as PysatSolver

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
import eq_checkers as EQ
import formula_builder as FB
import utils as U
import domain_preprocessing as DP
import tree_decomposition as TD

# level
# find levels
# get info about levels - map{level, metainfo}
# metainfo - how good the lvl is covered, for example

# then try iterating from nodes from other places


def try_saturate_levels(experiment):
    g = Graph(f"./hard-instances/{experiment}", "L")
    g.remove_identical()

    pool = FB.TPoolHolder()

    buckets = DP.find_unbalanced_gates(g)
    domain_info, shift = DP.calculate_domain_saturations(g, buckets, "L", start_from=1)
    cnf = FB.make_formula_from_my_graph(g, pool)

    metainfo = dict()

    domain_info = sorted(domain_info)

    domain_info = U.extract_domains_with_saturation_one_into_cnf(
        cnf, pool, domain_info, metainfo
    )

    best_domains, cartesian_size = U.take_domains_until_threshold(
        domain_info, metainfo, 10000
    )

    baskets = TD.prepare_first_layer_of_baskets(best_domains)
    assert len(baskets) == len(best_domains)

    with PysatSolver(bootstrap_with=cnf) as solver:
        final_basket, skipped = TD.merge_baskets(baskets, solver, pool)

    level_size = defaultdict(int)
    for node in g.node_names:
        level_size[g.node_to_level[node]] += 1

    taken_on_level = defaultdict(int)
    for bucket_gates in final_basket.gate_names_for_bitvectors:
        for gate_name in bucket_gates:
            taken_on_level[g.node_to_level[gate_name]] += 1

    levels = []
    for level, size in level_size.items():
        if size > 10:
            levels.append((taken_on_level[level] / size, level, size))

    # sorted_levels = sorted(levels)
    # levels_candidates = sorted_levels[-int(len(sorted_levels) / 10):]
    # for item in levels_candidates:
    #     print(item)

    # final_basket.join_into_one_bucket()

    # input_gates = [f"v{i}" for i in range(g.n_inputs)]

    # while len(final_basket.bitvectors) < 10000:
    #     # select a single new gate somehow
    #     # add a new basket
    #     pass

    # for level, size in level_size.items():
    #     print(f"{level=} {size=} saturation={taken_on_level[level] / size}")


def main():
    for experiment in [
        # "BubbleSort_4_3.aag",
        "BubbleSort_6_4.aag",
        # "BubbleSort_7_4.aag",
        # "PancakeSort_4_3.aag",
        # "PancakeSort_6_4.aag",
        "PancakeSort_7_4.aag",
    ]:
        try_saturate_levels(experiment)


if __name__ == "__main__":
    main()
