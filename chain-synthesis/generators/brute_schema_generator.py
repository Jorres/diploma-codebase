import time
import helpers as H
import pysat

from pysat.solvers import Minisat22


class TBruteGenerator:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def refresh(self):
        self.pool = H.TPoolHolder()

    def try_solve(self, f_truthtables, n, m, cur_size):
        formula = self.construct_formula(
            f_truthtables, n, m, cur_size)
        t1 = time.time()
        solved, model = self.launch_solver(cur_size, formula)
        t2 = time.time()
        return solved, model, t2 - t1

    def not_equal(self, char, ids, bit):
        if bit == 1:
            return -1 * self.pool.v_to_id(char, ids)
        else:
            return self.pool.v_to_id(char, ids)

    def launch_solver(self, cur_size, formula):
        with Minisat22(bootstrap_with=formula.clauses, use_timer=True) as solver:
            result = solver.solve()

            if result:
                if self.pipeline.pretty_print:
                    print(solver.accum_stats())
                return True, solver.get_model()
            else:
                # print(solver.accum_stats())
                print("UNSAT with ", cur_size, " , time = ",
                      '{0:.2f}s'.format(solver.time()))
                return False, None

    def generate_truth_table_clauses(self, n, i, j, k, t, formula):
        # TODO explain this clause, bring the formula here
        for a in range(0, 2):
            for b in range(0, 2):
                for c in range(0, 2):
                    lst = [
                        -1 * self.pool.v_to_id("s", [i, j, k]),
                        self.not_equal("x", [i, t], a),
                        self.not_equal("f", [i, b, c], 1 - a)
                    ]

                    if j <= n:
                        # That means, vertex j is an input, not an
                        # internal node, and its value is known.
                        if H.nth_bit_of(t, j) != b:
                            continue
                    else:
                        lst.append(self.not_equal("x", [j, t], b))

                    if k <= n:
                        # That means, vertex k is an input, not an
                        # internal node, and its value is known.
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

        # Truth tables of output vertices are equal to truth tables of given functions
        for h in functions:
            for i in new_nodes:
                for t in truth_table:
                    # [0, 1] to [-1, 1]
                    modifier = f_truthtables[h][t] * 2 - 1
                    formula.append([
                        -1 * self.pool.v_to_id("g", [h, i]),
                        modifier * self.pool.v_to_id("x", [i, t])
                    ])

        # Every output is assigned to some node
        for h in functions:
            formula.append([self.pool.v_to_id("g", [h, i])
                            for i in new_nodes])

        # Every node has exactly two inputs
        for i in new_nodes:
            lst = []
            for k in range(1, i):
                for j in range(1, k):
                    lst.append(self.pool.v_to_id("s", [i, j, k]))
            formula.append(lst)

        # Main clause, encodes topology and truth table of a node
        for i in new_nodes:
            for k in range(1, i):
                for j in range(1, k):
                    for t in truth_table:
                        self.generate_truth_table_clauses(
                            n, i, j, k, t, formula)

        # Rules out trivial binary operations -
        # constant 1, projections of both variables
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

        # Each step is used at least once, either as 
        # intermediary step or as an output vertex.
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

        # Avoid a situation like this:
        #      3 # vertex 3 is useless, it `knows` exactly the
        #     /| # same things as vertex 2 -> possible to create equivalent
        #    / | # without it
        #    2 |
        #    |/
        #    1
        for i in new_nodes:
            for k in range(1, i):
                for j in range(1, k):
                    for ish in range(i + 1, last_new_node):
                        formula.append([
                            -1 * self.pool.v_to_id("s", [i, j, k]),
                            -1 * self.pool.v_to_id("s", [ish, j, i]),
                        ])
                        formula.append([
                            -1 * self.pool.v_to_id("s", [i, j, k]),
                            -1 * self.pool.v_to_id("s", [ish, k, i]),
                        ])

        # Symmetry breaking - it should not be possible to have situations like this:
        # (vertex 8 with children 1 2) AND (vertex 7 with children 3 4)
        # because we can renumerate the vertices in colexicographical order
        # and have a much smaller search space as a result.
        for i in range(n + 1, last_new_node - 1):
            for k in range(1, i):
                for j in range(1, k):
                    for ksh in range(1, i + 1):
                        for jsh in range(1, ksh):
                            if ksh == k and jsh < j:
                                formula.append([
                                    -1 * self.pool.v_to_id("s", [i, j, k]),
                                    -1 *
                                    self.pool.v_to_id(
                                        "s", [(i + 1), jsh, ksh]),
                                ])
                            if ksh < k:
                                formula.append([
                                    -1 * self.pool.v_to_id("s", [i, j, k]),
                                    -1 *
                                    self.pool.v_to_id(
                                        "s", [(i + 1), jsh, ksh]),
                                ])

        if self.pipeline.pretty_print:
            H.pretty_print_formula(self.pool, formula)
            print("Formula size in clauses", len(formula.clauses))

        return formula
