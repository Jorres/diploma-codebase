import json
import sys
import pysat.formula
import random
import time

# from pysat.solvers import Lingeling
from pysat.solvers import Minisat22
from collections import defaultdict
from threading import Timer

import helpers as H
import validator as V


def interrupt(s):
    s.interrupt()


class TSchemaGenerator():
    def __init__(self, should_pretty_print, should_limit_time=True):
        self.pool = H.TPoolHolder()
        self.limit_time = should_limit_time
        self.pretty_print = should_pretty_print

    def not_equal(self, char, ids, bit):
        if bit == 1:
            return -1 * self.pool.v_to_id(char, ids)
        else:
            return self.pool.v_to_id(char, ids)

    def check_truth_table_bit(self, n, i, k, j, t, formula):
        for a in range(0, 2):
            for b in range(0, 2):
                for c in range(0, 2):
                    lst = [
                        -1 * self.pool.v_to_id("s", [i, j, k]),

                        self.not_equal("x", [i, t], a),

                        self.not_equal("f", [i, b, c], 1 - a)
                    ]

                    if j <= n:
                        if H.nth_bit_of(t, j) != b:
                            continue
                    else:
                        lst.append(self.not_equal("x", [j, t], b))

                    if k <= n:
                        if H.nth_bit_of(t, k) != c:
                            continue
                    else:
                        lst.append(self.not_equal("x", [k, t], c))

                    formula.append(lst)

    def construct_formula(self, f_truthtables, n, m, r):
        formula = pysat.formula.CNF()

        last_new_node = n + r + 1
        new_nodes = range(n + 1, last_new_node)
        truth_table = range(0, 2 ** n)
        functions = range(1, m + 1)

        # Output vertices are equal to truth table's rows
        for h in functions:
            for i in new_nodes:
                for t in truth_table:
                    # [0, 1] to [-1, 1]
                    modifier = f_truthtables[h][t] * 2 - 1
                    formula.append([
                        -1 * self.pool.v_to_id("g", [h, i]),
                        modifier * self.pool.v_to_id("x", [i, t])
                    ])

        # Every output exists somewhere in the chain
        for h in functions:
            formula.append([self.pool.v_to_id("g", [h, i])
                            for i in new_nodes])

        # Every step has exactly two inputs
        for i in new_nodes:
            lst = []
            for k in range(1, i):
                for j in range(1, k):
                    lst.append(self.pool.v_to_id("s", [i, j, k]))
            formula.append(lst)

        # Main clause, check truth table correspondense
        for i in new_nodes:
            for k in range(1, i):
                for j in range(1, k):
                    for t in truth_table:
                        self.check_truth_table_bit(n, i, k, j, t, formula)

        # Ruling out trivial binary operations
        for i in new_nodes:
            formula.append([
                self.pool.v_to_id("f", [i, 0, 1]),
                self.pool.v_to_id("f", [i, 1, 0]),
                self.pool.v_to_id("f", [i, 1, 1])
            ])
            formula.append([
                self.pool.v_to_id("f", [i, 0, 1]),
                -1 * self.pool.v_to_id("f", [i, 1, 0]),
                -1 * self.pool.v_to_id("f", [i, 1, 1])
            ])
            formula.append([
                -1 * self.pool.v_to_id("f", [i, 0, 1]),
                self.pool.v_to_id("f", [i, 1, 0]),
                -1 * self.pool.v_to_id("f", [i, 1, 1])
            ])

        # Each step is used at least once,
        # either as intermediary step
        # or as an output vertex.
        # TODO benchmark without this and with this
        # for i in new_nodes:
        #     lst = []
        #     for k in functions:
        #         lst.append(self.pool.v_to_id("g", [k, i]))
        #     for ish in range(i + 1, last_new_node):
        #         for j in range(1, i):
        #             lst.append(self.pool.v_to_id("s", [ish, i, j]))
        #     for ish in range(i + 1, last_new_node):
        #         for j in range(i + 1, ish):
        #             lst.append(self.pool.v_to_id("s", [ish, j, i]))
        #     formula.append(lst)

        # H.pretty_print_formula(formula)
        return formula

    def try_solve(self, size_allowed, formula):
        with Minisat22(bootstrap_with=formula.clauses, use_timer=True) as solver:
            if self.limit_time:
                timer = Timer(20 + size_allowed, interrupt, [solver])
                timer.start()
                result = solver.solve_limited(expect_interrupt=True)
                timer.cancel()
            else:
                result = solver.solve()

            if result:
                if self.pretty_print:
                    print(solver.accum_stats())
                return True, solver.get_model()
            else:  # solve could also return `None`, will treat as `False`
                print(solver.accum_stats())
                print("UNSAT with ", size_allowed, " , time = ",
                      '{0:.2f}s'.format(solver.time()))
                return False, None

    def generate_schema(self, n, m, f_truthtables, schema_size):
        self.pool = H.TPoolHolder()
        found_scheme_size = -1
        for cur_size in range(1, int(schema_size)):
            formula = self.construct_formula(f_truthtables, n, m, cur_size)
            t1 = time.time()
            solved, model = self.try_solve(cur_size, formula)
            t2 = time.time()
            if solved:
                found_scheme_size = cur_size
                break

        self.last_sat_attempt_time = t2 - t1

        if found_scheme_size == -1:
            print("No solution with schema size up to", schema_size)
            return

        gr, f_to_node, node_truthtables = self.interpret_as_graph(
            cur_size, model)
        return gr, f_to_node, node_truthtables, found_scheme_size

    def generate_fixed_size_schema(self, n, m, f_truthtables, cur_size):
        '''Undefined behaviour if supplied task is UNSAT'''
        self.pool = H.TPoolHolder()
        found_scheme_size = -1
        formula = self.construct_formula(f_truthtables, n, m, cur_size)
        t1 = time.time()
        _, model = self.try_solve(cur_size, formula)
        t2 = time.time()

        self.last_sat_attempt_time = t2 - t1

        gr, f_to_node, node_truthtables = self.interpret_as_graph(
            cur_size, model)
        return gr, f_to_node, node_truthtables, found_scheme_size

    def interpret_as_graph(self, r, model):
        if self.pretty_print:
            print("The schema consists of", r, "additional nodes")

        gr = dict()
        f_to_node = dict()

        node_truthtables = defaultdict(lambda: defaultdict(dict))

        for variable in model:
            key = json.loads(self.pool.id_to_v(abs(variable)))

            if key['char'] == "g":
                if variable > 0:
                    h, i = key['ids']
                    f_to_node[h] = i
                    if self.pretty_print:
                        print("Output", h, "is located at vertex", i)

            if key['char'] == "f":
                i, p, q = key['ids']
                result = variable > 0
                node_truthtables[i][p][q] = result
                if self.pretty_print:
                    print("Vertex", i, "produces from", p, q,
                          "value", result)

            if key['char'] == "s":
                i, j, k = key['ids']
                if variable > 0:
                    gr[i] = (j, k)
                    if self.pretty_print:
                        print("Vertex", i, "is calculated from", j, k)

        return gr, f_to_node, node_truthtables


def run_fixed(truth_tables_file, schema_size):
    random.seed()

    f = open(truth_tables_file, "r")
    lines = f.readlines()
    f.close()
    n, m, f_truthtables, _ = H.read_one_test(lines, curshift=0)

    schemaGenerator = TSchemaGenerator(should_pretty_print=True)
    gr, f_to_node, node_truthtables, found_scheme_size = schemaGenerator.generate_schema(
        n, m, f_truthtables, schema_size)

    V.validate(gr, f_to_node, f_truthtables,
               node_truthtables, n, m, found_scheme_size)
