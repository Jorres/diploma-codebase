import os
import pysat
import subprocess
import sys
import math
import time

from joblib import Parallel, delayed
from pysat.solvers import Maplesat as PysatSolver
from os.path import exists
from pycryptosat import Solver

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from formula_builder import make_united_miter_from_two_graphs
from graph import Graph

SUCCESS = 3
GANAK_TIMEOUT = 4
GANAK_FAILURE = 6


def make_xor(formula, xor, left, right):
    formula.append([-1 * xor, -1 * left, -1 * right, ])
    formula.append([-1 * xor, left, right, ])
    formula.append([xor, -1 * left, right, ])
    formula.append([xor, left, -1 * right, ])


def make_and(formula, v, left, right):
    formula.append([v, -1 * left, -1 * right, ])
    formula.append([-1 * v, left, ])
    formula.append([-1 * v, right, ])


def make_maj(formula, m, i, j, k):
    formula.append([-1*i, -1*j, m])
    formula.append([-1*i, -1*k, m])
    formula.append([-1*j, -1*k, m])
    formula.append([i,    j, -m])
    formula.append([i,    k, -m])
    formula.append([j,    k, -m])


def append_layer_to_cnf(_formula, input_vars, kind):
    formula = _formula.copy()
    max_var = -1
    for clause in formula.clauses:
        for lit in clause:
            max_var = max(abs(lit), max_var)
    first_new = -1
    last_new = -1

    # heavily relies on input vars being in [1 ; input_vars]

    if kind == "maj":
        function_size = 3
    elif kind == "and" or kind == "xor":
        function_size = 2
    else:
        print(f"unsupported function type {kind}")
        exit(1)

    for new_var_id in range(0, int(math.floor(input_vars / function_size))):
        max_var += 1
        new_var = max_var

        if function_size == 2:
            left = 2 * new_var_id + 1
            right = 2 * new_var_id + 2
        elif function_size == 3:
            left = 3 * new_var_id + 1
            middle = 3 * new_var_id + 2
            right = 3 * new_var_id + 3

        if kind == "xor":
            make_xor(formula, new_var, left, right)
        elif kind == "and":
            make_and(formula, new_var, left, right)
        elif kind == "maj":
            make_maj(formula, new_var, left, middle, right)

        if first_new == -1:
            first_new = new_var
        last_new = new_var

    if kind == "maj" and input_vars != 24:
        print(input_vars)
        assert int(math.floor(input_vars / 3)) * 3 == input_vars - 1
        last_new += 1
        formula.append([last_new, input_vars])
        formula.append([-1 * last_new, -1 * input_vars])

    return formula, (first_new, last_new)


def get_word(kind):
    if kind == "xor":
        return "pairs"
    elif kind == "and":
        return "pairs"
    elif kind == "maj":
        return "triples"


def measure_solver_time(layer_type):
    source_dir = "./data/miters-cnf"
    dest_dir = "./data/miters-with-layer"
    hist_dir = "./data/hist"

    for dirpath, dnames, fnames in os.walk(source_dir):
        for f in fnames:
            hist_name = f"{hist_dir}/{f[:-8]}-{get_word(layer_type)}-{layer_type}.hist"

            if "8_4" in f or "9_4" in f:
                continue
            if "5_4" in f and layer_type == "maj":
                continue
            if exists(hist_name):
                continue

            formula = pysat.formula.CNF(from_file=f"{source_dir}/{f}")
            n = int(f[4])
            m = int(f[6])

            input_size = n * m

            formula_with_layer, new_vars = append_layer_to_cnf(
                formula, input_size, layer_type)
            formula_with_layer.to_file(f"{dest_dir}/{f[:-4]}_{layer_type}.cnf")

            first_new, last_new = new_vars

            last_new += 1

            total_new = last_new - first_new

            if layer_type == "and" or layer_type == "xor":
                assert total_new == int(input_size / 2)
            else:
                if input_size % 3 == 1:
                    assert total_new == int(math.floor(input_size / 3)) + 1
                else:
                    assert input_size % 3 == 0
                    assert total_new == int(input_size / 3)

            print(f"{f[:-4]}_{layer_type}, total tasks: {2 ** total_new}")

            # This gets calculation times
            with Parallel(n_jobs=-2, verbose=2) as parallel:
                hist_values = parallel(
                    delayed(do_measure)(
                        total_new,
                        i,
                        formula_with_layer,
                        first_new
                    )
                    for i in range(0, 2 ** total_new)
                )

            with open(hist_name, "w") as hist:
                hist.writelines([f"{val}\n" for val in hist_values])

# def measure_ganak_time():
#     schema_folder = "./data/single-schemas-aag/"
#     experiments = ["5_4", "6_4"]
#     for sorts in [
#         ("Bubble", "Pancake"),
#         ("Selection", "Bubble"),
#         ("Pancake", "Selection"),
#     ]:
#         for test_shortname in experiments:
#             dest_dir = ""
#             left_sort, right_sort = sorts
#             left_schema_name = f"{left_sort}Sort_{test_shortname}"
#             left_schema_file = f"{schema_folder}/{left_schema_name}.aag"
#             right_schema_name = f"{right_sort}Sort_{test_shortname}"
#             right_schema_file = f"{schema_folder}/{right_schema_name}.aag"

#             gl = Graph(left_schema_file, "L")
#             gr = Graph(right_schema_file, "R")

#             # if exists(hist_name):
#             #     continue

#             formula = make_united_miter_from_two_graphs(gl, gr)

#             n = int(test_shortname[0])
#             m = int(test_shortname[2])

#             input_size = n * m

#             formula_with_layer, new_vars = append_layer_to_cnf(formula, input_size)

#             test_name = f"{left_sort[0]}v{right_sort[0]}_{test_shortname}"
#             formula_with_layer.to_file(f"./data/miterfree-with-layer/{test_name}.cnf")

#             first_new, last_new = new_vars

#             last_new += 1

#             total_new = last_new - first_new

#             assert total_new == int(input_size / 2)
#             print(f"{test_name}, total tasks: {2 ** total_new}")

#             with Parallel(n_jobs=-2, verbose=2) as parallel:
#                 res = parallel(
#                     delayed(do_ganak_measure)(
#                         total_new, i, formula_with_layer, first_new, input_size
#                     )
#                     for i in range(0, 2**total_new)
#                 )

#                 success, ganak_timeout, ganak_failure = map(
#                     len,
#                     [
#                         list(filter(lambda p: p == verdict, res))
#                         for verdict in [SUCCESS, GANAK_TIMEOUT, GANAK_FAILURE]
#                     ],
#                 )

#                 stat_file = f"./data/ganak/stats/{test_name}.txt"
#                 with open(stat_file, "w") as f:
#                     f.writelines(
#                         [f"{f} {success=} {ganak_timeout=} {ganak_failure=}\n"]
#                     )

#                 merged_file = f"./data/ganak/{test_name}"

#                 for dirpath, dnames, fnames in os.walk("./"):
#                     for fname in fnames:
#                         if fname.startswith("ganak_store_results_"):
#                             with open(fname, "r") as f:
#                                 pid_lines = f.readlines()
#                                 with open(merged_file, "a") as f:
#                                     f.writelines(pid_lines)
#                                 os.system(f"rm {fname}")

#                 exit(0)


def get_assumptions_from_new_layer(i, first_new, total_new):
    assumptions = []
    for bit_id in range(0, total_new):
        modifier = None
        if (i & (1 << bit_id)) > 0:
            modifier = 1
        else:
            modifier = -1
        new_assumption = modifier * (first_new + bit_id)
        assumptions.append(new_assumption)
    return assumptions


def do_measure(total_new, i, formula_with_layer, first_new):
    assumptions = get_assumptions_from_new_layer(i, first_new, total_new)

    solver = Solver()
    solver.add_clauses(formula_with_layer.clauses + [[x] for x in assumptions])

    t1 = time.time()
    solver_res, solution = solver.solve()
    t2 = time.time()
    assert solver_res is False
    return t2 - t1


# def do_ganak_measure(total_new, instance_id, no_miter, first_new, input_size):

#     comment_line = "c ind"
#     for i in range(1, input_size):
#         comment_line += f" {i}"

#     assumptions = get_assumptions_from_new_layer(i, first_new, total_new)

#     for assumption in assumptions:
#         no_miter.append([assumption])

#     target_file = f"./tmp_for_{instance_id}"
#     no_miter.to_file(target_file)

#     os.system(f'echo "{comment_line}" >> {target_file}')

#     t1 = time.time()
#     try:
#         res = subprocess.check_output(
#             [
#                 "../../ganak/bin/ganak",
#                 "-t",
#                 "1000",
#                 "-delta",
#                 "0.03",
#                 target_file,
#             ],
#             stderr=subprocess.STDOUT,
#             text=True,
#         )
#         os.system(f"rm {target_file}")
#     except subprocess.CalledProcessError:
#         os.system(f"rm {target_file}")
#         return GANAK_FAILURE
#     t2 = time.time()

#     if "TIMEOUT" in res:
#         return GANAK_TIMEOUT

#     tmp1 = str(res).split("\n")[-5:][0]
#     tmp2 = str(res).split("\n")[-5:][3]

#     single_elem = f"{tmp1} {tmp2} {t2 - t1} {instance_id}\n"  # parse that and return nice line

#     pid = os.getpid()
#     with open(f"./ganak_store_results_{pid}", "a") as f:
#         f.writelines(single_elem)
#     return SUCCESS


if __name__ == "__main__":
    measure_solver_time(layer_type="maj")
