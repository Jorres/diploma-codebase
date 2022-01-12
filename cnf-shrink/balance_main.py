import aiger
import formula_builder as FB
import graph as G

import pysat
import time
import random
import sys

import itertools

from collections import defaultdict

from pysat.solvers import Minisat22
from aiger_cnf import aig2cnf

logging_enabled = True


def mylog(*args):
    global logging_enabled
    if logging_enabled:
        print(*args)


def find_unbalanced(g):
    random_sample_size = 10000

    random_sample = [[random.choice([True, False])for t in range(
        g.inputs)] for i in range(random_sample_size)]

    mylog("Random sampling unbalanced nodes, {} samples".format(random_sample_size))
    had_true_on_node = defaultdict(int)
    percentage = 0
    for i, input in enumerate(random_sample):
        percentage_step = 0.05
        if (percentage + percentage_step) * random_sample_size < i:
            percentage += percentage_step
            sys.stdout.write("\rRandom sampling unbalanced nodes: {}% done".format(round(percentage * 100)))
            sys.stdout.flush()

        data = g.calculate_schema_on_inputs(input)
        for name, value in data.items():
            if value:
                had_true_on_node[name] += 1

    fractions = list(map(lambda name_cnt: (name_cnt[1] / random_sample_size, name_cnt[0]),
                         had_true_on_node.items()))

    unbalancedness_threshold = 0.03
    thresholded_unbalanced = list(filter(
        lambda p: p[0] < unbalancedness_threshold or p[0] > (1 - unbalancedness_threshold), fractions))

    # random.shuffle(thresholded_unbalanced)

    unbalanced_nodes = list(map(lambda p: p[1], thresholded_unbalanced))
    return unbalanced_nodes


def calculate_domains(g, unbalanced_nodes):
    mylog("Total unbalanced nodes selected: ", len(unbalanced_nodes))
    chunk_size = 10
    chunks = [unbalanced_nodes[x:x+chunk_size]
              for x in range(0, len(unbalanced_nodes), chunk_size)]
    mylog("Total domains to be built with size {}: {}".format(chunk_size, len(chunks)))
    domains = list()

    pool = FB.TPoolHolder()
    formula = FB.make_formula_from_my_graph(g, pool)
    with Minisat22(bootstrap_with=formula.clauses) as solver:
        percentage = 0
        for chunk_id, chunk in enumerate(chunks):
            percentage_step = 0.01
            if (percentage + percentage_step) * len(chunks) < chunk_id:
                percentage += percentage_step
                sys.stdout.write("\rProcessing chunks: {}%".format(round(percentage * 100)))
                sys.stdout.flush()
            domain = list()

            cur_chunk_size = len(chunk)
            for i in range(0, 2 ** cur_chunk_size):
                assumptions = list()
                for unit_id in range(0, cur_chunk_size):
                    if (i & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    assumptions.append(
                        modifier * pool.v_to_id(chunk[unit_id]))

                if solver.solve(assumptions=assumptions):
                    domain.append(i)

            domains.append((chunk, domain))

    domains_with_saturation = map(lambda p: (len(p[1]) / (2 ** len(p[0])),
                                             p[0], p[1]), domains)
    best_domains = sorted(list(domains_with_saturation))

    mylog("Ten first domains:")
    for i, (saturation, gate_names, domain) in enumerate(best_domains[:10]):
        mylog("Domain {}, domain size {}, saturation {} / 1".format(i,
              len(domain), len(domain) / (2 ** len(gate_names))))

    cartesian_size = 1
    limited_domains = list()
    i = 0
    while i < len(best_domains) and cartesian_size * len(best_domains[i][2]) < 100000:
        limited_domains.append(best_domains[i])
        cartesian_size *= len(best_domains[i][2])
        i += 1
    return limited_domains

# ideas
# there may be massive gains from optimizing hyperparameters (how 'empty' the domains
# should be, the length of a chunk (tradeoff between calculating domains and actually
# solving SAT instances))


def check_for_equivalence(g1, g2, domains_info):
    domains_only = list(map(lambda d: d[2], domains_info))
    combinations = itertools.product(*domains_only)

    total_combs = 1
    for v in map(lambda x: len(x), domains_only):
        total_combs *= v
    mylog("Total size of cartesian product of the domains:", total_combs)

    pool1 = FB.TPoolHolder()
    f1 = FB.make_formula_from_my_graph(g1, pool1)

    # Here we solve the problem of clashing names by separating pools.
    # Therefore, 'v123' in the first pool will have a different id
    # then a 'v123' in the second. It would be better to handle collisions
    # on 'Graph' class level, for instance by generating some prefix to all names,
    # but that would require some significant refactoring. TODO later.
    shift = -1
    for clause in f1.clauses:
        for var in clause:
            shift = max(shift, var)
    pool2 = FB.TPoolHolder(start_from=shift + 1)
    f2 = FB.make_formula_from_my_graph(g2, pool2)
    shared_cnf = f1.clauses + f2.clauses

    final_cnf = generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2)
    mylog("Miter schema generated. Iterating over cartesian product now")

    with Minisat22(bootstrap_with=final_cnf) as solver:
        percentage = 0
        comb_id = 0
        for combination in combinations:
            sys.stdout.write("\rProcessing cartesian product element number %i" % comb_id)
            sys.stdout.flush()
            comb_id += 1
            percentage_step = 0.01
            if (percentage + percentage_step) * total_combs < comb_id:
                percentage += percentage_step
                mylog("Combinations: {}%".format(round(percentage * 100)))
            assumptions = list()
            for domain_id, domain_value in enumerate(combination):
                for unit_id, gate in enumerate(domains_info[domain_id][1]):
                    if (domain_value & (1 << unit_id)) > 0:
                        modifier = 1
                    else:
                        modifier = -1
                    assumptions.append(modifier * pool2.v_to_id(gate))
            result = solver.solve(assumptions=assumptions)
            if result:
                print("Schemas are not equivalent, SAT on miter scheme has been found")
                return
    print("Schemas are equivalent, UNSAT has been achieved on every element from cartesian join")


def generate_miter_scheme(shared_cnf, pool1, pool2, g1, g2):
    for input_id in range(0, g1.inputs):
        input_name = 'v' + str(input_id)
        # Add clause for input equality
        input_g1_var = g1.what_input_var(input_name, pool1)
        input_g2_var = g2.what_input_var(input_name, pool2)

        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    for output_id, output_node_name in enumerate(g1.outputs):
        # Add clause for output xor gate
        c = pool2.v_to_id("xor_" + str(output_id))
        output_code_name = 'o' + str(output_id)
        a = g1.what_output_var(output_code_name, pool1)
        b = g2.what_output_var(output_code_name, pool2)
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


# TODO finally, launch measurement. On BubbleSort, for starters.

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
        input_graph_var = g.what_input_var(input, pool)

        final_cnf.append([-1 * input_aig_var, input_graph_var])
        final_cnf.append([input_aig_var, -1 * input_graph_var])

    for i, output in enumerate(aig.outputs):
        # Add clause for output xor gate
        c = pool.v_to_id("xor_" + str(i))
        a = start_cnf.output2lit[output]
        b = g.what_output_var(output, pool)
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


def run_test_for(test_path):
    aig_instance = aiger.load(test_path)

    g1 = G.Graph()
    g1.from_aig(aig_instance)
    t1 = time.time()
    validate_against_aig(g1, aig_instance)
    t2 = time.time()
    print("Running", test_path, "took", str(t2 - t1))


if __name__ == "__main__":
    # run_test_for("./sorts/PancakeSort_10_8.aig")
    # run_test_for("./sorts/InsertSort_10_8.aig")
    # run_test_for("./sorts/BubbleSort_10_8.aig")
    # run_test_for("./sorts/PancakeSort_7_4.aig")
    # run_test_for("./sorts/InsertSort_7_4.aig")
    # run_test_for("./sorts/BubbleSort_7_4.aig")

    test_path = "./sorts/BubbleSort_7_4.aig"
    aig_instance = aiger.load(test_path)
    g1 = G.Graph()
    g1.from_aig(aig_instance)
    g2 = G.Graph()
    g2.from_aig(aig_instance)
    t1 = time.time()
    mylog("Graph built")
    mylog("Looking for unbalanced nodes")
    unbalanced_nodes = find_unbalanced(g1)
    mylog("Unbalanced nodes found")
    # for i in range(0, 3):
    #     random.shuffle(unbalanced_nodes)
    best_domains = calculate_domains(g1, unbalanced_nodes)
    check_for_equivalence(g1, g2, best_domains)
    t2 = time.time()
    print("Running", test_path, "took", str(t2 - t1))


# I also should notice that decreasing random sample size
# could provide more than twice the speedup.

# chunk size 12 is somewhat difficult already, and the slowdown
# is quite steep

# All times in seconds unless specified otherwise.
#
# Sorting | size  | graph-size | naive-time | domain-time
# Insert  | large | 6997       | N/A        | estimated 2 days
# Insert  | small | 1522       | 13         | 10
# Bubble  | large | ~8200      | 1940       | 180
# Bubble  | small | 1694       | 37         | 12
# Pancake | large | ~31000     | > 14h, N/A | 1440
# Pancake | small | 5054       | 553        | 52
#
# N/A == did not finish, aborted
# Large means 10 * 8 = 80 inputs
# Small means 7  * 4 = 28 inputs
