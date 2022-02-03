import sys
import os
from tqdm import tqdm
import json
import time
import pysat

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from formula_builder import (
    TPoolHolder,
    make_formula_from_my_graph,
    generate_miter_without_xor,
    generate_miter_scheme,
)

from graph import Graph

from pysat.solvers import Maplesat as PysatSolver

import utils as U
import eq_checkers as EQ
import domain_preprocessing as DP


def extract_info(cnf, pool, g1, g2, metainfo, test_shortname):
    incompatible = DP.find_incompatible_nodes(g1, g2)

    learnt_clauses = []

    with PysatSolver(bootstrap_with=cnf) as solver:
        for name_1 in tqdm(g1.node_names):
            for name_2 in g2.node_names:

                for bit_1 in [-1, 1]:
                    for bit_2 in [-1, 1]:
                        if (name_1, name_2) in incompatible[bit_1][bit_2]:
                            continue

                        cnf_var_1 = bit_1 * pool.v_to_id(name_1)
                        cnf_var_2 = bit_2 * pool.v_to_id(name_2)

                        assumptions = [cnf_var_1, cnf_var_2]
                        # t1 = time.time()
                        res = U.solve_with_timeout(solver, assumptions, 1)
                        # t2 = time.time()
                        if not res:
                            learnt_clauses.append(assumptions)

    pysat.formula.CNF(from_clauses=cnf).to_file(
        f"./experiments/sample_binary_clauses/{test_shortname}.cnf"
    )

    with open(f"./experiments/sample_binary_clauses/{test_shortname}_learnt.txt", "w+") as f:
        for clause in learnt_clauses:
            f.write(f"{clause[0]} {clause[1]}\n")


def check_naive_vs_sampling(
    left_schema_file, right_schema_file, metainfo_file, test_shortname
):
    g1 = Graph(left_schema_file, "L")
    g2 = Graph(right_schema_file, "R")
    g1.remove_identical()
    g2.remove_identical()

    metainfo = dict()

    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)

    extract_info(shared_cnf, pool, g1, g2, metainfo, test_shortname)

    U.dump_dict(metainfo, metainfo_file)


def sample_binary_clauses():
    experiments = ["6_4"]
    for test_shortname in experiments:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        # cnf_file = f"./hard-instances/cnf/{test_shortname}.cnf"
        # cnf_naive_file = f"./hard-instances/cnf/{test_shortname}_naive.cnf"

        metainfo_file = f"./experiments/pairs_in_2m_schema/{test_shortname}.txt"
        # tasks_dump_file = f"./hard-instances/assumptions/{test_shortname}.txt"

        check_naive_vs_sampling(
            left_schema_file, right_schema_file, metainfo_file, test_shortname
        )


if __name__ == "__main__":
    sample_binary_clauses()
