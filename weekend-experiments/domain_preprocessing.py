import random

from collections import defaultdict
from tqdm import tqdm

from pysat.solvers import Maplesat as PysatSolver

import formula_builder as FB

import hyperparameters as H


# Returns names of nodes that are unbalanced enough, based on DISBALANCE_THRESHOLD.
def find_unbalanced_gates(g):
    print("Random sampling unbalanced nodes, {} samples".format(H.RANDOM_SAMPLE_SIZE))

    random.seed(42)

    complete_input_size = range(2 ** g.n_inputs)
    random_sample = random.sample(
        complete_input_size, min(len(complete_input_size), H.RANDOM_SAMPLE_SIZE)
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
            lambda name_cnt: (name_cnt[1] / H.RANDOM_SAMPLE_SIZE, name_cnt[0]),
            had_true_on_node.items(),
        )
    )

    fractions = list(filter(lambda a: not a[1].startswith("i"), fractions))

    # filter the gates that are unbalanced enough
    unbalanced = list(
        filter(
            lambda p: p[0] < H.DISBALANCE_THRESHOLD
            or p[0] > (1 - H.DISBALANCE_THRESHOLD),
            fractions,
        )
    )

    unbalanced_gates = list(map(lambda p: p[1], unbalanced))

    buckets = [
        unbalanced_gates[x : x + H.BUCKET_SIZE]
        for x in range(0, len(unbalanced_gates), H.BUCKET_SIZE)
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
