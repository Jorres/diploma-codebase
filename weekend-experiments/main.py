import time
import random
import itertools
import json
import pysat
import os
import sys

from collections import defaultdict
from tqdm import tqdm

from pysat.solvers import Maplesat as PysatSolver
from pycryptosat import Solver

import formula_builder as FB
import graph as G
import utils as U

import eq_checkers as EQ

import hyperparameters as H
import domain_preprocessing as DP
import tree_decomposition as TD

COMPLEX_CUBES_FILE = ""


def take_domains_from_one_side(domains, n):
    cartesian_size = 1
    vars_taken = 0
    best_domains = list()
    for saturation, bucket, domain, tag in domains[:n]:
        best_domains.append((domain, bucket, tag))
        vars_taken += len(bucket)
        cartesian_size *= len(domain)
    return best_domains, vars_taken, cartesian_size


def take_domains_until_threshold(domains_left, domains_right, metainfo):
    best_left, vars_left, cartesian_size_left = take_domains_from_one_side(
        domains_left, H.BUCKETS_FROM_LEFT
    )
    best_right, vars_right, cartesian_size_right = take_domains_from_one_side(
        domains_right, H.BUCKETS_FROM_RIGHT
    )

    total_cartesian_size = cartesian_size_left * cartesian_size_right
    metainfo["actual_cartesian_size"] = total_cartesian_size
    metainfo["total_vars_in_decomp"] = vars_left + vars_right
    return best_left + best_right, total_cartesian_size


# Calculates a cartesian product, encodes a miter schema,
# then iterates over the product to make sure there is UNSAT on every possible
# combination of domain values.
def all_domains_at_once_equivalence(
    g1,
    g2,
    domains_info_left,
    domains_info_right,
    metainfo,
):
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)

    shared_domain_info, cartesian_size = take_domains_until_threshold(
        domains_info_left, domains_info_right, metainfo
    )

    # strip bucket info, not needed for cartesian product calculation
    shared_domains_only = [x[0] for x in shared_domain_info]

    # construct the cartesian product of selected domains:
    combinations = itertools.product(*shared_domains_only)

    print("Total size of cartesian product of the domains:", cartesian_size)
    print(
        "Distribution: {}, total domains: {}".format(
            list(map(lambda x: len(x), shared_domains_only)), len(shared_domains_only)
        )
    )

    metainfo["distribution"] = list(map(lambda x: len(x), shared_domains_only))

    final_cnf = FB.generate_miter_scheme(shared_cnf, pool, g1, g2)

    runtimes = []
    equivalent = True

    solver = Solver()
    solver.add_clauses(final_cnf)

    for comb_id, combination in enumerate(
        tqdm(
            combinations,
            desc="Processing cartesian combination",
            total=cartesian_size,
        )
    ):
        # combination = [domain]
        assumptions = list()

        for domain_id, bitvector in enumerate(combination):
            bucket, domain, tag = shared_domain_info[domain_id]
            print(bucket, domain, tag)
            assert bitvector in domain
            for gate_id, gate_name in enumerate(bucket):
                modifier = U.get_bit_from_domain(bitvector, gate_id)
                assumptions.append(modifier * pool.v_to_id(gate_name))

        t1 = time.time()
        sat_on_miter, solution = solver.solve(assumptions=assumptions)
        t2 = time.time()
        runtimes.append(t2 - t1)


        if sat_on_miter:
            equivalent = False
            break

    runtimes = sorted(runtimes)
    total_solving_runtime = sum(runtimes)
    metainfo["solver_runtime_only"] = total_solving_runtime
    metainfo["some_biggest_runtimes"] = []

    for i in range(1, 4):
        if len(runtimes) >= i:
            metainfo["some_biggest_runtimes"].append(runtimes[-i])

    return equivalent


def get_one_side_domains_and_basket(g, shared_best_domains, pool):
    best_domains_side = list(
        filter(lambda domain: domain[2] == g.tag, shared_best_domains)
    )

    baskets = TD.prepare_first_layer_of_baskets(best_domains_side)

    with PysatSolver(bootstrap_with=FB.make_formula_from_my_graph(g, pool)) as solver:
        final_basket, skipped_side = TD.merge_baskets(baskets, solver, pool)

    return best_domains_side, final_basket


def get_two_final_baskets(g1, g2, domains_info_left, domains_info_right, metainfo):
    best_domains, cartesian_size = take_domains_until_threshold(
        domains_info_left, domains_info_right, metainfo
    )

    single_schemas_pool = FB.TPoolHolder()
    best_domains_left, final_basket_left = get_one_side_domains_and_basket(
        g1,
        best_domains,
        single_schemas_pool,
    )

    best_domains_right, final_basket_right = get_one_side_domains_and_basket(
        g2,
        best_domains,
        single_schemas_pool,
    )
    return final_basket_left, final_basket_right


def generate_inccnf(g1, g2, domains_info_left, domains_info_right, metainfo, file_name):
    basket_left, basket_right = get_two_final_baskets(
        g1, g2, domains_info_left, domains_info_right, metainfo
    )
    TD.generate_inccnf(
        g1,
        g2,
        basket_left,
        basket_right,
        metainfo,
        file_name,
        domains_info_left,
        domains_info_right,
    )


def tree_based_equivalence(
    g1, g2, domains_info_left, domains_info_right, metainfo, complex_cubes_file
):
    final_basket_left, final_basket_right = get_two_final_baskets(
        g1, g2, domains_info_left, domains_info_right, metainfo
    )

    TD.filter_complex_cubes(
        g1, g2, final_basket_left, final_basket_right, complex_cubes_file
    )

    return True

    return TD.iterate_over_two_megabackets(
        g1, g2, final_basket_left, final_basket_right
    )


def post_sampling_calculations(
    g1,
    g2,
    test_path_left,
    test_path_right,
    metainfo,
    buckets_left,
    buckets_right,
    mode,
    complex_cubes_file,
):

    best_domains_left, shift = DP.calculate_domain_saturations(
        g1, buckets_left, tag="L", start_from=1
    )
    best_domains_right, _ = DP.calculate_domain_saturations(
        g2, buckets_right, tag="R", start_from=shift + 1
    )

    if mode == "tree-based":
        result = tree_based_equivalence(
            g1, g2, best_domains_left, best_domains_right, metainfo, complex_cubes_file
        )
    elif mode == "all-domains-at-once":
        result = all_domains_at_once_equivalence(
            g1,
            g2,
            best_domains_left,
            best_domains_right,
            metainfo,
        )
    else:
        assert False

    metainfo["left_schema"] = test_path_left
    metainfo["right_schema"] = test_path_right
    metainfo["outcome"] = result
    return result


def domain_equivalence_check(
    test_path_left, test_path_right, metainfo_file, mode, complex_cubes_file=None
):
    g1 = G.Graph(test_path_left, "L")
    g2 = G.Graph(test_path_right, "R")

    t_start = time.time()
    metainfo = dict()

    print("Schemas initialized, looking for unbalanced nodes in the left schema")
    buckets_left = DP.find_unbalanced_gates(g1)
    print("Looking for unbalanced nodes in the right schema")
    buckets_right = DP.find_unbalanced_gates(g2)
    print("Unbalanced nodes found, proceeding to building domains")

    metainfo["type"] = mode

    result = post_sampling_calculations(
        g1,
        g2,
        test_path_left,
        test_path_right,
        metainfo,
        buckets_left,
        buckets_right,
        mode,
        complex_cubes_file,
    )

    t_finish = time.time()
    time_elapsed = str(t_finish - t_start)
    metainfo["time"] = time_elapsed

    U.print_to_file(metainfo_file, json.dumps(metainfo, indent=4))

    return result


def naive_equivalence_check(test_path_left, test_path_right, metainfo_file, cnf_file):
    g1 = G.Graph(test_path_left, "L")
    g2 = G.Graph(test_path_right, "R")

    metainfo = dict()
    metainfo["left_schema"] = test_path_left
    metainfo["right_schema"] = test_path_right
    metainfo["type"] = "naive"
    t1 = time.time()
    result = EQ.validate_naively(g1, g2, metainfo, cnf_file)
    t2 = time.time()
    metainfo["time"] = str(t2 - t1)
    metainfo["outcome"] = result
    U.print_to_file(metainfo_file, json.dumps(metainfo, indent=4))


def check_open_xors_equivalence(test_path_left, test_path_right, metainfo_file):
    print(test_path_left, test_path_right)
    g1 = G.Graph(test_path_left, "L")
    g2 = G.Graph(test_path_right, "R")

    metainfo = dict()
    metainfo["left_schema"] = test_path_left
    metainfo["right_schema"] = test_path_right
    metainfo["type"] = "open_xors"

    t1 = time.time()
    result = EQ.validate_with_open_xors(g1, g2, metainfo)
    t2 = time.time()

    metainfo["total_time"] = str(t2 - t1)
    metainfo["outcome"] = result
    U.print_to_file(metainfo_file, json.dumps(metainfo, indent=4))


def main():
    experiments = ["6_4", "7_4", "8_4"]
    for left_sort, right_sort in [
        ("Selection", "Bubble"),
        # ("Bubble", "Pancake"),
        # ("Pancake", "Selection"),
    ]:
        for test_shortname in experiments:
            left_schema_name = f"{left_sort}Sort_{test_shortname}"
            right_schema_name = f"{right_sort}Sort_{test_shortname}"

            left_schema_file = f"./hard-instances/fraag/{left_schema_name}.aag"
            right_schema_file = f"./hard-instances/fraag/{right_schema_name}.aag"

            test_name = f"{left_sort[0]}v{right_sort[0]}_{test_shortname}.txt"

            metainfo_file = f"./hard-instances/metainfo/{test_name}"
            complex_cubes_file = f"./icnf_data/complex_cubes/{test_name}"

            domain_equivalence_check(
                left_schema_file,
                right_schema_file,
                metainfo_file,
                "all-domains-at-once",
                complex_cubes_file,
            )

            # naive_equivalence_check(
            #     left_schema_file, right_schema_file, metainfo_file, None
            # )

            # domain_equivalence_check(
            #     left_schema_file, right_schema_file, metainfo_file, "all-domains-at-once"
            # )

if __name__ == "__main__":
    main()
