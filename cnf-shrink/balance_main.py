import aiger
import time
import random
import itertools

from collections import defaultdict
from pysat.solvers import Minisat22
from aiger_cnf import aig2cnf

import formula_builder as FB
import graph as G

# algorithm hyperparameters
DISBALANCE_THRESHOLD = 0.03
BUCKET_SIZE = 10
MAX_CARTESIAN_PRODUCT_SIZE = 100000
RANDOM_SAMPLE_SIZE = 10000


def get_from_cnf(cnf, var):
    if var in cnf:
        return 1
    assert -1 * var in cnf
    return 0


def find_unbalanced_gates(g):
    random_sample = [[random.choice([True, False]) for t in range(
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
        gate_values_on_input = g.calculate_schema_on_inputs(input)
        for name, value in gate_values_on_input.items():
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


def run_checkup_calculation(g, domains_info):
    inputs = [0 for i in range(28)]
    inputs[0] = 1
    results = g.calculate_schema_on_inputs(inputs)

    long_checkup_domain = list()
    for (saturation, bucket, domain) in domains_info:
        cur_domain_value = 0
        for gate_id, gate_name in enumerate(bucket):
            elem = 0
            if results[gate_name]:
                elem = 1
            cur_domain_value += elem * (2 ** gate_id)
        long_checkup_domain.append(cur_domain_value)
        assert cur_domain_value in domain
    return long_checkup_domain


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


def compare(lst, tup):
    return tuple(lst) == tup


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

    checkup_value = run_checkup_calculation(g1, domains_info)

    final_cnf = generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2)
    print("Miter schema generated. Iterating over cartesian product now")

    with Minisat22(bootstrap_with=final_cnf) as solver:
        percentage = 0
        comb_id = 0
        for combination in combinations:
            if compare(checkup_value, combination):
                print(checkup_value, combination)
            comb_id += 1
            percentage_step = 0.01

            if (percentage + percentage_step) * total_combs < comb_id:
                percentage += percentage_step
                print("Combinations processed: {}%".format(
                    round(100 * percentage)))

            # list(saturation, bucket, domain)
            assumptions = list()
            for domain_id, domain_value in enumerate(combination):
                for unit_id, gate in enumerate(domains_info[domain_id][1]):
                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    assumptions.append(modifier * pool1.v_to_id(gate))
            result = solver.solve(assumptions=assumptions)

            if compare(checkup_value, combination):
                investigate_this_shit(g2, shift, assumptions, final_cnf, pool1)

            # g1 and g2 on some fixed input really give different answers.
            # now to figuring out, why miter schema is unsat.

            if result:
                print("Schemas are not equivalent, SAT on miter schema has been found")
                return
    print("Schemas are equivalent, UNSAT has been achieved on every element from cartesian join")

def investigate_this_shit(g, shift, assumptions, final_cnf, final_pool):
    pool = FB.TPoolHolder()
    formula = FB.make_formula_from_my_graph(g, pool)
    exec_1 = None

    inputs = [0 for i in range(28)]
    inputs[0] = 1
    results = g.calculate_schema_on_inputs(inputs)
    new_assumptions = list()
    for i in range(28):
        iname = 'v' + str(i)
        modifier = -1
        if inputs[i]:
            modifier = 1
        new_assumptions.append(modifier * final_pool.v_to_id(iname))

    with Minisat22(bootstrap_with=formula) as solver:
        for execution in solver.enum_models(assumptions=new_assumptions):
            exec_1 = execution

    for i in range(28):
        o_name = 'o' + str(i)
        var_name = g.output_name_to_node_name[o_name]
        cnf_name = g.output_var_to_cnf_var(o_name, pool)
        # print(cnf_name)

        print("Graph: {}, CNF: {}".format(
            results[var_name], get_from_cnf(exec_1, cnf_name)))

    print("Trying to solve miter with assumptions on inputs")
    with Minisat22(bootstrap_with=final_cnf) as solver_final:
        res = solver_final.solve(assumptions=new_assumptions)
        if res:
            print("Yes, I've broken this Miter scheme")
        else:
            print("Nah. Miter scheme still gives UNSAT")



def generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2):
    assert g1.n_inputs == g2.n_inputs
    for input_id in range(0, g1.n_inputs):
        input_name = 'v' + str(input_id)
        # Add clause for input equality
        input_g1_var = g1.input_var_to_cnf_var(input_name, pool1)
        input_g2_var = g2.input_var_to_cnf_var(input_name, pool2)

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


def domain_equivalence_check(test_path_left, test_path_right):
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


def validate_against_aig(g, aig):
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
        # Add clause for input equality
        input_aig_var = start_cnf.input2lit[input]
        input_graph_var = g.input_var_to_cnf_var(input, pool)

        final_cnf.append([-1 * input_aig_var, input_graph_var])
        final_cnf.append([input_aig_var, -1 * input_graph_var])

    for i, output in enumerate(aig.outputs):
        # Add clause for output xor gate
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

    # Finally, check the formula for SAT\UNSAT
    with Minisat22(bootstrap_with=final_cnf) as solver:
        print("Running SAT-solver to determine scheme equivalency")
        result = solver.solve()
        if not result:
            print("Hoorah, UNSAT means schemes are equivalent")
        if result:
            print("Your schema is non-equivalent to the source schema :(")


def naive_equivalence_check(test_path_left, test_path_right):
    aig_instance_left = aiger.load(test_path_left)
    aig_instance_right = aiger.load(test_path_right)

    g1 = G.Graph()
    g1.from_aig(aig_instance_left)
    t1 = time.time()
    validate_against_aig(g1, aig_instance_right)
    t2 = time.time()
    print("Running", test_path_left, test_path_right, "took", str(t2 - t1))


def get_outputs_on(g, inputs):
    raw_outputs = g.calculate_schema_on_inputs(inputs)
    named_outputs = []
    for i in range(28):
        named_outputs.append(
            raw_outputs[g.output_name_to_node_name['o' + str(i)]])
    return named_outputs


# Launch this function to make sure the schemas really differ on some very simple input.
def manual_nonequivalence_example():
    left_schema = aiger.load("./sorts/BubbleSortFaulty_7_4.aig")
    right_schema = aiger.load("./sorts/BubbleSort_7_4.aig")

    g1 = G.Graph()
    g1.from_aig(left_schema)
    g2 = G.Graph()
    g2.from_aig(right_schema)

    inputs = [0 for i in range(28)]
    inputs[0] = 1

    outputs_left = get_outputs_on(g1, inputs)
    outputs_right = get_outputs_on(g2, inputs)
    print(outputs_left)
    print(outputs_right)


if __name__ == "__main__":
    # manual_nonequivalence_example()
    # domain_equivalence_check("./sorts/BubbleSort_7_4.aig", "./sorts/BubbleSortFaulty_7_4.aig")
    naive_equivalence_check("./sorts/BubbleSortFaulty_7_4.aig", "./sorts/BubbleSort_7_4.aig")
