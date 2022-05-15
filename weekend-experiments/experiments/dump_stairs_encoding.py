import sys
import os
import pysat
from pysat.solvers import Maplesat as PysatSolver

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
from utils import prepare_shared_cnf_from_two_graphs
from formula_builder import generate_miter_scheme


def main():
    experiments = [
        "4_3",
        "6_4",
        "7_4",
    ]

    for test_shortname in experiments:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        g1 = Graph(left_schema_file, "L")
        g2 = Graph(right_schema_file, "R")

        shared_cnf, pool = prepare_shared_cnf_from_two_graphs(g1, g2)

        for mode in ["or", "stairs"]:
            final_cnf = generate_miter_scheme(
                shared_cnf, pool, g1, g2, mode=mode)
            cnf_file = f"./experiments/stairs_encoding/{test_shortname}_{mode}.cnf"
            pysat.formula.CNF(from_clauses=final_cnf).to_file(cnf_file)


if __name__ == "__main__":
    main()
