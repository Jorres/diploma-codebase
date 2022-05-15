import os
import subprocess
import time
import itertools
import random
import sys
import pysat
from joblib import Parallel, delayed
from pysat.solvers import Maplesat as PysatSolver
from pycryptosat import Solver

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
from formula_builder import (
    generate_miter_scheme,
)
import utils as U
import domain_preprocessing as DP

SMALL = 1
TIMEOUT = 2
SUCCESS = 3
GANAK_TIMEOUT = 4
INCOMPAT = 5
GANAK_FAILURE = 6

def main():
    experiments = ["5_4", "6_4"]
    for sorts in [
        ("Bubble", "Pancake"),
        ("Selection", "Bubble"),
        ("Pancake", "Selection"),
    ]:
        for test_shortname in experiments:
            left_sort, right_sort = sorts
            left_schema_name = f"{left_sort}Sort_{test_shortname}"
            left_schema_file = f"./hard-instances/fraag/{left_schema_name}.aag"
            right_schema_name = f"{right_sort}Sort_{test_shortname}"
            right_schema_file = f"./hard-instances/fraag/{right_schema_name}.aag"

            g = Graph(left_schema_file, "L")
            gr = Graph(right_schema_file, "R")

            buckets_left = DP.find_unbalanced_gates(g)
            buckets_right = DP.find_unbalanced_gates(gr)

            best_domains_left, shift = DP.calculate_domain_saturations(
                g, buckets_left[:3], tag="L", start_from=1
            )

            best_domains_left = sorted(
                [
                    (satur, bucket, domain)
                    for (satur, bucket, domain, _) in best_domains_left
                ]
            )

            best_domains_right, shift_right = DP.calculate_domain_saturations(
                g, buckets_right[:3], tag="R", start_from=shift + 1
            )

            best_domains_right = sorted(
                [
                    (satur, bucket, domain)
                    for (satur, bucket, domain, _) in best_domains_right
                ]
            )

            input_size = int(test_shortname[0]) * int(test_shortname[2])

            comment_line = "c ind"
            for i in range(1, input_size):
                comment_line += f" {i}"

            for bucket_id in range(0, 1):
                metainfo = dict()
                metainfo["left_schema"] = left_schema_name
                metainfo["right_schema"] = right_schema_name
                metainfo["bucket_id"] = bucket_id
                _, bucket_l, domain_l = best_domains_left[bucket_id]
                _, bucket_r, domain_r = best_domains_right[bucket_id]

                domain = list(itertools.product(domain_l, domain_r))

                shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g, gr)
                cnf = generate_miter_scheme(shared_cnf, pool, g, gr)

                random.shuffle(domain)

                metainfo["total_tasks"] = len(list(domain))

                print(len(domain))

                with Parallel(n_jobs=-2, verbose=2) as parallel:
                    res = parallel(
                        delayed(do_measure)(
                            g,
                            gr,
                            bucket_l,
                            bucket_r,
                            pool,
                            cnf,
                            bitvector_l,
                            bitvector_r,
                            comment_line,
                            i,
                            left_schema_name,
                            right_schema_name,
                        )
                        for i, (bitvector_l, bitvector_r) in enumerate(domain)
                    )

                    small, timeout, success, ganak_timeout, incompat, ganak_failure = map(
                        len,
                        [
                            list(filter(lambda p: p == verdict, res))
                            for verdict in [SMALL, TIMEOUT, SUCCESS, GANAK_TIMEOUT, INCOMPAT, GANAK_FAILURE]
                        ],
                    )

                    stat_file = "./experiments/ganak_data/results/stats_small.txt"
                    with open(stat_file, "a") as f:
                        f.writelines([f"{get_code_name(left_schema_name, right_schema_name, test_shortname, bucket_id)} {small=} {timeout=} {success=} {ganak_timeout=} {incompat=} {ganak_failure=}\n"])

                    merged_file = f"./experiments/ganak_data/results/{get_code_name(left_schema_name, right_schema_name, test_shortname, bucket_id)}"

                    for dirpath, dnames, fnames in os.walk("./"):
                        for fname in fnames:
                            if fname.startswith("tmp_"):
                                with open(fname, "r") as f:
                                    pid_lines = f.readlines()
                                    with open(merged_file, "a") as f:
                                        f.writelines(pid_lines)
                                    os.system(f"rm {fname}")


def do_measure(
    g,
    gr,
    bucket_l,
    bucket_r,
    pool,
    cnf,
    bitvector_l,
    bitvector_r,
    comment_line,
    i,
    left_schema_name,
    right_schema_name,
):
    no_miter, pool_2 = U.prepare_shared_cnf_from_two_graphs(g, gr)
    assumptions = []

    for gate_id, gate_name in enumerate(bucket_l):
        modifier = U.get_bit_from_domain(bitvector_l, gate_id)
        lit = modifier * pool.v_to_id(gate_name)
        assumptions.append(lit)
        no_miter.append([lit])
    for gate_id, gate_name in enumerate(bucket_r):
        modifier = U.get_bit_from_domain(bitvector_r, gate_id)
        lit = modifier * pool.v_to_id(gate_name)
        assumptions.append(lit)
        no_miter.append([lit])

    solver = Solver(confl_limit=100000)
    solver.add_clauses(cnf + [[x] for x in assumptions])
    t1 = time.time()
    solver_res, solution = solver.solve()
    t2 = time.time()

    if solver_res is None:
        return TIMEOUT
    if t2 - t1 > 1:
        return TIMEOUT

    assert not solver_res

    target_file = (
        f"./experiments/ganak_data/{left_schema_name[0]}v{right_schema_name[0]}_{i}"
    )

    pysat.formula.CNF(from_clauses=no_miter).to_file(target_file)
    os.system(f'echo "{comment_line}" >> {target_file}')

    try:
        res = subprocess.check_output(
            [
                "../ganak/bin/ganak",
                "-t",
                "1000",
                "-delta",
                "0.03",
                target_file,
            ],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return GANAK_FAILURE

    os.system(f"rm {target_file}")

    if "TIMEOUT" in res:
        return GANAK_TIMEOUT

    tmp1 = str(res).split("\n")[-5:][0]
    if " 0 " in tmp1:
        return INCOMPAT

    tmp2 = str(res).split("\n")[-5:][3]
    single_elem = f"{tmp1} {tmp2} {t2 - t1}\n"

    pid = os.getpid()

    with open(f"./tmp_{pid}", "a") as f:
        f.writelines(single_elem)
    return SUCCESS


def get_code_name(left, right, test_shortname, bucket_id):
    return f"{left[0]}v{right[0]}_{test_shortname}_{bucket_id}_small"


if __name__ == "__main__":
    main()
