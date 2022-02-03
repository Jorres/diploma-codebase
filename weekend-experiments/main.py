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


# Calculates a cartesian product, encodes a miter schema,
# then iterates over the product to make sure there is UNSAT on every possible
# combination of domain values.
def check_for_equivalence(
    g1,
    g2,
    domains_info_left,
    domains_info_right,
    metainfo,
    tasks_dump_file,
    cnf_file,
):
    shared_domain_info = sorted(domains_info_left + domains_info_right)

    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)

    one_saturated_domains = 0
    one_defined = 0

    for saturation, bucket, domain, tag in shared_domain_info:
        if len(domain) == 1:
            one_saturated_domains += 1
            for gate_id, gate_name in enumerate(bucket):
                bitvector = domain[0]
                modifier = U.get_bit_from_domain(bitvector, gate_id)
                shared_cnf.append([modifier * pool.v_to_id(gate_name)])
                one_defined += 1
        else:
            break

    metainfo["one_defined"] = one_defined
    metainfo["one_saturated_domains"] = one_saturated_domains
    shared_domain_info = shared_domain_info[one_saturated_domains:]

    cartesian_size = 1
    best_domains = list()
    total_vars_in_decomp = 0
    for (saturation, bucket, domain, tag) in shared_domain_info:
        if cartesian_size * len(domain) > H.MAX_CARTESIAN_PRODUCT_SIZE:
            break
        best_domains.append(domain)
        total_vars_in_decomp += len(bucket)
        cartesian_size *= len(domain)

    metainfo["actual_cartesian_size"] = cartesian_size
    metainfo["total_vars_in_decomp"] = total_vars_in_decomp

    # construct the cartesian product of selected domains:
    combinations = itertools.product(*best_domains)

    print("Total size of cartesian product of the domains:", cartesian_size)
    print(
        "Distribution: {}, total domains: {}".format(
            list(map(lambda x: len(x), best_domains)), len(best_domains)
        )
    )
    metainfo["distribution"] = list(map(lambda x: len(x), best_domains))

    final_cnf = FB.generate_miter_scheme(shared_cnf, pool, g1, g2)

    final_cnf_as_formula = pysat.formula.CNF(from_clauses=final_cnf)
    final_cnf_as_formula.to_file(cnf_file)

    runtimes = []
    equivalent = True
    tasks = list()

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
            saturation, bucket, domain, tag = shared_domain_info[domain_id]

            assert bitvector in domain
            for gate_id, gate_name in enumerate(bucket):
                modifier = U.get_bit_from_domain(bitvector, gate_id)
                assumptions.append(modifier * pool.v_to_id(gate_name))

        t1 = time.time()
        sat_on_miter, solution = solver.solve(assumptions=assumptions)
        t2 = time.time()
        runtimes.append(t2 - t1)
        tasks.append((t2 - t1, comb_id, assumptions))

        if sat_on_miter:
            equivalent = False
            break

    runtimes = sorted(runtimes)
    metainfo["some_biggest_runtimes"] = []

    for i in range(1, 4):
        if len(runtimes) >= i:
            metainfo["some_biggest_runtimes"].append(runtimes[-i])

    with open(tasks_dump_file, "w+") as f:
        pretty_tasks = dict()
        pretty_tasks["tasks"] = tasks
        f.write(json.dumps(pretty_tasks, indent=4))

    return equivalent


def post_sampling_calculations(
    g1,
    g2,
    test_path_left,
    test_path_right,
    metainfo,
    buckets_left,
    buckets_right,
    t_start,
    tasks_dump_file,
    cnf_file,
):
    best_domains_left, shift = DP.calculate_domain_saturations(
        g1, buckets_left, tag="L", start_from=1
    )
    best_domains_right, _ = DP.calculate_domain_saturations(
        g2, buckets_right, tag="R", start_from=shift + 1
    )
    result = check_for_equivalence(
        g1,
        g2,
        best_domains_left,
        best_domains_right,
        metainfo,
        tasks_dump_file,
        cnf_file,
    )
    t_finish = time.time()

    time_elapsed = str(t_finish - t_start)
    metainfo["left_schema"] = test_path_left
    metainfo["right_schema"] = test_path_right
    metainfo["time"] = time_elapsed
    metainfo["outcome"] = result
    return result


def domain_equivalence_check(
    test_path_left,
    test_path_right,
    metainfo_file,
    cnf_file,
    tasks_dump_file,
):
    g1 = G.Graph(test_path_left, "L")
    g2 = G.Graph(test_path_right, "R")

    g1.remove_identical()
    g2.remove_identical()

    t_start = time.time()
    metainfo = dict()

    print("Schemas initialized, looking for unbalanced nodes in the left schema")
    buckets_left = DP.find_unbalanced_gates(g1)
    print("Looking for unbalanced nodes in the right schema")
    buckets_right = DP.find_unbalanced_gates(g2)
    print("Unbalanced nodes found, proceeding to building domains")

    metainfo["type"] = "domain"

    result = post_sampling_calculations(
        g1,
        g2,
        test_path_left,
        test_path_right,
        metainfo,
        buckets_left,
        buckets_right,
        t_start,
        tasks_dump_file,
        cnf_file,
    )

    U.print_to_file(metainfo_file, json.dumps(metainfo, indent=4))

    return result


def naive_equivalence_check(test_path_left, test_path_right, metainfo_file, cnf_file):
    g1 = G.Graph(test_path_left, "L")
    g2 = G.Graph(test_path_right, "R")
    g1.remove_identical()
    g2.remove_identical()

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


def topsort_order_equivalence_check(test_path_left, test_path_right, metainfo_file):
    print(test_path_left, test_path_right)
    g1 = G.Graph(test_path_left, "L")
    g2 = G.Graph(test_path_right, "R")

    g1.remove_identical()
    g2.remove_identical()

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


if __name__ == "__main__":
    experiments = ["4_3", "6_4", "7_4", "8_4"]

    for test_shortname in experiments:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        cnf_file = f"./hard-instances/cnf/{test_shortname}.cnf"
        cnf_naive_file = f"./hard-instances/cnf/{test_shortname}_naive.cnf"

        metainfo_file = f"./hard-instances/metainfo/{test_shortname}.txt"
        tasks_dump_file = f"./hard-instances/assumptions/{test_shortname}.txt"

        # topsort_order_equivalence_check(left_schema_file, right_schema_file, metainfo_file)

        # naive_equivalence_check(
        #     left_schema_file, right_schema_file, metainfo_file, cnf_naive_file
        # )

        domain_equivalence_check(
            left_schema_file,
            right_schema_file,
            metainfo_file,
            cnf_file,
            tasks_dump_file,
        )
