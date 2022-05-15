import sys
import os
from tqdm import tqdm
import time
import copy
import random
import concurrent.futures

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import utils as U

from pysat.solvers import Maplesat as PysatSolver

from pycryptosat import Solver
from graph import Graph
from formula_builder import (
    TPoolHolder,
    make_formula_from_my_graph,
    generate_miter_without_xor,
    PicklablePool,
)

import hyperparameters as H
from domain_preprocessing import calculate_domain_saturations


def main():
    experiments = ["7_4"]
    for left_sort, right_sort in [
        ("Pancake", "Selection"),
        ("Selection", "Bubble"),
        ("Bubble", "Pancake"),
    ]:
        for test_shortname in experiments:
            left_schema_name = f"{left_sort}Sort_{test_shortname}"

            left_schema_file = f"./hard-instances/fraag/{left_schema_name}.aag"

            g = Graph(left_schema_file, "L")

            buckets = [
                g.node_names[x : x + H.BUCKET_SIZE]
                for x in range(0, len(g.node_names), H.BUCKET_SIZE)
            ]

            print(buckets)
            saturs = calculate_domain_saturations(g, buckets, "L", 1)
            saturs = [(a, len(c), 2 ** H.BUCKET_SIZE) for (a, b, c, tag) in saturs[0]]
            for satur in sorted(saturs):
                print(satur)
            exit(0)


if __name__ == "__main__":
    main()
