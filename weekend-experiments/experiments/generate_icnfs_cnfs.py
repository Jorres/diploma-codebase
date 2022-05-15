import sys
import os
import pysat
import time
from pysat.solvers import Maplesat as PysatSolver

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
from main import generate_inccnf
from utils import prepare_shared_cnf_from_two_graphs
from formula_builder import generate_miter_scheme
import domain_preprocessing as DP
import hyperparameters as H


def generate_icnf(f1, f2, file_name):
    g1 = Graph(f1, "L")
    g2 = Graph(f2, "R")

    metainfo = dict()

    t1 = time.time()
    buckets_left = DP.find_unbalanced_gates(g1)
    buckets_right = DP.find_unbalanced_gates(g2)
    t2 = time.time()
    metainfo["sampling_balancedness"] = t2 - t1

    t1 = time.time()
    domains_info_left, shift = DP.calculate_domain_saturations(
        g1, buckets_left, tag="L", start_from=1
    )
    domains_info_right, _ = DP.calculate_domain_saturations(
        g2, buckets_right, tag="R", start_from=shift + 1
    )
    t2 = time.time()
    metainfo["calculating_saturation"] = t2 - t1

    generate_inccnf(g1, g2, domains_info_left, domains_info_right, metainfo, file_name)


def generate_cnf(f1, f2, file_name):
    g1 = Graph(f1, "L")
    g2 = Graph(f2, "R")

    shared_cnf, pool = prepare_shared_cnf_from_two_graphs(g1, g2)

    miter_cnf = generate_miter_scheme(shared_cnf, pool, g1, g2, mode="or")

    pysat.formula.CNF(from_clauses=miter_cnf).to_file(file_name)


def generate_icnf_filename(type, test_size):
    return os.path.join(
        "icnf_data",
        "icnfs",
        f"{type}_{test_size}_{H.BUCKET_SIZE}_{H.BUCKETS_FROM_LEFT}_{H.BUCKETS_FROM_RIGHT}.icnf",
    )


def generate_cnf_filename(type, test_size):
    return os.path.join("cnf_data", "cnfs", f"{type}_{test_size}.cnf")


def main():
    for dirpath, dnames, fnames in os.walk("./icnf_data/BubbleSort"):
        for bubble_fname in fnames:
            bubble = os.path.join("icnf_data", "BubbleSort", bubble_fname)
            pancake = bubble.replace("Bubble", "Pancake")
            selection = bubble.replace("Bubble", "Selection")

            test_size = bubble_fname.split("_", 1)[1]
            test_size = test_size.split(".")[0]

            # icnf_filename = generate_icnf_filename("BvP", test_size)
            # generate_icnf(bubble, pancake, icnf_filename)
            # cnf_filename = generate_cnf_filename("BvP", test_size)
            # generate_cnf(bubble, pancake, cnf_filename)

            # icnf_filename = generate_icnf_filename("BvS", test_size)
            # generate_icnf(bubble, selection, icnf_filename)
            # cnf_filename = generate_cnf_filename("BvS", test_size)
            # generate_cnf(bubble, selection, cnf_filename)

            # icnf_filename = generate_icnf_filename("PvS", test_size)
            # generate_icnf(pancake, selection, icnf_filename)
            # cnf_filename = generate_cnf_filename("PvS", test_size)
            # generate_cnf(pancake, selection, cnf_filename)

            cnf_filename = generate_cnf_filename("SvB", test_size)
            generate_cnf(selection, bubble, cnf_filename)

            cnf_filename = generate_cnf_filename("BvP", test_size)
            generate_cnf(bubble, pancake, cnf_filename)

            cnf_filename = generate_cnf_filename("PvS", test_size)
            generate_cnf(pancake, selection, cnf_filename)


if __name__ == "__main__":
    main()
