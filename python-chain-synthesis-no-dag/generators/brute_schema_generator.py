import time
import helpers as H
import pysat


class TBruteGenerator:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def refresh(self):
        self.pool = H.TPoolHolder()

    def try_solve(self, f_truthtables, n, m, cur_size):
        formula = self.construct_formula(f_truthtables, n, m, cur_size)
        t1 = time.time()
        solved, model = self.pipeline.launch_solver(cur_size, formula)
        t2 = time.time()
        return solved, model, t2 - t1

    def not_equal(self, char, ids, bit):
        if bit == 1:
            return -1 * self.pool.v_to_id(char, ids)
        else:
            return self.pool.v_to_id(char, ids)

    def generate_truth_table_clauses(self, n, i, k, j, t, formula):
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
                        self.generate_truth_table_clauses(n, i, k, j, t, formula)

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
        for i in new_nodes:
            lst = []
            for k in functions:
                lst.append(self.pool.v_to_id("g", [k, i]))
            for ish in range(i + 1, last_new_node):
                for j in range(1, i):
                    lst.append(self.pool.v_to_id("s", [ish, j, i]))
            for ish in range(i + 1, last_new_node):
                for j in range(i + 1, ish):
                    lst.append(self.pool.v_to_id("s", [ish, i, j]))
            formula.append(lst)

        # H.pretty_print_formula(formula)
        return formula
