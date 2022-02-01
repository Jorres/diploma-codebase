from graph import Graph
import os


def test_read_large_aig():
    # aig_file = "./test-data/PancakeSort_4_3.aag"

    # lines_before = open(aig_file, "r").readlines()

    # g = Graph(aig_file)

    # tmp_file = "tmp.aag"
    # os.system(f"touch {tmp_file}")

    # g.to_file(tmp_file)

    # lines_after = open(tmp_file, "r").readlines()

    # os.system(f"rm {tmp_file}")

    # # first lines about inputs and outputs should be identical
    # for line_id in range(len(lines_before)):
    #     if line_id < 1 + g.n_inputs + g.n_outputs:
    #         assert lines_before[line_id] == lines_after[line_id]

    # # lines about ands could follow in any order
    # # lexicographic or topological
    # assert set(lines_before) == set(lines_after)
    pass

def test_remove_identical_small_graph_ands():
    aig_file = "./test-data/small-graph-1.aag"

    g = Graph(aig_file, "L")
    nodes_before = len(g.node_names)
    assert nodes_before == 6

    g.remove_identical()
    nodes_after_1 = len(g.node_names)
    assert nodes_after_1 == 3

    nodes_after_2 = len(g.node_names)
    assert nodes_after_2 == 3


def test_remove_identical_small_graph_nots():
    aig_file = "./test-data/small-graph-2.aag"

    g = Graph(aig_file, "L")
    nodes_before = len(g.node_names)
    assert nodes_before == 6

    g.remove_identical()
    nodes_after_1 = len(g.node_names)
    assert nodes_after_1 == 4

    nodes_after_2 = len(g.node_names)
    assert nodes_after_2 == 4


def test_remove_identical_should_remove_all_at_once():
    aig_files = ["./test-data/BubbleSort_4_3.aag", "./test-data/PancakeSort_4_3.aag"]
    for aig_file in aig_files:
        g = Graph(aig_file, "L")
        nodes_before = len(g.node_names)
        g.remove_identical()
        nodes_after_1 = len(g.node_names)
        assert nodes_before >= nodes_after_1
        nodes_after_2 = len(g.node_names)
        assert nodes_after_1 == nodes_after_2
