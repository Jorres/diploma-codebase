import sys
import os
from tqdm import tqdm
import json
import time

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from formula_builder import (
    TPoolHolder,
    make_formula_from_my_graph,
    generate_miter_without_xor,
)

from graph import Graph
from pycryptosat import Solver
import utils as U


def check_pairs_in_2m_schema(left_file, right_file, metainfo_file):
    g1 = Graph(left_file, "L")
    g2 = Graph(right_file, "R")
    g1.remove_identical()
    g2.remove_identical()
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)
    shared_cnf = generate_miter_without_xor(shared_cnf, pool, g1, g2)

    solver = Solver()
    solver.add_clauses(shared_cnf)

    metainfo = dict()
    pairs = list()

    for lname in tqdm(g1.node_names):
        for rname in g2.node_names:
            results = []
            result_runtimes = []
            for bit_i in [-1, 1]:
                for bit_j in [-1, 1]:
                    var_i = bit_i * pool.v_to_id(lname)
                    var_j = bit_j * pool.v_to_id(rname)
                    t1 = time.time()
                    results.append(solver.solve(assumptions=[var_i, var_j]))
                    t2 = time.time()
                    result_runtimes.append(t2 - t1)

            dist = g1.node_to_depth[lname] + g2.node_to_depth[rname]
            pairs.append((sum(result_runtimes), result_runtimes, (lname, rname, dist)))

    pairs_simplest = list(sorted(pairs))[:1000]
    pairs_hardest = list(sorted(pairs))[-1000:]

    metainfo["pairs_hardest"] = pairs_hardest
    metainfo["pairs_simplest"] = pairs_simplest
    U.dump_dict(metainfo, metainfo_file)


def pairs_in_2m_schema():
    experiments = ["4_3", "6_4", "7_4"]
    for test_shortname in experiments:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        # cnf_file = f"./hard-instances/cnf/{test_shortname}.cnf"
        # cnf_naive_file = f"./hard-instances/cnf/{test_shortname}_naive.cnf"

        metainfo_file = f"./experiments/pairs_in_2m_schema/{test_shortname}.txt"
        # tasks_dump_file = f"./hard-instances/assumptions/{test_shortname}.txt"

        check_pairs_in_2m_schema(
            left_schema_file,
            right_schema_file,
            metainfo_file,
        )


if __name__ == "__main__":
    pairs_in_2m_schema()
