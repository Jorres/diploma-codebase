import sys
import os
import pytest

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from graph import Graph
import eq_checkers as EQ


def test_two_schemas_equivalent_naively():
    tests = ["4_3"]

    for test_shortname in tests:
        left_schema_name = f"BubbleSort_{test_shortname}"
        right_schema_name = f"PancakeSort_{test_shortname}"

        left_schema_file = f"./hard-instances/{left_schema_name}.aag"
        right_schema_file = f"./hard-instances/{right_schema_name}.aag"

        g1 = Graph(left_schema_file, "L")
        g2 = Graph(right_schema_file, "R")
        assert EQ.validate_naively(g1, g2)
        assert EQ.validate_with_open_xors(g1, g2)
        assert EQ.validate_naively_stairs(g1, g2)


def test_schema_not_equivalent_to_faulty_variant():
    tests = ["BubbleSort_4_3", "PancakeSort_4_3"]

    for test in tests:
        left_schema_name = test
        right_schema_name = f"{test}_faulty"

        left_schema_file = f"./tests/test-data/{left_schema_name}.aag"
        right_schema_file = f"./tests/test-data/{right_schema_name}.aag"

        g1 = Graph(left_schema_file, "L")
        g2 = Graph(right_schema_file, "R")

        assert not EQ.validate_naively(g1, g2)
        assert not EQ.validate_with_open_xors(g1, g2)
        assert not EQ.validate_naively_stairs(g1, g2)
