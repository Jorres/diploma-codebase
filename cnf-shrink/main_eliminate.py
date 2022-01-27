import time
import random
import json
import os

from tqdm import tqdm

import graph as G

import main_equivalence as EQ
import pair_eliminator as PE
import utils as U


def optimize_graph(test_folder, test_name, result_folder, result_file):
    test_path = f"{test_folder}/{test_name}"
    print(f"Optimizing {test_path=}")
    g1 = G.Graph(test_path)
    g2 = G.Graph(test_path)

    pair_elim = PE.PairEliminator()
    t1 = time.time()
    g1_pruned, pruned_gates = pair_elim.try_prune_all_pairs(g1)
    # g1_pruned = g1
    # pruned_gates = U.PrunedGates(0, 0)
    total_pruned = pruned_gates.ands + pruned_gates.nots
    t2 = time.time()

    assert len(g1_pruned.outputs) == len(g2.outputs)
    assert g1_pruned.n_inputs == g2.n_inputs
    assert len(g1_pruned.node_names) == len(g2.node_names) - total_pruned

    complete_input_range = range(2 ** g1.n_inputs)
    actual_sample_size = min(len(complete_input_range), 10 ** 4)
    random_sample = random.sample(complete_input_range, actual_sample_size)

    for i in tqdm(random_sample, total=actual_sample_size, leave=False):
        outputs_left = g1_pruned.calculate_schema_on_inputs(i)
        outputs_right = g2.calculate_schema_on_inputs(i)
        for output_id in range(len(g2.outputs)):
            output_name = 'o' + str(output_id)
            value_left = outputs_left[g1_pruned.output_name_to_node_name[output_name]]
            value_right = outputs_right[g2.output_name_to_node_name[output_name]]
            assert value_left == value_right

    cur_result = dict()
    cur_result['name'] = test_path
    cur_result['total_pruned'] = total_pruned
    cur_result['pruned_ands'] = pruned_gates.ands
    cur_result['pruned_nots'] = pruned_gates.nots
    cur_result['graph_size'] = len(g1.node_names)
    cur_result['validated'] = EQ.validate_naively(g1_pruned, g2)
    cur_result['time_elapsed'] = str(t2 - t1)

    with open(f"{result_folder}/{result_file}", "a") as f:
        f.write(json.dumps(cur_result, indent=4) + "\n")

    optimized_graph_target_filename = f"{result_folder}/{test_name[:-4]}_optimized.aag"
    g1_pruned.to_file(optimized_graph_target_filename)


def run_on_iscas():
    iscas_instances = []

    for dirpath, dnames, fnames in os.walk("./iscas_aags/"):
        for f in fnames:
            test_path = "./iscas_aags/{}".format(f)
            try:
                g = G.Graph(test_path)
                l = len(g.node_names)
                iscas_instances.append((l, "iscas_aags", f))
            except Exception:
                pass

    for _, test_folder, test_name in sorted(iscas_instances):
        optimize_graph(test_folder, test_name,
                       "elim_results", "iscas_results.txt")


def run_on_sorts():
    experiments = [
        # "Sort_4_3.aig",
        # "Sort_6_4.aig",
        # "Sort_7_4.aig",
        "Sort_8_4.aig",
        # "Sort_8_5.aig",
        # "Sort_8_6.aig",
        # "Sort_8_7.aig",
        # "Sort_9_4.aig",
        # "Sort_10_4.aig"
    ]

    for test_suff in experiments:
        for kind in ["Bubble", "Pancake"]:
            test_name = kind + test_suff
            optimize_graph("new_sorts", test_name,
                           "elim_results", "results.txt")


def run_on_satencodings():
    complex_experiments = [
        "multiplier.aag",
        # "tresh.aag",
        # "A5_1.aag"
    ]

    for test_name in complex_experiments:
        optimize_graph("complex_examples", test_name,
                       "elim_results", "special_results.txt")


def main():
    # run_on_iscas()
    # run_on_satencodings()
    run_on_sorts()


if __name__ == "__main__":
    main()
