import sys
import os
import pytest

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
import eq_checkers as EQ


def test_calculate_distance_is_symmetric():
    aig_files = [
        "./tests/test-data/small-graph-1.aag",
        "./tests/test-data/small-graph-2.aag",
        "./tests/test-data/BubbleSort_4_3.aag",
        "./tests/test-data/PancakeSort_4_3.aag",
    ]
    for aig_file in aig_files:
        g = Graph(aig_file, "L")

        # not removing identical to keep the graph
        # a little bit more complicated

        dists_from = dict()

        for node in g.node_names:
            dists_from[node] = g.calculate_dists_from(node)

        for node_1 in g.node_names:
            for node_2 in g.node_names:
                assert dists_from[node_1][node_2] == dists_from[node_2][node_1]


def test_calculate_distance_on_small_graph():
    aig_file = "./tests/test-data/small-graph-1.aag"

    g = Graph(aig_file, "L")

    dists_from = dict()

    for node in g.node_names:
        dists_from[node] = g.calculate_dists_from(node)

    assert dists_from["v0"]["a0L"] == 1
    assert dists_from["v0"]["a1L"] == 1

    assert dists_from["v0"]["a2L"] == 2
    assert dists_from["v0"]["a3L"] == 2

    assert dists_from["a2L"]["a0L"] == 1
    assert dists_from["a3L"]["a1L"] == 1
