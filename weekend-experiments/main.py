import time
import random
import itertools
import json
import pysat
import math

from collections import defaultdict
from tqdm import tqdm

from pysat.solvers import Maplesat as PysatSolver
from pycryptosat import Solver

import formula_builder as FB
import graph as G
import utils as U

# Algorithm hyperparameters:

# How disbalanced a gate is allowed to be to enter any of the bucket
DISBALANCE_THRESHOLD = 0.01

# This one is best left between 10 and 15, 2 ^ BUCKET_SIZE tasks are solved
BUCKET_SIZE = 13

# Ideally, for every test there exists a perfect moment where we can stop
# adding domains into the cartesian product. But this is some reasonable
# threshold based on sorting tests
MAX_CARTESIAN_PRODUCT_SIZE = 5000000

RANDOM_SAMPLE_SIZE = 10000


# Returns names of nodes that are unbalanced enough, based on DISBALANCE_THRESHOLD.
def find_unbalanced_gates(g, should_include_nots):
    print("Random sampling unbalanced nodes, {} samples".format(RANDOM_SAMPLE_SIZE))

    random.seed(42)

    complete_input_size = range(2 ** g.n_inputs)
    random_sample = random.sample(
        complete_input_size, min(len(complete_input_size), RANDOM_SAMPLE_SIZE)
    )

    had_true_on_node = defaultdict(int)

    for i, input in enumerate(
        tqdm(random_sample, desc="Random sampling unbalanced nodes")
    ):
        gate_values_on_input = g.calculate_schema_on_inputs(input)
        for name, value in gate_values_on_input.items():
            if value:
                had_true_on_node[name] += 1

    # map each gate to its saturation
    # fractions : [(disbalance, gate_name)]
    fractions = list(
        map(
            lambda name_cnt: (name_cnt[1] / RANDOM_SAMPLE_SIZE, name_cnt[0]),
            had_true_on_node.items(),
        )
    )

    if not should_include_nots:
        fractions = list(filter(lambda a: not a[1].startswith("i"), fractions))

    # filter the gates that are unbalanced enough
    unbalanced = list(
        filter(
            lambda p: p[0] < DISBALANCE_THRESHOLD or p[0] > (1 - DISBALANCE_THRESHOLD),
            fractions,
        )
    )

    unbalanced_gates = list(map(lambda p: p[1], unbalanced))

    buckets = [
        unbalanced_gates[x : x + BUCKET_SIZE]
        for x in range(0, len(unbalanced_gates), BUCKET_SIZE)
    ]

    return buckets


# Calculates a list of tuples:
# (saturation, bucket, domain, tag)
# saturation - value (0-1]
# bucket - list of node names, of which the bucket consists
# domain - list of positive ints, every int is a bitvector of length len(bucket)
# tag - either L or R for the left or right half of a miter schema, accordingly
def calculate_domain_saturations(g, buckets, tag, start_from):
    print("Total buckets selected for {} schema: {}".format(tag, len(buckets)))

    domains = list()

    pool = FB.TPoolHolder(start_from=start_from)
    formula = FB.make_formula_from_my_graph(g, pool)

    shift = -1
    for clause in formula.clauses:
        for var in clause:
            shift = max(shift, abs(var))

    # bucket : [gate_name]
    # domains : [(bucket, [bit_vector])]
    with PysatSolver(bootstrap_with=formula.clauses) as solver:
        for bucket_id, bucket in enumerate(
            tqdm(buckets, desc="Calculating saturation for bucket")
        ):
            domain = list()

            cur_bucket_size = len(bucket)
            for i in range(0, 2 ** cur_bucket_size):
                assumptions = list()
                for gate_in_bucket_id, gate_name in enumerate(bucket):
                    if (i & (1 << gate_in_bucket_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    assumptions.append(modifier * pool.v_to_id(gate_name))

                if solver.solve(assumptions=assumptions):
                    domain.append(i)

            domains.append((bucket, domain))

    # calculate saturation for each domain
    # domains : [(saturation, bucket, [bit_vector], tag)]
    domains_with_saturation = list(
        map(lambda p: (len(p[1]) / (2 ** len(p[0])), p[0], p[1], tag), domains)
    )
    return domains_with_saturation, shift


def prepare_shared_cnf_from_two_graphs(g1, g2):
    pool = FB.TPoolHolder()
    shared_cnf = FB.make_united_miter_from_two_graphs(g1, g2, pool)
    return shared_cnf.clauses, pool


# Calculates a cartesian product, encodes a miter schema,
# then iterates over the product to make sure there is UNSAT on every possible
# combination of domain values.
def check_for_equivalence(
    g1,
    g2,
    domains_info_left,
    domains_info_right,
    metainfo,
    settings,
    tasks_dump_file,
    cnf_file,
):
    shared_domain_info = sorted(domains_info_left + domains_info_right)


    shared_cnf, pool = prepare_shared_cnf_from_two_graphs(g1, g2)

    one_saturated_domains = 0
    one_defined = 0

    for saturation, bucket, domain, tag in shared_domain_info:
        if len(domain) == 1:
            one_saturated_domains += 1
            for unit_id, gate_name in enumerate(bucket):
                domain_value = domain[0]
                if (domain_value & (1 << unit_id)) > 0:
                    modifier = 1
                else:
                    modifier = -1
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
        if cartesian_size * len(domain) > MAX_CARTESIAN_PRODUCT_SIZE:
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

    final_cnf = generate_miter_scheme(shared_cnf, pool, g1, g2)

    final_cnf_as_formula = pysat.formula.CNF(from_clauses=final_cnf)
    final_cnf_as_formula.to_file(cnf_file)


    runtimes = []
    equivalent = True
    tasks = list()

    solver = Solver()
    solver.add_clauses(final_cnf)

    bucket_to_runtime = dict()

    for comb_id, combination in enumerate(
        tqdm(
            combinations,
            desc="Processing cartesian combination",
            total=cartesian_size,
        )
    ):
        # combination = [domain]
        assumptions = list()

        for domain_id, domain_value in enumerate(combination):
            saturation, bucket, domain, tag = shared_domain_info[domain_id]

            assert domain_value in domain
            for unit_id, gate_name in enumerate(bucket):
                if (domain_value & (1 << unit_id)) > 0:
                    modifier = 1
                else:
                    modifier = -1
                assumptions.append(modifier * pool.v_to_id(gate_name))

        t1 = time.time()
        sat_on_miter, solution = solver.solve(assumptions=assumptions)
        t2 = time.time()
        runtimes.append(t2 - t1)
        # bucket_to_runtime[domain_id] = t2 - t1
        tasks.append((t2 - t1, comb_id, assumptions))

        if sat_on_miter:
            equivalent = False
            break

    runtimes = sorted(runtimes)
    metainfo["some_biggest_runtimes"] = []

    bucket_info = dict()
    i = 0
    for saturation, bucket, domain, tag in shared_domain_info:
        bucket_info[i] = dict()
        # bucket_info[i]['runtime'] = bucket_to_runtime[i]
        bucket_lits = []

        if tag == "L":
            for gate in bucket:
                bucket_lits.append(g1.source_name_to_lit[gate] // 2)
        else:
            for gate in bucket:
                bucket_lits.append(g2.source_name_to_lit[gate] // 2)

        bucket_info[i]['bucket_literals'] = bucket_lits

        if tag == "L":
            bucket_info[i]['graph_name'] = g1.name
        else:
            bucket_info[i]['graph_name'] = g2.name
        i += 1

    with open("./dumped_buckets.txt", "a+") as f:
        f.write(json.dumps(bucket_info, indent=4))

    for i in range(1, 4):
        if len(runtimes) >= i:
            metainfo["some_biggest_runtimes"].append(runtimes[-i])

    with open(tasks_dump_file, "w+") as f:
        pretty_tasks = dict()
        pretty_tasks["tasks"] = tasks
        f.write(json.dumps(pretty_tasks, indent=4))

    return equivalent


def generate_miter_scheme(shared_cnf, pool, g1, g2):
    assert g1.n_inputs == g2.n_inputs

    # TODO re-use input variables instead of adding clauses on inputs equality
    for input_id in range(0, g1.n_inputs):
        # Add clauses for input equality
        input_g1_var = g1.input_var_to_cnf_var(f"v{input_id}{g1.tag}", pool)
        input_g2_var = g2.input_var_to_cnf_var(f"v{input_id}{g2.tag}", pool)

        # EQ Tseyting encoding
        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    for output_id in range(g1.n_outputs):
        # Add clause for output xor gate
        xor_gate = pool.v_to_id(f"xor_{output_id}")
        output_code_name = f"o{output_id}"
        left_output = g1.output_var_to_cnf_var(output_code_name, pool)
        right_output = g2.output_var_to_cnf_var(output_code_name, pool)
        print(left_output, right_output, xor_gate)

        # XOR Tseytin encoding
        # xorgate <=> left xor right
        shared_cnf.append([-1 * left_output, -1 * right_output, -1 * xor_gate])
        shared_cnf.append([left_output, right_output, -1 * xor_gate])
        shared_cnf.append([left_output, -1 * right_output, xor_gate])
        shared_cnf.append([-1 * left_output, right_output, xor_gate])

    # OR together all new xor_ variables
    lst = []
    for output_id in range(g1.n_outputs):
        lst.append(pool.v_to_id(f"xor_{output_id}"))
    shared_cnf.append(lst)

    return shared_cnf


def post_sampling_calculations(
    g1,
    g2,
    test_path_left,
    test_path_right,
    metainfo,
    buckets_left,
    buckets_right,
    t_start,
    settings,
    tasks_dump_file,
    cnf_file,
):
    best_domains_left, shift = calculate_domain_saturations(
        g1, buckets_left, tag="L", start_from=1
    )
    best_domains_right, _ = calculate_domain_saturations(
        g2, buckets_right, tag="R", start_from=shift + 1
    )
    result = check_for_equivalence(
        g1,
        g2,
        best_domains_left,
        best_domains_right,
        metainfo,
        settings,
        tasks_dump_file,
        cnf_file,
    )
    t_finish = time.time()

    time_elapsed = str(t_finish - t_start)
    metainfo["left_schema"] = test_path_left
    metainfo["right_schema"] = test_path_right
    metainfo["time"] = time_elapsed
    metainfo["outcome"] = result
    U.print_to_file(metainfo_file, json.dumps(metainfo, indent=4))
    return result


def domain_equivalence_check(
    test_path_left,
    test_path_right,
    metainfo_file,
    cnf_file,
    tasks_dump_file,
    should_include_nots,
):
    g1 = G.Graph(test_path_left, "L")
    g2 = G.Graph(test_path_right, "R")

    g1.remove_identical()
    g2.remove_identical()

    t_start = time.time()
    metainfo = dict()

    metainfo["max_cartesian_size"] = MAX_CARTESIAN_PRODUCT_SIZE
    metainfo["disbalance_threshold"] = DISBALANCE_THRESHOLD

    print("Schemas initialized, looking for unbalanced nodes in the left schema")
    buckets_left = find_unbalanced_gates(g1, should_include_nots)
    print("Looking for unbalanced nodes in the right schema")
    buckets_right = find_unbalanced_gates(g2, should_include_nots)
    print("Unbalanced nodes found, proceeding to building domains")

    settings = dict()
    metainfo["should_include_nots"] = should_include_nots
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
        settings,
        tasks_dump_file,
        cnf_file,
    )

    return result


def validate_naively(g1, g2, metainfo, cnf_file):

    shared_cnf, pool = prepare_shared_cnf_from_two_graphs(g1, g2)

    final_cnf = generate_miter_scheme(shared_cnf, pool, g1, g2)

    pysat.formula.CNF(from_clauses=final_cnf).to_file(cnf_file)

    solver = Solver()
    solver.add_clauses(final_cnf)

    t1 = time.time()
    result, solution = solver.solve()
    t2 = time.time()

    metainfo["solver_only_time_no_preparation"] = t2 - t1
    return not result


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
    result = validate_naively(g1, g2, metainfo, cnf_file)
    t2 = time.time()
    metainfo["time"] = str(t2 - t1)
    metainfo["outcome"] = result
    U.print_to_file(metainfo_file, json.dumps(metainfo, indent=4))


def validate_open_xor(g1, g2, metainfo):
    shared_cnf, pool = prepare_shared_cnf_from_two_graphs(g1, g2)

    # TODO re-use input variables instead of adding clauses on inputs equality (!!!)
    for input_id in range(0, g1.n_inputs):

        # Add clauses for input equality
        input_g1_var = g1.input_var_to_cnf_var(f"v{input_id}{g1.tag}", pool)
        input_g2_var = g2.input_var_to_cnf_var(f"v{input_id}{g2.tag}", pool)

        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    solver = Solver()
    solver.add_clauses(shared_cnf)

    assert g1.n_outputs == g2.n_outputs
    for output_id in range(g1.n_outputs):
        output_name = f"o{output_id}"
        output_var_1 = g1.output_var_to_cnf_var(output_name, pool)
        output_var_2 = g2.output_var_to_cnf_var(output_name, pool)

        conj_table = list()
        one_xor_runtime = list()
        for bit_left in [-1, 1]:
            for bit_right in [-1, 1]:
                assumptions = [
                        bit_left * output_var_1,
                        bit_right * output_var_2
                ]

                t1 = time.time()
                res, solution = solver.solve(assumptions=assumptions)
                # print(solution)
                conj_table.append(res)
                t2 = time.time()

                one_xor_runtime.append(t2 - t1)
        metainfo[f'runtimes_{output_id}'] = one_xor_runtime

        if conj_table == [True, False, False, True]:
            print(f"Output {output_id} equivalent")
        else:
            print(f"Output {output_id} non-equivalent")
            return False

    return True


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
    result = validate_open_xor(g1, g2, metainfo)
    t2 = time.time()

    metainfo["total_time"] = str(t2 - t1)
    metainfo["outcome"] = result
    U.print_to_file(metainfo_file, json.dumps(metainfo, indent=4))


if __name__ == "__main__":
    experiments = [
        # "4_3",
        "6_4",
        # "7_4",
        # "8_4"
    ]

    max_cartesian_sizes = [100000]
    unbalanced_thresholds = [0.1]

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

        for max_cartesian_size in max_cartesian_sizes:
            for unbalanced_threshold in unbalanced_thresholds:
                MAX_CARTESIAN_PRODUCT_SIZE = 100000
                DISBALANCE_THRESHOLD = unbalanced_threshold
                domain_equivalence_check(
                    left_schema_file,
                    right_schema_file,
                    metainfo_file,
                    cnf_file,
                    tasks_dump_file,
                    should_include_nots=False,
                )
                # domain_equivalence_check(left_schema_file,
                #                          right_schema_file, metainfo_file, should_include_nots=False)
