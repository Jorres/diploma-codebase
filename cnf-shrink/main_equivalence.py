import aiger
import time
import random
import itertools
import json
import statistics
import pysat
import sys

from collections import defaultdict
from tqdm import tqdm

# Minisat22, Glucose4
from pysat.solvers import Maplesat as Solver

import formula_builder as FB
import graph as G
import utils as U

# Algorithm hyperparameters:

# How disbalanced a gate is allowed to be to enter any of the bucket
DISBALANCE_THRESHOLD = 0.1

# This one is best left between 10 and 15, 2 ^ BUCKET_SIZE tasks are solved
BUCKET_SIZE = 15

# Ideally, for every test there exists a perfect moment where we can stop
# adding domains into the cartesian product. But this is some reasonable
# threshold based on sorting tests
MAX_CARTESIAN_PRODUCT_SIZE = 5000000

RANDOM_SAMPLE_SIZE = 10000

SECONDS_BEFORE_MODELS_ENUMERATION = 20
MAX_ENUMMED_MODELS_SIZE = 50000

SECONDS_SOLVING_NO_OPTIMIZATION = 15
SECONDS_ON_ONE_DOMAIN_ITERATION = 5


# Returns names of nodes that are unbalanced enough, based on DISBALANCE_THRESHOLD.
def find_unbalanced_gates(g):
    print("Random sampling unbalanced nodes, {} samples".format(RANDOM_SAMPLE_SIZE))

    random.seed(42)

    complete_input_size = range(2 ** g.n_inputs)
    random_sample = random.sample(complete_input_size, min(
        len(complete_input_size), RANDOM_SAMPLE_SIZE))

    had_true_on_node = defaultdict(int)

    for i, input in enumerate(tqdm(random_sample, desc="Random sampling unbalanced nodes")):
        gate_values_on_input = g.calculate_schema_on_inputs(input)
        for name, value in gate_values_on_input.items():
            if value:
                had_true_on_node[name] += 1

    # map each gate to its saturation
    # fractions : [(disbalance, gate_name)]
    fractions = list(map(lambda name_cnt: (name_cnt[1] / RANDOM_SAMPLE_SIZE, name_cnt[0]),
                         had_true_on_node.items()))

    only_and_fractions = filter(lambda a: not a[1].startswith('i'), fractions)

    # filter the gates that are unbalanced enough
    thresholded_unbalanced = list(filter(
        lambda p: p[0] < DISBALANCE_THRESHOLD or p[0] > (1 - DISBALANCE_THRESHOLD), only_and_fractions))

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

    # pool.v_to_id = None

    # bucket : [gate_name]
    # domains : [(bucket, [bit_vector])]
    with Solver(bootstrap_with=formula.clauses) as solver:
        for bucket_id, bucket in enumerate(tqdm(buckets, desc="Calculating saturation for bucket")):
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
    # domains : [(saturation, bucket, [bit_vector], tag)]
    domains_with_saturation = list(map(lambda p: (len(p[1]) / (2 ** len(p[0])),
                                                  p[0], p[1], tag), domains))
    return domains_with_saturation, shift


def get_possible_inputs(g, cnf, assumptions, pool):
    inputs = set()
    with Solver(bootstrap_with=cnf) as solver:
        for id, model in enumerate(tqdm(solver.enum_models(assumptions=assumptions, desc="Enumerating models"))):
            input_clause = list()

            input = 0

            # Construct a helper structure for easier lookup
            fast_model = dict()

            for val in model:
                literal = abs(val)
                fast_model[literal] = val > 0

            for input_id in range(g.n_inputs):
                input_code_name = 'v' + str(input_id)
                input_literal = g.input_var_to_cnf_var(input_code_name, pool)
                assert input_literal in fast_model
                if fast_model[input_literal]:
                    input += 2 ** input_id

                # Construct a prohibition clause for current input
                modifier = 1
                if not fast_model[input_literal]:
                    modifier = -1
                # We're prohibiting this clause, therefore we need to take
                # every input bit with a reverse modifier:
                # not (a1 && a2 ... an) == (not a1 || not a2 ... not an)
                modifier *= -1
                input_clause.append(modifier * input_literal)

            assert len(inputs) == id

            inputs.add(input)
            solver.add_clause(input_clause)

            if len(inputs) > MAX_ENUMMED_MODELS_SIZE:
                return False, inputs
    return True, inputs


def try_check_for_satisfying_sets_naively(g1, g2, left_assumptions, right_assumptions, pool1, pool2, cnf1, cnf2):
    status_left, left_possible_inputs = get_possible_inputs(
        g1, cnf1, left_assumptions, pool1)
    status_right, right_possible_inputs = get_possible_inputs(
        g2, cnf2, right_assumptions, pool2)

    if not status_left and not status_right:
        tqdm.write(
            'Too many models to enumerate for this graph, aborting. Solving directly again.')
        return None

    if status_left:
        inputs = left_possible_inputs
    if status_right and len(right_possible_inputs) < len(left_possible_inputs):
        inputs = right_possible_inputs

    tqdm.write("{} {}".format(
        len(left_possible_inputs), len(right_possible_inputs)))

    for input in inputs:
        left_outputs = g1.calculate_schema_on_inputs(input)
        right_outputs = g2.calculate_schema_on_inputs(input)
        for output_id in range(len(g1.outputs)):
            output_code_name = 'o' + str(output_id)
            left_output_name = g1.output_name_to_node_name[
                output_code_name]
            right_output_name = g2.output_name_to_node_name[
                output_code_name]
            if left_outputs[left_output_name] != right_outputs[right_output_name]:
                return True
    return False


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
def check_for_equivalence(g1, g2, domains_info_left, domains_info_right, metainfo_dict, settings):
    shared_domain_info = sorted(domains_info_left + domains_info_right)
    # print("Distribution: {}, total domains: {}".format(
    #     list(map(lambda x: len(x[2]), shared_domain_info)), len(shared_domain_info)))

    shared_cnf, pool_left, pool_right = prepare_shared_cnf_from_two_graphs(
        g1, g2)
    one_saturated_domains = 0

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
                    shared_cnf.append(
                        [modifier * pool_left.v_to_id(gate_name)])
                elif tag == "R":
                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    shared_cnf.append(
                        [modifier * pool_right.v_to_id(gate_name)])
        else:
            break

    shared_domain_info = shared_domain_info[one_saturated_domains:]

    cartesian_size = 1
    best_domains = list()
    for (saturation, bucket, domain, tag) in shared_domain_info:
        if cartesian_size * len(domain) > MAX_CARTESIAN_PRODUCT_SIZE:
            break
        best_domains.append(domain)
        cartesian_size *= len(domain)

    metainfo_dict['actual_cartesian_size'] = cartesian_size

    # construct the cartesian product of selected domains:
    combinations = itertools.product(*best_domains)

    print("Total size of cartesian product of the domains:", cartesian_size)
    print("Distribution: {}, total domains: {}".format(
        list(map(lambda x: len(x), best_domains)), len(best_domains)))

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

    metainfo_dict['MODELS_ENUMERATION_ENABLED'] = settings['model_enumeration_enabled']
    metainfo_dict['enum_solved_cnfs'] = list()

    with Solver(bootstrap_with=final_cnf, use_timer=True) as solver:
        for comb_id, combination in enumerate(tqdm(combinations, desc="Processing cartesian combination", total=cartesian_size)):
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
                        left_assumptions.append(
                            modifier * pool_left.v_to_id(gate_name))
                    elif tag == "R":
                        right_assumptions.append(
                            modifier * pool_right.v_to_id(gate_name))
                    else:
                        assert False

            total_assumptions = left_assumptions + right_assumptions

            sat_on_miter = None

            if settings['model_enumeration_enabled']:
                sat_on_miter = U.solve_with_timeout(
                    solver, total_assumptions, SECONDS_BEFORE_MODELS_ENUMERATION)
                if sat_on_miter is None:
                    tqdm.write('Difficult task encountered')
                    t1 = time.time()
                    sat_on_miter = try_check_for_satisfying_sets_naively(
                        g1, g2, left_assumptions, right_assumptions, pool_left, pool_right, f_left, f_right)
                    t2 = time.time()
                    runtimes.append(t2 - t1)
                    metainfo_dict['enum_solved_cnfs'].append(t2 - t1)
                else:
                    runtimes.append(solver.time())

            # Trying to solve for a while, before we decide it is time for another
            # optimization
            if sat_on_miter is None:
                sat_on_miter = U.solve_with_timeout(
                    solver, total_assumptions, SECONDS_SOLVING_NO_OPTIMIZATION)
                if sat_on_miter:
                    runtimes.append(solver.time())

            # Optimization with feeding assumption sets one by one
            if sat_on_miter is None and settings['domain_one_by_one_consumption']:
                bucketed_assumptions = [total_assumptions[x:x+BUCKET_SIZE]
                                        for x in range(0, len(total_assumptions), BUCKET_SIZE)]

                # solving with all buckets is equivalent to solving with total_assumptions, we
                # do that later anyway
                bucketed_assumptions.pop()

                current_assumptions = bucketed_assumptions[0] + \
                    bucketed_assumptions[1]

                next_bucket = 2
                for _ in tqdm(U.while_true_generator(), desc="Appending domains one by one"):
                    sat_on_miter = U.solve_with_timeout(
                        solver, current_assumptions, SECONDS_ON_ONE_DOMAIN_ITERATION)
                    if sat_on_miter is not None:
                        runtimes.append(solver.time())
                        break
                    if next_bucket == len(bucketed_assumptions):
                        break
                    current_assumptions = current_assumptions + \
                        bucketed_assumptions[next_bucket]
                    next_bucket += 1

            # Finally, solving task without time limit, tried all optimizations without success
            if sat_on_miter is None:
                sat_on_miter = solver.solve(assumptions=total_assumptions)
                runtimes.append(solver.time())

            if sat_on_miter:
                equivalent = False
                break

    if equivalent:
        print("Schemas are equivalent, UNSAT has been achieved on every element from cartesian join")
    else:
        print("Schemas are not equivalent, SAT on miter schema has been found")

    runtimes = sorted(runtimes)
    if len(runtimes) > 2:
        metainfo_dict['quantiles'] = statistics.quantiles(runtimes, n=10)
    metainfo_dict['some_biggest_runtimes'] = []
    for i in range(1, 4):
        if len(runtimes) >= i:
            metainfo_dict['some_biggest_runtimes'].append(runtimes[-i])

    return equivalent


def generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2):
    assert g1.n_inputs == g2.n_inputs

    # TODO re-use input variables instead of adding clauses on inputs equality
    for input_id in range(0, g1.n_inputs):
        input_name = 'v' + str(input_id)
        # Add clauses for input equality
        input_g1_var = g1.input_var_to_cnf_var(input_name, pool1)
        input_g2_var = g2.input_var_to_cnf_var(input_name, pool2)

        # EQ Tseyting encoding
        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    for output_id in range(len(g1.outputs)):
        # Add clause for output xor gate
        xor_gate = pool2.v_to_id("xor_" + str(output_id))
        output_code_name = 'o' + str(output_id)
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

    # Konstantin asked me to prepare a miter sample, maybe later I'll need some more
    # formula = pysat.formula.CNF(from_clauses=shared_cnf)
    # formula.to_file("miter_sample.cnf")
    # sys.exit(0)

    return shared_cnf


def post_sampling_calculations(g1, g2, test_path_left, test_path_right, res, unbalanced_nodes_left, unbalanced_nodes_right, t_start, settings):
    best_domains_left, shift = calculate_domain_saturations(
        g1, unbalanced_nodes_left, tag="L", start_from=1)
    best_domains_right, _ = calculate_domain_saturations(
        g2, unbalanced_nodes_right, tag="R", start_from=shift + 1)
    result = check_for_equivalence(
        g1, g2, best_domains_left, best_domains_right, res, settings)
    t_finish = time.time()

    time_elapsed = str(t_finish - t_start)
    res_string = "Running {} against {} took {} seconds".format(
        test_path_left, test_path_right, time_elapsed)
    res['left_schema'] = test_path_left
    res['right_schema'] = test_path_right
    res['time'] = time_elapsed
    res['outcome'] = result
    U.print_to_file(res_filename, json.dumps(res, indent=4))
    print(res_string)
    return result


def domain_equivalence_check(test_path_left, test_path_right, res_filename):
    g1 = G.Graph(test_path_left)
    g2 = G.Graph(test_path_right)

    g1.relabel_graph_in_top_to_bottom_fashion()
    g2.relabel_graph_in_top_to_bottom_fashion()

    t_start = time.time()
    res = dict()
    res['max_cartesian_size'] = MAX_CARTESIAN_PRODUCT_SIZE
    res['disbalance_threshold'] = DISBALANCE_THRESHOLD
    print("Schemas initialized, looking for unbalanced nodes in the left schema")
    unbalanced_nodes_left = find_unbalanced_gates(g1)
    print("Looking for unbalanced nodes in the right schema")
    unbalanced_nodes_right = find_unbalanced_gates(g2)
    print("Unbalanced nodes found, proceeding to building domains")

    settings = dict()
    settings['model_enumeration_enabled'] = False
    settings['domain_one_by_one_consumption'] = False
    result = post_sampling_calculations(
        g1, g2, test_path_left, test_path_right, res, unbalanced_nodes_left, unbalanced_nodes_right, t_start, settings)

    return result


def validate_naively(g1, g2):
    pool_left = FB.TPoolHolder()
    f_left = FB.make_formula_from_my_graph(g1, pool_left)

    shift = -1
    for clause in f_left.clauses:
        for var in clause:
            shift = max(shift, var)

    pool_right = FB.TPoolHolder(start_from=shift + 1)
    f_right = FB.make_formula_from_my_graph(g2, pool_right)

    final_cnf = generate_miter_scheme(
        f_left.clauses + f_right.clauses, pool_left, pool_right, g1, g2)

    with Solver(bootstrap_with=final_cnf) as solver:
        print("Running SAT-solver to determine scheme equivalency")
        result = solver.solve()
        if not result:
            print("Schemas are equivalent, UNSAT on miter scheme")
        if result:
            print("Schemas are NOT equivalent, SAT on miter scheme has been found")
        return not result


def naive_equivalence_check(test_path_left, test_path_right, res_filename):
    g1 = G.Graph(test_path_left)
    g2 = G.Graph(test_path_right)

    t1 = time.time()
    result = validate_naively(g1, g2)
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
        # ("./new_sorts/BubbleSort_4_3.aig",
        #  "./new_sorts/PancakeSort_4_3.aig",
        #  "./results/4_3.txt"
        #  ),
        # ("./sorts/BubbleSort_7_4.aig",
        #  "./sorts/BubbleSortFaulty_7_4.aig",
        #  "./results/7_4_faulty.txt"
        #  ),
        ("./new_sorts/BubbleSort_6_4.aig",
         "./new_sorts/PancakeSort_6_4.aig",
         "./results/6_4.txt"
         ),
        # ("./new_sorts/BubbleSort_7_4.aig",
        #  "./new_sorts/PancakeSort_7_4.aig",
        #  "./results/7_4.txt"
        #  ),
        # ("./new_sorts/BubbleSort_8_4.aig",
        #  "./new_sorts/PancakeSort_8_4.aig",
        #  "./results/8_4.txt"
        #  ),
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

    # max_cartesian_sizes = [10, 1000, 100000, 10000000]
    # unbalanced_thresholds = [0.02, 0.03]

    max_cartesian_sizes = [100000]
    unbalanced_thresholds = [0.03]

    for (left_schema_filename, right_schema_filename, res_filename) in experiments:
        # naive_equivalence_check(left_schema_filename,
        #                         right_schema_filename, res_filename)
        for max_cartesian_size in max_cartesian_sizes:
            for unbalanced_threshold in unbalanced_thresholds:
                MAX_CARTESIAN_PRODUCT_SIZE = max_cartesian_size
                DISBALANCE_THRESHOLD = unbalanced_threshold
                domain_equivalence_check(left_schema_filename,
                                         right_schema_filename, res_filename)

