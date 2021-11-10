import json
import sys
import pysat.formula
from pysat.solvers import Lingeling
from collections import defaultdict

import helpers as H
import validator as V


def not_equal(char, ids, bit):
    if bit == 1:
        return -1 * H.v_to_id(char, ids)
    else:
        return H.v_to_id(char, ids)


def check_truth_table_bit(n, i, k, j, t, formula):
    for a in range(0, 2):
        for b in range(0, 2):
            for c in range(0, 2):
                lst = [
                    -1 * H.v_to_id("s", [i, j, k]),

                    not_equal("x", [i, t], a),

                    not_equal("f", [i, b, c], 1 - a)
                ]

                if j <= n:
                    if H.nth_bit_of(t, j) != b:
                        continue
                else:
                    lst.append(not_equal("x", [j, t], b))

                if k <= n:
                    if H.nth_bit_of(t, k) != c:
                        continue
                else:
                    lst.append(not_equal("x", [k, t], c))

                formula.append(lst)


def construct_formula(f_truthtables, n, m, r):
    formula = pysat.formula.CNF()

    new_nodes = range(n + 1, n + r + 1)
    truth_table = range(0, 2 ** n)

    # Output vertices are equal to truth table's rows
    for h in range(1, m + 1):
        for i in new_nodes:
            for t in truth_table:
                # [0, 1] to [-1, 1]
                modifier = f_truthtables[h][t] * 2 - 1
                formula.append([
                    -1 * H.v_to_id("g", [h, i]),
                    modifier * H.v_to_id("x", [i, t])
                ])

    # Every output exists somewhere in the chain
    for h in range(1, m + 1):
        formula.append([H.v_to_id("g", [h, i])
                        for i in new_nodes])

    # Every step has exactly two inputs
    for i in new_nodes:
        lst = []
        for k in range(1, i):
            for j in range(1, k):
                lst.append(H.v_to_id("s", [i, j, k]))
        formula.append(lst)

    # Main clause, check truth table correspondense
    for i in new_nodes:
        for k in range(1, i):
            for j in range(1, k):
                for t in truth_table:
                    check_truth_table_bit(n, i, k, j, t, formula)

    H.pretty_print_formula(formula)
    return formula


def read_tables(filename):
    f = open(filename, "r")
    lines = f.readlines()
    f.close()

    f_truthtables = defaultdict(dict)

    n, m = map(int, lines[0].split(" "))

    curline = 2
    for i in range(0, m):
        for j in range(0, 2 ** n):
            ith_fun_jth_bit = int(lines[curline])
            f_truthtables[i + 1][j] = ith_fun_jth_bit
            curline = curline + 1
        curline = curline + 1

    return n, m, f_truthtables


def try_solve(formula):
    with Lingeling(bootstrap_with=formula.clauses, with_proof=True) as ling:
        solution_exists = ling.solve()
        if solution_exists is False:
            print(ling.get_proof())
        return solution_exists, ling.get_model()


def interpret_as_graph(r, model):
    print("The schema consists of", r, "additional nodes")

    gr = dict()
    f_to_node = dict()

    node_truthtables = defaultdict(lambda: defaultdict(dict))

    for variable in model:
        key = json.loads(H.id_to_v(abs(variable)))

        if key['char'] == "g":
            if variable > 0:
                h, i = key['ids']
                f_to_node[h] = i
                print("Output", h, "is located at vertex", i)

        if key['char'] == "f":
            i, p, q = key['ids']
            result = variable > 0
            node_truthtables[i][p][q] = result
            print("Vertex", i, "produces from", p, q,
                  "value", result)

        if key['char'] == "s":
            i, j, k = key['ids']
            if variable > 0:
                gr[i] = (j, k)
                print("Vertex", i, "is calculated from", j, k)

    return gr, f_to_node, node_truthtables


def main():
    schema_size = sys.argv[1]
    truth_tables_file = sys.argv[2]

    n, m, f_truthtables = read_tables(truth_tables_file)

    found_scheme_size = -1
    for cur_size in range(1, int(schema_size)):
        formula = construct_formula(f_truthtables, n, m, cur_size)
        solved, model = try_solve(formula)
        if solved:
            found_scheme_size = cur_size
            break

    if found_scheme_size == -1:
        print("No solution with schema size up to", schema_size)
        return

    gr, f_to_node, node_truthtables = interpret_as_graph(cur_size, model)
    V.validate(gr, f_to_node, f_truthtables,
               node_truthtables, n, m, found_scheme_size)


main()
