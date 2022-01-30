import time
import random
import itertools
import json
import pysat

from collections import defaultdict
from tqdm import tqdm

from pysat.solvers import Maplesat as Solver

import formula_builder as FB
import graph as G
import utils as U

# Algorithm hyperparameters:

# How disbalanced a gate is allowed to be to enter any of the bucket
DISBALANCE_THRESHOLD = 0.01

# This one is best left between 10 and 15, 2 ^ BUCKET_SIZE tasks are solved
BUCKET_SIZE = 15

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
        fractions = filter(lambda a: not a[1].startswith("i"), fractions)

    # filter the gates that are unbalanced enough
    thresholded_unbalanced = list(
        filter(
            lambda p: p[0] < DISBALANCE_THRESHOLD or p[0] > (1 - DISBALANCE_THRESHOLD),
            fractions,
        )
    )

    # leave only gate names
    unbalanced_nodes = list(map(lambda p: p[1], thresholded_unbalanced))
    return unbalanced_nodes


# Calculates a list of tuples:
# (saturation, bucket, domain, tag)
# saturation - value (0-1]
# bucket - list of node names, of which the bucket consists
# domain - list of positive ints, every int is a bitvector of length len(bucket)
# tag - either L or R for the left or right half of a miter schema, accordingly
def calculate_domain_saturations(g, unbalanced_nodes, tag, start_from):
    print(
        "Total unbalanced nodes selected for {} schema: {}".format(
            tag, len(unbalanced_nodes)
        )
    )

    buckets = [
        unbalanced_nodes[x : x + BUCKET_SIZE]
        for x in range(0, len(unbalanced_nodes), BUCKET_SIZE)
    ]

    print(
        "Total buckets to be built with size {}: {}".format(BUCKET_SIZE, len(buckets))
    )

    domains = list()

    pool = FB.TPoolHolder(start_from=start_from)
    formula = FB.make_formula_from_my_graph(g, pool)

    shift = -1
    for clause in formula.clauses:
        for var in clause:
            shift = max(shift, abs(var))

    # bucket : [gate_name]
    # domains : [(bucket, [bit_vector])]
    with Solver(bootstrap_with=formula.clauses) as solver:
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
    pool_left = FB.TPoolHolder()
    f_left = FB.make_formula_from_my_graph(g1, pool_left)

    # Here we solve the problem of clashing names by separating pools.
    # Therefore, 'v123' in the first pool will have a different id
    # then a 'v123' in the second. It would be better to handle collisions
    # on 'Graph' class level, for instance by generating some prefix to all names,
    # but that would require some significant refactoring. Therefore I just use
    # two pool instances. TODO refactor later.
    shift = -1
    for clause in f_left.clauses:
        for var in clause:
            shift = max(shift, abs(var))

    pool_right = FB.TPoolHolder(start_from=shift + 1)
    f_right = FB.make_formula_from_my_graph(g2, pool_right)

    shared_cnf = f_left.clauses + f_right.clauses

    return shared_cnf, pool_left, pool_right


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

    shared_cnf, pool_left, pool_right = prepare_shared_cnf_from_two_graphs(g1, g2)

    one_saturated_domains = 0
    one_defined = 0

    shared_cnf_len_at_start = len(shared_cnf)

    for saturation, bucket, domain, tag in shared_domain_info:
        if len(domain) == 1:
            one_saturated_domains += 1
            for unit_id, gate_name in enumerate(bucket):
                domain_value = domain[0]
                if tag == "L":
                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    shared_cnf.append([modifier * pool_left.v_to_id(gate_name)])
                elif tag == "R":
                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    shared_cnf.append([modifier * pool_right.v_to_id(gate_name)])
                else:
                    assert False
                one_defined += 1
        else:
            break

    assert len(shared_cnf) == shared_cnf_len_at_start + one_defined

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

    final_cnf = generate_miter_scheme(shared_cnf, pool_left, pool_right, g1, g2)

    runtimes = []
    equivalent = True

    tasks = list()

    with Solver(bootstrap_with=final_cnf, use_timer=True) as solver:
        for comb_id, combination in enumerate(
            tqdm(
                combinations,
                desc="Processing cartesian combination",
                total=cartesian_size,
            )
        ):
            # combination = [domain]
            left_assumptions = list()
            right_assumptions = list()

            for domain_id, domain_value in enumerate(combination):
                saturation, bucket, domain, tag = shared_domain_info[domain_id]
                assert domain_value in domain
                for unit_id, gate_name in enumerate(bucket):

                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1

                    if tag == "L":
                        left_assumptions.append(modifier * pool_left.v_to_id(gate_name))
                    elif tag == "R":
                        right_assumptions.append(
                            modifier * pool_right.v_to_id(gate_name)
                        )
                    else:
                        assert False

            total_assumptions = left_assumptions + right_assumptions

            sat_on_miter = solver.solve(assumptions=total_assumptions)
            runtimes.append(solver.time())
            tasks.append((solver.time(), comb_id, total_assumptions))

            if sat_on_miter:
                equivalent = False
                break

    runtimes = sorted(runtimes)
    metainfo["some_biggest_runtimes"] = []
    metainfo["sat_calls_only_runtimes"] = sum(runtimes)

    for i in range(1, 4):
        if len(runtimes) >= i:
            metainfo["some_biggest_runtimes"].append(runtimes[-i])

    final_cnf_as_formula = pysat.formula.CNF(from_clauses=final_cnf)
    final_cnf_as_formula.to_file(cnf_file)

    with open(tasks_dump_file, "w+") as f:
        pretty_tasks = dict()
        pretty_tasks["tasks"] = tasks
        f.write(json.dumps(pretty_tasks, indent=4))

    return equivalent


def generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2):
    assert g1.n_inputs == g2.n_inputs

    # TODO re-use input variables instead of adding clauses on inputs equality
    for input_id in range(0, g1.n_inputs):
        input_name = "v" + str(input_id)
        # Add clauses for input equality
        input_g1_var = g1.input_var_to_cnf_var(input_name, pool1)
        input_g2_var = g2.input_var_to_cnf_var(input_name, pool2)

        # EQ Tseyting encoding
        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    for output_id in range(len(g1.outputs)):
        # Add clause for output xor gate
        xor_gate = pool2.v_to_id("xor_" + str(output_id))
        output_code_name = "o" + str(output_id)
        left_output = g1.output_var_to_cnf_var(output_code_name, pool1)
        right_output = g2.output_var_to_cnf_var(output_code_name, pool2)

        # XOR Tseytin encoding
        # xorgate <=> left xor right
        shared_cnf.append([-1 * left_output, -1 * right_output, -1 * xor_gate])
        shared_cnf.append([left_output, right_output, -1 * xor_gate])
        shared_cnf.append([left_output, -1 * right_output, xor_gate])
        shared_cnf.append([-1 * left_output, right_output, xor_gate])

    # OR together all new xor_ variables
    lst = []
    for output_id in range(len(g1.outputs)):
        lst.append(pool2.v_to_id("xor_" + str(output_id)))
    shared_cnf.append(lst)

    return shared_cnf


def post_sampling_calculations(
    g1,
    g2,
    test_path_left,
    test_path_right,
    metainfo,
    unbalanced_nodes_left,
    unbalanced_nodes_right,
    t_start,
    settings,
    tasks_dump_file,
    cnf_file,
):
    best_domains_left, shift = calculate_domain_saturations(
        g1, unbalanced_nodes_left, tag="L", start_from=1
    )
    best_domains_right, _ = calculate_domain_saturations(
        g2, unbalanced_nodes_right, tag="R", start_from=shift + 1
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
    g1 = G.Graph(test_path_left)
    g2 = G.Graph(test_path_right)

    t_start = time.time()
    metainfo = dict()

    metainfo["max_cartesian_size"] = MAX_CARTESIAN_PRODUCT_SIZE
    metainfo["disbalance_threshold"] = DISBALANCE_THRESHOLD

    print("Schemas initialized, looking for unbalanced nodes in the left schema")
    unbalanced_nodes_left = find_unbalanced_gates(g1, should_include_nots)
    print("Looking for unbalanced nodes in the right schema")
    unbalanced_nodes_right = find_unbalanced_gates(g2, should_include_nots)
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
        unbalanced_nodes_left,
        unbalanced_nodes_right,
        t_start,
        settings,
        tasks_dump_file,
        cnf_file,
    )

    return result


def validate_naively(g1, g2, metainfo, cnf_file):
    pool_left = FB.TPoolHolder()
    f_left = FB.make_formula_from_my_graph(g1, pool_left)

    shift = -1
    for clause in f_left.clauses:
        for var in clause:
            shift = max(shift, var)

    pool_right = FB.TPoolHolder(start_from=shift + 1)
    f_right = FB.make_formula_from_my_graph(g2, pool_right)

    final_cnf = generate_miter_scheme(
        f_left.clauses + f_right.clauses, pool_left, pool_right, g1, g2
    )

    pysat.formula.CNF(from_clauses=final_cnf).to_file(cnf_file)

    with Solver(bootstrap_with=final_cnf, use_timer=True) as solver:
        result = solver.solve()
        metainfo["solver_only_time_no_preparation"] = solver.time()
        return not result


def naive_equivalence_check(test_path_left, test_path_right, metainfo_file, cnf_file):
    g1 = G.Graph(test_path_left)
    g2 = G.Graph(test_path_right)

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


if __name__ == "__main__":
    experiments = [
        # "4_3",
        "6_4",
        "7_4",
        "8_4"
    ]

    max_cartesian_sizes = [100000]
    unbalanced_thresholds = [0.03]

    for test_shortname in experiments:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        cnf_file = f"./hard-instances/cnf/{test_shortname}.cnf"
        cnf_naive_file = f"./hard-instances/cnf/{test_shortname}_naive.cnf"

        metainfo_file = f"./hard-instances/metainfo/{test_shortname}.txt"
        tasks_dump_file = f"./hard-instances/assumptions/{test_shortname}.txt"

        naive_equivalence_check(
            left_schema_file, right_schema_file, metainfo_file, cnf_naive_file
        )

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
