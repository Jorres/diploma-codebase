import aiger
import time
import random
import itertools
import json
import statistics

from collections import defaultdict

from pysat.solvers import Minisat22
from pysat.solvers import Glucose4

from aiger_cnf import aig2cnf

import formula_builder as FB
import graph as G
import utils as U

# Algorithm hyperparameters:

# How disbalanced a gate is allowed to be to enter any of the bucket
DISBALANCE_THRESHOLD = 0.03

# This one is best left between 10 and 15, 2 ^ BUCKET_SIZE tasks are solved
BUCKET_SIZE = 14

# Ideally, for every test there exists a perfect moment where we can stop
# adding domains into the cartesian product. But this is some reasonable
# threshold based on sorting tests
MAX_CARTESIAN_PRODUCT_SIZE = 5000000

RANDOM_SAMPLE_SIZE = 10000


# Returns names of nodes that are unbalanced enough, based on DISBALANCE_THRESHOLD.
def find_unbalanced_gates(g):
    random_sample = [[random.choice([True, False]) for t in range(
        g.n_inputs)] for i in range(RANDOM_SAMPLE_SIZE)]

    print("Random sampling unbalanced nodes, {} samples".format(RANDOM_SAMPLE_SIZE))
    had_true_on_node = defaultdict(int)

    for i, input in enumerate(random_sample):
        gate_values_on_input = g.calculate_schema_on_inputs(input)
        for name, value in gate_values_on_input.items():
            if value:
                had_true_on_node[name] += 1

    # map each gate to its saturation
    fractions = list(map(lambda name_cnt: (name_cnt[1] / RANDOM_SAMPLE_SIZE, name_cnt[0]),
                         had_true_on_node.items()))

    # filter the gates that are unbalanced enough
    thresholded_unbalanced = list(filter(
        lambda p: p[0] < DISBALANCE_THRESHOLD or p[0] > (1 - DISBALANCE_THRESHOLD), fractions))

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
    print("Total unbalanced nodes selected for {} schema: {}".format(
        tag, len(unbalanced_nodes)))
    buckets = [unbalanced_nodes[x:x+BUCKET_SIZE]
               for x in range(0, len(unbalanced_nodes), BUCKET_SIZE)]
    print("Total buckets to be built with size {}: {}".format(
        BUCKET_SIZE, len(buckets)))

    domains = list()

    pool = FB.TPoolHolder(start_from=start_from)
    formula = FB.make_formula_from_my_graph(g, pool)

    shift = -1
    for clause in formula.clauses:
        for var in clause:
            shift = max(shift, abs(var))

    with Glucose4(bootstrap_with=formula.clauses) as solver:
        for bucket_id, bucket in enumerate(buckets):
            domain = list()

            cur_bucket_size = len(bucket)
            for i in range(0, 2 ** cur_bucket_size):
                assumptions = list()
                for gate_in_bucket_id, gate_name in enumerate(bucket):
                    if (i & (1 << gate_in_bucket_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    assumptions.append(
                        modifier * pool.v_to_id(gate_name))

                if solver.solve(assumptions=assumptions):
                    domain.append(i)

            domains.append((bucket, domain))

    # calculate saturation for each domain
    domains_with_saturation = list(map(lambda p: (len(p[1]) / (2 ** len(p[0])),
                                                  p[0], p[1], tag), domains))

    return domains_with_saturation, shift


# Calculates a cartesian product, encodes a miter schema,
# then iterates over the product to make sure there is UNSAT on every possible
# combination of domain values.
def check_for_equivalence(g1, g2, domains_info_left, domains_info_right, metainfo_dict):
    shared_domain_info = sorted(domains_info_left + domains_info_right)

    cartesian_size = 1
    best_domains = list()
    for (saturation, bucket, domain, tag) in shared_domain_info:
        if cartesian_size * len(domain) > MAX_CARTESIAN_PRODUCT_SIZE:
            break
        best_domains.append(domain)
        cartesian_size *= len(domain)
    metainfo_dict['actual_cartesian_size'] = cartesian_size

    if len(best_domains) == 0:
        return True, -1

    # construct the cartesian product of selected domains:
    combinations = itertools.product(*best_domains)

    print("Total size of cartesian product of the domains:", cartesian_size)

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

    final_cnf = generate_miter_scheme(
        shared_cnf, pool_left, pool_right, g1, g2)
    print("Miter schema generated. Iterating over cartesian product now")

    runtimes = []
    equivalent = True
    with Glucose4(bootstrap_with=final_cnf, use_timer=True) as solver:
        for comb_id, combination in enumerate(combinations):
            assumptions = list()
            for domain_id, domain_value in enumerate(combination):
                saturation, bucket, domain, tag = shared_domain_info[domain_id]
                for unit_id, gate in enumerate(bucket):
                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    if tag == "L":
                        assumptions.append(modifier * pool_left.v_to_id(gate))
                    elif tag == "R":
                        assumptions.append(modifier * pool_right.v_to_id(gate))
                    else:
                        assert False

            result = solver.solve(assumptions=assumptions)
            runtimes.append(solver.time())
            if result:
                print("Schemas are not equivalent, SAT on miter schema has been found")
                equivalent = False
                break

    print("Schemas are equivalent, UNSAT has been achieved on every element from cartesian join")

    runtimes = sorted(runtimes)
    metainfo_dict['quantiles'] = statistics.quantiles(runtimes, n=10)
    if len(runtimes) > 2:
        metainfo_dict['top_three'] = [runtimes[-3], runtimes[-2], runtimes[-1]]

    return equivalent


def generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2):
    assert g1.n_inputs == g2.n_inputs
    for input_id in range(0, g1.n_inputs):
        input_name = 'v' + str(input_id)
        # Add clauses for input equality
        input_g1_var = g1.input_var_to_cnf_var(input_name, pool1)
        input_g2_var = g2.input_var_to_cnf_var(input_name, pool2)

        # NOT Tseyting encoding
        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    for output_id in range(len(g1.outputs)):
        # Add clause for output xor gate
        xor_gate = pool2.v_to_id("xor_" + str(output_id))
        output_code_name = 'o' + str(output_id)
        left_output = g1.output_var_to_cnf_var(output_code_name, pool1)
        right_output = g2.output_var_to_cnf_var(output_code_name, pool2)

        # XOR Tseytin encoding
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


def domain_equivalence_check(test_path_left, test_path_right, res_filename):
    left_schema = aiger.load(test_path_left)
    right_schema = aiger.load(test_path_right)
    g1 = G.Graph()
    g1.from_aig(left_schema)
    g2 = G.Graph()
    g2.from_aig(right_schema)

    t1 = time.time()
    res = dict()
    res['max_cartesian_size'] = MAX_CARTESIAN_PRODUCT_SIZE
    res['disbalance_threshold'] = DISBALANCE_THRESHOLD
    print("Schemas initialized, looking for unbalanced nodes in the left schema")
    unbalanced_nodes_left = find_unbalanced_gates(g1)
    print("Looking for unbalanced nodes in the right schema")
    unbalanced_nodes_right = find_unbalanced_gates(g2)
    print("Unbalanced nodes found, proceeding to building domains")
    best_domains_left, shift = calculate_domain_saturations(
        g1, unbalanced_nodes_left, tag="L", start_from=1)
    best_domains_right, _ = calculate_domain_saturations(
        g2, unbalanced_nodes_right, tag="R", start_from=shift + 1)
    result = check_for_equivalence(
        g1, g2, best_domains_left, best_domains_right, res)
    t2 = time.time()

    res_string = "Running {} against {} took {} seconds".format(
        test_path_left, test_path_right, str(t2 - t1))
    res['left_schema'] = test_path_left
    res['right_schema'] = test_path_right
    res['time'] = str(t2 - t1)
    res['outcome'] = result
    U.print_to_file(res_filename, json.dumps(res, indent=4))
    print(res_string)
    return result


def validate_against_aig_naively(g, aig):
    start_cnf = aig2cnf(aig.aig)
    shift = -1
    for clause in start_cnf.clauses:
        for var in clause:
            shift = max(shift, var)

    pool = FB.TPoolHolder(start_from=shift + 1)
    my_cnf = FB.make_formula_from_my_graph(g, pool)
    final_cnf = my_cnf.clauses
    for clause in start_cnf.clauses:
        if len(clause) == 1:
            continue
        final_cnf.append(list(clause))

    for input in aig.inputs:
        # Add clauses for input equality
        input_aig_var = start_cnf.input2lit[input]
        input_graph_var = g.input_var_to_cnf_var(input, pool)

        final_cnf.append([-1 * input_aig_var, input_graph_var])
        final_cnf.append([input_aig_var, -1 * input_graph_var])

    for i, output in enumerate(aig.outputs):
        # Add clause for every output xor gate
        c = pool.v_to_id("xor_" + str(i))
        a = start_cnf.output2lit[output]
        b = g.output_var_to_cnf_var(output, pool)
        final_cnf.append([-1 * a, -1 * b, -1 * c])
        final_cnf.append([a, b, -1 * c])
        final_cnf.append([a, -1 * b, c])
        final_cnf.append([-1 * a, b, c])

    # OR together all new xor_ variables
    lst = []
    for i in range(len(aig.outputs)):
        lst.append(pool.v_to_id("xor_" + str(i)))
    final_cnf.append(lst)

    with Glucose4(bootstrap_with=final_cnf) as solver:
        print("Running SAT-solver to determine scheme equivalency")
        result = solver.solve()
        if not result:
            print("Schemas are equivalent, UNSAT on miter scheme")
        if result:
            print("Schemas are NOT equivalent, SAT on miter scheme has been found")
        return not result


def naive_equivalence_check(test_path_left, test_path_right, res_filename):
    aig_instance_left = aiger.load(test_path_left)
    aig_instance_right = aiger.load(test_path_right)

    g1 = G.Graph()
    g1.from_aig(aig_instance_left)
    t1 = time.time()
    result = validate_against_aig_naively(g1, aig_instance_right)
    t2 = time.time()
    res = dict()
    res_string = "Running {} against {} naively took {}".format(
        test_path_left, test_path_right, str(t2 - t1))
    print(res_string)
    res['left_schema'] = test_path_left
    res['right_schema'] = test_path_right
    res['time'] = str(t2 - t1)
    res['outcome'] = result
    U.print_to_file(res_filename, json.dumps(res, indent=4))


if __name__ == "__main__":
    experiments = [
        ("./new_sorts/BubbleSort_4_3.aig",
         "./new_sorts/PancakeSort_4_3.aig",
         "./results/4_3.txt"
         ),
        ("./new_sorts/BubbleSort_6_4.aig",
         "./new_sorts/PancakeSort_6_4.aig",
         "./results/6_4.txt"
         ),
        ("./new_sorts/BubbleSort_7_4.aig",
         "./new_sorts/PancakeSort_7_4.aig",
         "./results/7_4.txt"
         ),
        ("./new_sorts/BubbleSort_8_4.aig",
         "./new_sorts/PancakeSort_8_4.aig",
         "./results/8_4.txt"
         ),
        # ("./new_sorts/BubbleSort_8_5.aig",
        #  "./new_sorts/PancakeSort_8_5.aig",
        #  "./results/8_5.txt"
        #  ),
        # ("./new_sorts/BubbleSort_8_6.aig",
        #  "./new_sorts/PancakeSort_8_6.aig",
        #  "./results/8_6.txt"
        #  ),
        # ("./new_sorts/BubbleSort_8_7.aig",
        #  "./new_sorts/PancakeSort_8_7.aig",
        #  "./results/8_7.txt"
        #  ),
        # ("./new_sorts/BubbleSort_9_4.aig",
        #  "./new_sorts/PancakeSort_9_4.aig",
        #  "./results/9_4.txt"
        #  ),
        # ("./new_sorts/BubbleSort_10_4.aig",
        #  "./new_sorts/PancakeSort_10_4.aig",
        #  "./results/10_4.txt"
        #  ),
    ]

    max_cartesian_sizes = [10, 100, 1000, 10000, 100000, 1000000, 10000000]
    unbalanced_thresholds = [0.02, 0.03, 0.05]

    for (left_schema_filename, right_schema_filename, res_filename) in experiments:
        naive_equivalence_check(left_schema_filename,
                                right_schema_filename, res_filename)
        for max_cartesian_size in max_cartesian_sizes:
            for unbalanced_threshold in unbalanced_thresholds:
                MAX_CARTESIAN_PRODUCT_SIZE = max_cartesian_size
                DISBALANCE_THRESHOLD = unbalanced_threshold
                domain_equivalence_check(left_schema_filename,
                                         right_schema_filename, res_filename)
