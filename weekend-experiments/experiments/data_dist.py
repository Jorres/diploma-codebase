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
    PicklablePool
)


def calculate_pair_compatibility(solver, l, r, pool):
    results = ""
    result_runtimes = list()
    for bit_i in [-1, 1]:
        for bit_j in [-1, 1]:
            var_i = bit_i * pool.v_to_id(l)
            var_j = bit_j * pool.v_to_id(r)
            t1 = time.time()
            res = solver.solve(assumptions=[var_i, var_j])
            if res:
                results += "1"
            else:
                results += "0"
            t2 = time.time()
            result_runtimes.append(t2 - t1)
    return results, result_runtimes


def single_task_for_double(lname, right_node_names, shared_cnf, pool, left_depth, right_name_to_depth):
    big_res = list()
    for rname in right_node_names:
        # with PysatSolver(bootstrap_with=shared_cnf) as solver:
        solver = Solver()
        solver.add_clauses(shared_cnf)
        results, result_runtimes = calculate_pair_compatibility(
            solver, lname, rname, pool
        )
        dist = left_depth + right_name_to_depth[rname]
        big_res.append((sum(result_runtimes), results, result_runtimes, dist))
    return big_res


def take_some_from(g1, g2, shared_cnf, pool, futures, threadpool):
    to_be_taken_len = min(len(g1.node_names), 100)
    to_be_taken = copy.deepcopy(g1.node_names)
    random.shuffle(to_be_taken)
    to_be_taken = to_be_taken[:to_be_taken_len]

    for lname in tqdm(to_be_taken, desc="Pushing tasks to executor"):
        future = threadpool.submit(
            single_task_for_double, lname, g2.node_names, shared_cnf, pool, g1.node_to_depth[lname], g2.node_to_depth)
        futures.append(future)


def get_data_from_double_schema(left_file, right_file):
    g1 = Graph(left_file, "L")
    g2 = Graph(right_file, "R")
    g1.remove_identical()
    g2.remove_identical()
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)
    shared_cnf = generate_miter_without_xor(shared_cnf, pool, g1, g2)

    threadpool = concurrent.futures.ProcessPoolExecutor(max_workers=6)

    futures = list()

    take_some_from(g1, g2, shared_cnf, pool, futures, threadpool)
    take_some_from(g2, g1, shared_cnf, pool, futures, threadpool)

    data = list()
    for future in tqdm(futures):
        for elem in future.result():
            data.append(elem)
    return data


def single_task(lname, right_nodenames, shared_cnf, pool, dist_from_i):
    big_res = list()
    lname_met = False
    for rname in right_nodenames:
        if rname == lname:
            lname_met = True
        if not lname_met:
            continue

        with PysatSolver(bootstrap_with=shared_cnf) as solver:
            results, result_runtimes = calculate_pair_compatibility(
                solver, lname, rname, pool
            )

            dist = dist_from_i[rname]
            big_res.append((sum(result_runtimes), results, result_runtimes, dist))
    return big_res


def get_data_from_single_schema(file, experiment):
    g = Graph(file, "L")
    g.remove_identical()

    pool = PicklablePool()
    shared_cnf = make_formula_from_my_graph(g, pool)

    chunks = [g.node_names[x:x+50] for x in range(0, len(g.node_names), 50)]

    for chunk in tqdm(chunks, desc="Chunks"):
        with concurrent.futures.ProcessPoolExecutor(max_workers=7) as threadpool:
            data = list()
            futures = list()

            for lname in tqdm(chunk, desc="Pushing tasks", leave=False):
                dist_from_i = g.calculate_dists_from(lname)

                future = threadpool.submit(
                    single_task, lname, g.node_names, shared_cnf, pool, dist_from_i)
                futures.append(future)

            for future in tqdm(futures, desc="Processing futures", leave=False):
                data += future.result()

            dump_data_into_file(data, f"{experiment}.txt")


def dump_data_into_file(data, filename):
    with open(f"./experiments/data_dist/{filename}", "a") as f:
        for elem in data:
            total, status, partials, dist = elem
            f.write(f"{total:.7f} {status} {dist}")
            for partial_time in partials:
                f.write(f" {partial_time:.5f}")
            f.write("\n")


def collect_data_on_single():
    # specials = ["a51_stream114", "bivium-no-init_stream200", "md4_48"]
    # specials = ["bivium-no-init_stream200"]
    # sorts_shortnames = ["7_4"]
    sorts_shortnames = ["7_4"]
    sorts = [ f"PancakeSort_{x}" for x in sorts_shortnames ]

    for experiment in sorts:
        schema_file = f"./hard-instances/{experiment}.aag"
        data = get_data_from_single_schema(schema_file, experiment)
        # dump_data_into_file(data, f"{experiment}.txt")


def collect_data_on_combined():
    # experiments = ["6_4", "7_4"]

    for test_shortname in experiments:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        data = get_data_from_double_schema(left_schema_file, right_schema_file)
        dump_data_into_file(data, f"BvP_{test_shortname}.txt")


if __name__ == "__main__":
    collect_data_on_single()
    # collect_data_on_combined()
