import aiger
import time
import random
import itertools

from collections import defaultdict
from pysat.solvers import Minisat22

import formula_builder as FB
import graph as G

# algorithm hyperparameters
DISBALANCE_THRESHOLD = 0.03
BUCKET_SIZE = 10
MAX_CARTESIAN_PRODUCT_SIZE = 100000
RANDOM_SAMPLE_SIZE = 10000


def find_unbalanced_gates(g):
    random_sample = [[random.choice([True, False])for t in range(
        g.n_inputs)] for i in range(RANDOM_SAMPLE_SIZE)]

    print("Random sampling unbalanced nodes, {} samples".format(RANDOM_SAMPLE_SIZE))
    had_true_on_node = defaultdict(int)

    percentage = 0
    for i, input in enumerate(random_sample):
        percentage_step = 0.05
        if (percentage + percentage_step) * RANDOM_SAMPLE_SIZE < i:
            percentage += percentage_step
            print("Random sampling unbalanced nodes: {}% done".format(
                round(percentage * 100)))
        data = g.calculate_schema_on_inputs(input)
        for name, value in data.items():
            if value:
                had_true_on_node[name] += 1

    # list(saturation, node_name)
    fractions = list(map(lambda name_cnt: (name_cnt[1] / RANDOM_SAMPLE_SIZE, name_cnt[0]),
                         had_true_on_node.items()))

    # list(saturation, node_name)
    thresholded_unbalanced = list(filter(
        lambda p: p[0] < DISBALANCE_THRESHOLD or p[0] > (1 - DISBALANCE_THRESHOLD), fractions))

    # list(node_name)
    unbalanced_nodes = list(map(lambda p: p[1], thresholded_unbalanced))
    return unbalanced_nodes


def calculate_domain_saturations(g, unbalanced_nodes):
    print("Total unbalanced nodes selected: ", len(unbalanced_nodes))

    buckets = [unbalanced_nodes[x:x+BUCKET_SIZE]
               for x in range(0, len(unbalanced_nodes), BUCKET_SIZE)]
    print("Total domains to be built with size {}: {}".format(
        BUCKET_SIZE, len(buckets)))

    domains = list()

    pool = FB.TPoolHolder()
    formula = FB.make_formula_from_my_graph(g, pool)

    with Minisat22(bootstrap_with=formula.clauses) as solver:
        percentage = 0
        for bucket_id, bucket in enumerate(buckets):
            percentage_step = 0.01
            if (percentage + percentage_step) * len(buckets) < bucket_id:
                percentage += percentage_step
                print("Processing buckets: {}%".format(round(percentage * 100)))
            domain = list()

            cur_bucket_size = len(bucket)
            for i in range(0, 2 ** cur_bucket_size):
                assumptions = list()
                for unit_id in range(0, cur_bucket_size):
                    if (i & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    assumptions.append(
                        modifier * pool.v_to_id(bucket[unit_id]))

                if solver.solve(assumptions=assumptions):
                    domain.append(i)

            domains.append((bucket, domain))
    # domains: list(bucket (list of gates), domain (list of possible values))

    # list(saturation, bucket, domain)
    domains_with_saturation = map(lambda p: (len(p[1]) / (2 ** len(p[0])),
                                             p[0], p[1]), domains)
    sorted_domains = sorted(list(domains_with_saturation))

    print("Ten first domains:")
    for i, (saturation, bucket, domain) in enumerate(sorted_domains[:10]):
        print("Domain {}, domain size {}, saturation {} / 1".format(i,
              len(domain), len(domain) / (2 ** len(bucket))))

    cartesian_size = 1
    best_domains = list()
    i = 0
    while i < len(sorted_domains) and cartesian_size * len(sorted_domains[i][2]) < MAX_CARTESIAN_PRODUCT_SIZE:
        best_domains.append(sorted_domains[i])
        cartesian_size *= len(sorted_domains[i][2])
        i += 1
    return best_domains


def check_for_equivalence(g1, g2, domains_info):
    domains_only = list(map(lambda d: d[2], domains_info))
    combinations = itertools.product(*domains_only)

    total_combs = 1
    for v in map(lambda x: len(x), domains_only):
        total_combs *= v
    print("Total size of cartesian product of the domains:", total_combs)

    pool1 = FB.TPoolHolder()
    f1 = FB.make_formula_from_my_graph(g1, pool1)

    # Here we solve the problem of clashing names by separating pools.
    # Therefore, 'v123' in the first pool will have a different id
    # then a 'v123' in the second. It would be better to handle collisions
    # on 'Graph' class level, for instance by generating some prefix to all names,
    # but that would require some significant refactoring. Therefore I just use
    # two pool instances. TODO later.

    shift = -1
    for clause in f1.clauses:
        for var in clause:
            shift = max(shift, abs(var))

    pool2 = FB.TPoolHolder(start_from=shift + 1)
    f2 = FB.make_formula_from_my_graph(g2, pool2)
    shared_cnf = f1.clauses + f2.clauses

    final_cnf = generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2)
    print("Miter schema generated. Iterating over cartesian product now")

    with Minisat22(bootstrap_with=final_cnf) as solver:
        percentage = 0
        comb_id = 0
        for combination in combinations:
            comb_id += 1
            percentage_step = 0.01

            if (percentage + percentage_step) * total_combs < comb_id:
                percentage += percentage_step
                print("Combinations processed: {}%".format(
                    round(100 * percentage)))

            assumptions = list()
            for domain_id, domain_value in enumerate(combination):
                for unit_id, gate in enumerate(domains_info[domain_id][1]):
                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    assumptions.append(modifier * pool1.v_to_id(gate))
            result = solver.solve(assumptions=assumptions)
            if result:
                print("Schemas are not equivalent, SAT on miter schema has been found")
                return
    print("Schemas are equivalent, UNSAT has been achieved on every element from cartesian join")


def generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2):
    for input_id in range(0, g1.n_inputs):
        input_name = 'v' + str(input_id)
        # Add clause for input equality
        input_g1_var = g1.input_var_to_cnf_var(input_name, pool1)
        input_g2_var = g2.input_var_to_cnf_var(input_name, pool2)

        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    for output_id, output_node_name in enumerate(g1.outputs):
        # Add clause for output xor gate
        c = pool2.v_to_id("xor_" + str(output_id))
        output_code_name = 'o' + str(output_id)
        a = g1.output_var_to_cnf_var(output_code_name, pool1)
        b = g2.output_var_to_cnf_var(output_code_name, pool2)
        shared_cnf.append([-1 * a, -1 * b, -1 * c])
        shared_cnf.append([a, b, -1 * c])
        shared_cnf.append([a, -1 * b, c])
        shared_cnf.append([-1 * a, b, c])

    # OR together all new xor_ variables
    lst = []
    for i in range(len(g1.outputs)):
        lst.append(pool2.v_to_id("xor_" + str(output_id)))
    shared_cnf.append(lst)
    return shared_cnf


def domain_eqivalence_check(test_path_left, test_path_right):
    left_schema = aiger.load(test_path_left)
    right_schema = aiger.load(test_path_right)
    g1 = G.Graph()
    g1.from_aig(left_schema)
    g2 = G.Graph()
    g2.from_aig(right_schema)
    t1 = time.time()
    print("Graph built, looking for unbalanced nodes")
    unbalanced_nodes = find_unbalanced_gates(g1)
    print("Unbalanced nodes found")
    best_domains = calculate_domain_saturations(g1, unbalanced_nodes)
    check_for_equivalence(g1, g2, best_domains)
    t2 = time.time()
    print("Running", test_path_left, "against",
          test_path_right, "took", str(t2 - t1), "seconds")


def get_outputs_on(g, inputs):
    raw_outputs = g.calculate_schema_on_inputs(inputs)
    named_outputs = []
    for i in range(28):
        named_outputs.append(
            raw_outputs[g.output_name_to_node_name['o' + str(i)]])
    return named_outputs


def validate_graph_building():
    left_schema = aiger.load("./sorts/BubbleSortFaulty_7_4.aig")
    right_schema = aiger.load("./sorts/BubbleSort_7_4.aig")

    g1 = G.Graph()
    g1.from_aig(left_schema)
    g2 = G.Graph()
    g2.from_aig(right_schema)

    inputs = [0 for i in range(28)]
    inputs[0] = 1
    print(g1.outputs)
    print(g2.outputs)
    outputs_left = get_outputs_on(g1, inputs)
    outputs_right = get_outputs_on(g2, inputs)
    print(outputs_left)
    print(outputs_right)


if __name__ == "__main__":
    # validate_graph_building()
    domain_eqivalence_check("./sorts/BubbleSort_7_4.aig",
                            "./sorts/BubbleSortFaulty_7_4.aig")
