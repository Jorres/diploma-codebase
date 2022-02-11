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


def extract_domains_with_saturation_one_into_cnf(cnf, pool, domains, metainfo):
    one_saturated_domains = 0
    one_defined = 0
    for saturation, bucket, domain, tag in domains:
        if len(domain) == 1:
            one_saturated_domains += 1
            for gate_id, gate_name in enumerate(bucket):
                bitvector = domain[0]
                modifier = U.get_bit_from_domain(bitvector, gate_id)
                cnf.append([modifier * pool.v_to_id(gate_name)])
                one_defined += 1
        else:
            break
    metainfo["one_defined"] = one_defined
    metainfo["one_saturated_domains"] = one_saturated_domains
    return domains[one_saturated_domains:]


def take_domains_until_threshold(domains, metainfo, max_product_size=H.MAX_CARTESIAN_PRODUCT_SIZE):
    cartesian_size = 1
    best_domains = list()
    total_vars_in_decomp = 0
    for saturation, bucket, domain, tag in domains:
        if cartesian_size * len(domain) > max_product_size:
            break
        best_domains.append((domain, bucket))
        total_vars_in_decomp += len(bucket)
        cartesian_size *= len(domain)

    metainfo["actual_cartesian_size"] = cartesian_size
    metainfo["total_vars_in_decomp"] = total_vars_in_decomp
    return best_domains, cartesian_size


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
    shared_domain_info = sorted(domains_info_left + domains_info_right)
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)

    shared_domain_info = extract_domains_with_saturation_one_into_cnf(
        shared_cnf, pool, shared_domain_info, metainfo)

    best_domains, cartesian_size = take_domains_until_threshold(shared_domain_info, metainfo)

    # strip bucket info, not needed for cartesian product calculation
    best_domains = [x[0] for x in best_domains]

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
            saturation, bucket, domain, tag = shared_domain_info[domain_id]
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
    metainfo["some_biggest_runtimes"] = []

    for i in range(1, 4):
        if len(runtimes) >= i:
            metainfo["some_biggest_runtimes"].append(runtimes[-i])

    return equivalent


def tree_based_equivalence(
    g1,
    g2,
    domains_info_left,
    domains_info_right,
    metainfo,
):
    shared_domain_info = sorted(domains_info_left + domains_info_right)
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)

    shared_domain_info = extract_domains_with_saturation_one_into_cnf(
        shared_cnf, pool, shared_domain_info, metainfo)

    final_cnf = FB.generate_miter_scheme(shared_cnf, pool, g1, g2)

    best_domains, cartesian_size = take_domains_until_threshold(
        shared_domain_info, metainfo, H.MAX_CARTESIAN_PRODUCT_SIZE * H.MAX_CARTESIAN_PRODUCT_SIZE)

    # layer of the calculation = baskets
    # 2 baskets can be merged into 1 basket
    # basket stores values in form of:
    # list(int)
    # [499238, 2384238]

    # In addition, a basket stores the gate names for the bitvectors
    # it holds. Once.
    # ['a100' .. 'i123'], ['a437' .. 'i900']

    baskets = TD.prepare_first_layer_of_baskets(best_domains)
    assert len(baskets) == len(best_domains)

    for basket in baskets:
        basket.debug_print()

    skipped = 0
    layer = 0
    with PysatSolver(bootstrap_with=final_cnf) as solver:
        while len(baskets) > 1:
            print(f"{layer=}")
            layer += 1
            new_baskets = list()
            i = 0
            while i < len(baskets):
                if i + 1 >= len(baskets):
                    new_baskets.append(baskets[i])
                    i += 1
                else:
                    new_basket, skipped_this_time = baskets[i].merge(baskets[i + 1], solver, pool)
                    print(f"{skipped_this_time=}")
                    new_baskets.append(new_basket)
                    skipped += skipped_this_time
                    i += 2
            assert len(baskets) > len(new_baskets)
            baskets = new_baskets

            print('----------')

            for basket in baskets:
                basket.debug_print()

        final_basket = baskets[0]

        for bitvector in tqdm(final_basket.bitvectors, desc="Last bucket"):
            assumptions = TD.bitvector_to_assumptions(
                bitvector, final_basket.gate_names_for_bitvectors, pool)

            res = solver.solve(assumptions=assumptions)
            if res:
                return False

    metainfo['skipped'] = skipped
    return True


def post_sampling_calculations(
    g1,
    g2,
    test_path_left,
    test_path_right,
    metainfo,
    buckets_left,
    buckets_right,
    mode
):
    best_domains_left, shift = DP.calculate_domain_saturations(
        g1, buckets_left, tag="L", start_from=1
    )
    best_domains_right, _ = DP.calculate_domain_saturations(
        g2, buckets_right, tag="R", start_from=shift + 1
    )

    if mode == "tree-based":
        result = tree_based_equivalence(
            g1,
            g2,
            best_domains_left,
            best_domains_right,
            metainfo,
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
    test_path_left,
    test_path_right,
    metainfo_file,
    mode
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

    metainfo["type"] = mode

    result = post_sampling_calculations(
        g1,
        g2,
        test_path_left,
        test_path_right,
        metainfo,
        buckets_left,
        buckets_right,
        mode
    )

    t_finish = time.time()
    time_elapsed = str(t_finish - t_start)
    metainfo["time"] = time_elapsed

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


def check_open_xors_equivalence(test_path_left, test_path_right, metainfo_file):
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


def main():
    experiments = ["7_4"]
    for test_shortname in experiments:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        metainfo_file = f"./hard-instances/metainfo/{test_shortname}.txt"

        # domain_equivalence_check(
        #     left_schema_file,
        #     right_schema_file,
        #     metainfo_file,
        #     "tree-based",
        # )

        naive_equivalence_check(left_schema_file, right_schema_file, metainfo_file, None)

        domain_equivalence_check(
            left_schema_file,
            right_schema_file,
            metainfo_file,
            "all-domains-at-once"
        )


if __name__ == "__main__":
    main()
