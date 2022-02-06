import sys
import os
import pytest

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
import eq_checkers as EQ


@pytest.mark.long
def test_two_schemas_equivalent_naively():
    tests = ["4_3", "6_4"]

    for test_shortname in tests:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        g1 = Graph(left_schema_file, "L")
        g2 = Graph(right_schema_file, "R")
        g1.remove_identical()
        g2.remove_identical()

        assert EQ.validate_naively(g1, g2)
