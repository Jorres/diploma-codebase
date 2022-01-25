import time
import json
from tqdm import tqdm

import formula_builder as FB
import graph as G

import main_equivalence as EQ
import pair_eliminator as PE


def main():
    experiments = [
        "Sort_4_3.aig",
        "Sort_6_4.aig",
        "Sort_6_4.aig",
        "Sort_7_4.aig",
        "Sort_8_4.aig",
        "Sort_8_5.aig",
        "Sort_8_6.aig",
        "Sort_8_7.aig",
        "Sort_9_4.aig",
        "Sort_10_4.aig"
    ]

    complex_experiments = [
        "multiplier.aag",
        "tresh.aag",
        "A5_1.aag"
    ]

    # for test_suff in experiments:
    #     for kind in ["Pancake", "Bubble"]:
    #         test_path = "./new_sorts/{}{}".format(kind, test_suff)
    #         g1 = G.Graph(test_path)
    #         g2 = G.Graph(test_path)

    #         pair_elim = PE.PairEliminator()
    #         t1 = time.time()
    #         g1_pruned, total_pruned = pair_elim.try_prune_all_pairs(g1)
    #         t2 = time.time()

    #         assert len(g1_pruned.outputs) == len(g2.outputs)
    #         assert g1_pruned.n_inputs == g2.n_inputs
    #         assert len(g1_pruned.node_names) == len(g2.node_names) - total_pruned

    #         if 2 ** g2.n_inputs < 10 ** 6:
    #             for i in tqdm(range(2 ** g2.n_inputs), leave=False):
    #                 outputs_left = g1_pruned.calculate_schema_on_inputs(i)
    #                 outputs_right = g2.calculate_schema_on_inputs(i)
    #                 for output_id in range(len(g2.outputs)):
    #                     output_name = 'o' + str(output_id)
    #                     value_left = outputs_left[g1_pruned.output_name_to_node_name[output_name]]
    #                     value_right = outputs_right[g2.output_name_to_node_name[output_name]]
    #                     assert value_left == value_right

    #         cur_result = dict()
    #         cur_result['name'] = test_path
    #         cur_result['pruned'] = total_pruned
    #         cur_result['graph_size'] = len(g1.node_names)
    #         cur_result['validated'] = EQ.validate_naively(g1_pruned, g2)
    #         cur_result['time_elapsed'] = str(t2 - t1)

    #         with open("./elim_results/results.txt", "a") as f:
    #             f.write(json.dumps(cur_result, indent=4) + "\n")
    for test_suff in complex_experiments:
        test_path = "./complex_examples/{}".format(test_suff)
        g1 = G.Graph(test_path)
        g2 = G.Graph(test_path)

        pair_elim = PE.PairEliminator()
        t1 = time.time()
        g1_pruned, total_pruned = pair_elim.try_prune_all_pairs(g1)
        t2 = time.time()

        assert len(g1_pruned.outputs) == len(g2.outputs)
        assert g1_pruned.n_inputs == g2.n_inputs
        assert len(g1_pruned.node_names) == len(g2.node_names) - total_pruned

        if 2 ** g2.n_inputs < 10 ** 6:
            for i in tqdm(range(2 ** g2.n_inputs), leave=False):
                outputs_left = g1_pruned.calculate_schema_on_inputs(i)
                outputs_right = g2.calculate_schema_on_inputs(i)
                for output_id in range(len(g2.outputs)):
                    output_name = 'o' + str(output_id)
                    value_left = outputs_left[g1_pruned.output_name_to_node_name[output_name]]
                    value_right = outputs_right[g2.output_name_to_node_name[output_name]]
                    assert value_left == value_right

        cur_result = dict()
        cur_result['name'] = test_path
        cur_result['pruned'] = total_pruned
        cur_result['graph_size'] = len(g1.node_names)
        cur_result['validated'] = EQ.validate_naively(g1_pruned, g2)
        cur_result['time_elapsed'] = str(t2 - t1)

        with open("./elim_results/special_results.txt", "a") as f:
            f.write(json.dumps(cur_result, indent=4) + "\n")


if __name__ == "__main__":
    main()
