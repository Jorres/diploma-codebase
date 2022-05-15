import sys
import os
import copy
import time
from tqdm import tqdm

import pysat
from pysat.solvers import Maplesat as PysatSolver


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
import eq_checkers as EQ
import formula_builder as FB
import utils as U


def remove_and_clauses(g, pool, node, clauses):
    child_left, child_right = g.children[node]
    target_set = set([pool.v_to_id(x) for x in [node, child_left, child_right]])

    new_clauses = list()

    for clause in clauses:
        if not set([abs(x) for x in clause]).issubset(target_set):
            new_clauses.append(clause)

    return new_clauses


def generate_stuck_at_faults(experiment):
    aag_filename = f"./hard-instances/fraag/{experiment}"
    g_left = Graph(aag_filename, "L")
    g_right = Graph(aag_filename, "R")

    pool = FB.TPoolHolder()
    cnf_correct = FB.make_formula_from_my_graph(g_left, pool)
    cnf_faulty_template = FB.make_formula_from_my_graph(g_right, pool)

    miter_cnf = FB.generate_miter_scheme(
        cnf_correct.clauses + cnf_faulty_template.clauses, pool, g_left, g_right
    )

    pysat.formula.CNF(from_clauses=miter_cnf).to_file(
        f"./experiments/data_atpg/base_cnf_{experiment}.cnf"
    )

    all_results = []
    difficult_positive = []
    difficult_negative = []
    redundant_gates = set()
    positives = 0

    for node in tqdm(g_right.node_names):
        if node.startswith("i") or node.startswith("v"):
            continue

        miter_filtered = remove_and_clauses(g_right, pool, node, miter_cnf)
        right_cnf_var = pool.v_to_id(node)
        for additional_unit in [-1 * right_cnf_var, right_cnf_var]:
            miter_filtered.append([additional_unit])
            with PysatSolver(bootstrap_with=miter_filtered) as solver:
                t1 = time.time()

                result = U.solve_with_conflict_limit(solver, [], 5000000)

                t2 = time.time()
                if result is True:
                    positives += 1
                if result is False:
                    redundant_gates.add(node)

                aig_source_var_literal = g_right.source_name_to_lit[node]
                result_tuple = (
                    t2 - t1,
                    aig_source_var_literal,
                    additional_unit,
                    node,
                    result,
                )

                if t2 - t1 > 1:
                    if result is True:
                        difficult_positive.append(result_tuple)
                    elif result is False:
                        difficult_negative.append(result_tuple)

                all_results.append(result_tuple)
            miter_filtered.pop()

    n_and_gates = len(list(filter(lambda x: x.startswith("a"), g_right.node_names)))
    n_and_gates *= 2  # since we try two stuck-at-faults for every gate

    print(f"Positives ratio: {positives / n_and_gates}")

    U.dump_dict(
        difficult_positive,
        f"./experiments/data_atpg/difficult_positive_{experiment}.txt",
    )

    U.dump_dict(
        difficult_negative,
        f"./experiments/data_atpg/difficult_negative_{experiment}.txt",
    )

    U.dump_dict(
        sorted(all_results)[-10:],
        f"./experiments/data_atpg/some_top_tasks_{experiment}.txt",
    )

    return difficult_positive, difficult_negative, all_results


def main():
    for experiment in [
        # "4_3",
        # "6_4",
        # "7_4",
        # "4_8",
        # "8_4",
        "9_4",
    ]:
        generate_stuck_at_faults(f"BubbleSort_{experiment}.aag")
        generate_stuck_at_faults(f"PancakeSort_{experiment}.aag")


if __name__ == "__main__":
    main()
