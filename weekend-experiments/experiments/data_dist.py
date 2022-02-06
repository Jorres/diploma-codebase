import sys
import os
from tqdm import tqdm
import json
import time
import copy
import random
import concurrent.futures

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


def calculate_pair_compatibility(solver, l, r, pool):
    results = ""
    result_runtimes = list()
    for bit_i in [-1, 1]:
        for bit_j in [-1, 1]:
            var_i = bit_i * pool.v_to_id(l)
            var_j = bit_j * pool.v_to_id(r)
            t1 = time.time()
            res, solution = solver.solve(assumptions=[var_i, var_j])
            if res:
                results += "1"
            else:
                results += "0"
            t2 = time.time()
            result_runtimes.append(t2 - t1)
    return results, result_runtimes

def take_some_from(g1, g2, shared_cnf, pool, data):
    to_be_taken_len = int(len(g1.node_names) / 50)
    to_be_taken = copy.deepcopy(g1.node_names)
    random.shuffle(to_be_taken)
    to_be_taken = to_be_taken[:to_be_taken_len]

    for lname in tqdm(to_be_taken):
        for rname in g2.node_names:
            solver = Solver()
            solver.add_clauses(shared_cnf)
            results, result_runtimes = calculate_pair_compatibility(
                solver, lname, rname, pool
            )
            dist = g1.node_to_depth[lname] + g2.node_to_depth[rname]
            data.append((sum(result_runtimes), results, result_runtimes, dist))

def get_data_from_double_schema(left_file, right_file):
    g1 = Graph(left_file, "L")
    g2 = Graph(right_file, "R")
    g1.remove_identical()
    g2.remove_identical()
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)
    shared_cnf = generate_miter_without_xor(shared_cnf, pool, g1, g2)

    data = list()

    take_some_from(g1, g2, shared_cnf, pool, data)
    take_some_from(g2, g1, shared_cnf, pool, data)

    return data

def single_task(lname, rname, data, shared_cnf, pool):
    solver = Solver()
    solver.add_clauses(shared_cnf)

    results, result_runtimes = calculate_pair_compatibility(
        solver, lname, rname, pool
    )

    dist = dist_from_i[rname]
    data.append((sum(result_runtimes), results, result_runtimes, dist))


def get_data_from_single_schema(file):
    g = Graph(file, "L")
    g.remove_identical()

    pool = TPoolHolder()
    shared_cnf = make_formula_from_my_graph(g, pool)

    pool_size = 6
    datas = [list() for _ in range(pool_size)]
    shared_cnfs = [copy.deepcopy(shared_cnf) for _ in range(pool_size)]
    threadpool = concurrent.futures.ThreadPoolExecutor(6)

    n = len(g.node_names)
    for i in tqdm(range(n)):
        lname = g.node_names[i]
        dist_from_i = g.calculate_dists_from(lname)
        for j in range(i, n):
            rname = g.node_names[j]
            future = threadpool.submit(lname, rname, data, shared_cnf, poolsingle_task, ())
            # solver = Solver()
            # solver.add_clauses(shared_cnf)

            # results, result_runtimes = calculate_pair_compatibility(
            #     solver, lname, rname, pool
            # )

            # dist = dist_from_i[rname]
            # data.append((sum(result_runtimes), results, result_runtimes, dist))

    return data


def dump_data_into_file(data, filename):
    with open(f"./experiments/data_dist/{filename}", "w") as f:
        for elem in data:
            total, status, partials, dist = elem
            f.write(f"{total:.7f} {status} {dist}")
            for partial_time in partials:
                f.write(f" {partial_time:.5f}")
            f.write("\n")


def collect_data_on_single():
    # specials = ["a51_stream114", "bivium-no-init_stream200", "md4_48"]
    specials = ["bivium-no-init_stream200"]
    sorts_shortnames = ["7_4"]
    sorts = [f"BubbleSort_{x}" for x in sorts_shortnames] + [
        f"PancakeSort_{x}" for x in sorts_shortnames
    ]

    for experiment in sorts + specials:
        schema_file = f"./hard-instances/{experiment}.aag"
        data = get_data_from_single_schema(schema_file)
        dump_data_into_file(data, f"{experiment}.txt")


def collect_data_on_combined():
    experiments = ["4_3"]

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
