import sys
import os
  
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph


def test_graphs_equal_after_reading_and_dumping():
    aig_file = "./tests/test-data/BubbleSort_4_3.aag"

    g = Graph(aig_file, "L")

    tmp_file = "tmp.aag"
    os.system(f"touch {tmp_file}")
    g.to_file(tmp_file)

    g1 = Graph(tmp_file, "L")
    g2 = Graph(aig_file, "R")

    os.system(f"rm {tmp_file}")

    assert g1.n_inputs == g2.n_inputs
    assert g1.n_outputs == g2.n_outputs
    for input in range(2 ** g1.n_inputs):
        outputs_1 = g1.calculate_schema_on_inputs(input)
        outputs_2 = g2.calculate_schema_on_inputs(input)
        for output_id in range(g1.n_outputs):
            name_1 = g1.output_name_to_node_name[f"o{output_id}"]
            name_2 = g2.output_name_to_node_name[f"o{output_id}"]
            assert outputs_1[name_1] == outputs_2[name_2]
