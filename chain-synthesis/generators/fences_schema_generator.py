import time
import pysat

# from pysat.solvers import Lingeling
from pysat.solvers import Minisat22
from pysat.solvers import Cadical

import helpers as H
import generators.fence_enumerator as F


class TFenceGenerator:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def refresh(self):
        self.pool = H.TPoolHolder()

    def launch_solver(self, cur_size, formula, prop_limit):
        with Minisat22(bootstrap_with=formula.clauses, use_timer=True) as solver:
            solver.prop_budget(prop_limit)
            solved = solver.solve_limited(expect_interrupt=True)

            if solved is None:
                print("Skipping topology due to budget constraints", prop_limit)
                return H.TSolverResult.timed_out, None
            elif not solved:
                print(solver.accum_stats())
                print("UNSAT with ", cur_size, " , time = ",
                      '{0:.2f}s'.format(solver.time()))
                return H.TSolverResult.unsat, None
            else:  # solved
                print("DAG solution found!")
                return H.TSolverResult.sat, solver.get_model()

    def try_solve(self, f_truthtables, n, m, cur_size):
        total_elapsed = 0

        propagations_limit = 100000

        known_unsat = set()
        fences_len = 1

        while len(known_unsat) < fences_len:
            fence_id = 0
            # TODO if you want to parallel stuff,
            # just use the next line as a main threadpool-controlling
            # loop and give the rest to worker threads
            fences = F.TFenceEnumerator(cur_size).iter()
            propagations_limit *= 4

            for fence in fences:
                fence_id += 1
                fences_len = max(fences_len, fence_id)
                if fence_id in known_unsat:
                    continue
                cur_size, formula = self.construct_formula(
                    f_truthtables, n, m, fence)
                t1 = time.time()
                solved, model = self.launch_solver(cur_size, formula, propagations_limit)
                t2 = time.time()
                total_elapsed += t2 - t1
                if solved == H.TSolverResult.sat:
                    return True, model, total_elapsed
                elif solved == H.TSolverResult.unsat:
                    known_unsat.add(fence_id)

        return False, None, total_elapsed

    def not_equal(self, char, ids, bit):
        if bit == 1:
            return -1 * self.pool.v_to_id(char, ids)
        else:
            return self.pool.v_to_id(char, ids)

    def generate_truth_table_clauses(self, n, i, j, k, t, formula):
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

    def safe_topological_ijk(self, i, _, k):
        return self.v_to_level[i] == self.v_to_level[k] + 1

    def safe_topological_ijkp(self, i, _1, _2, p):
        return self.v_to_level[i] == self.v_to_level[p] + 1

    def construct_formula(self, f_truthtables, n, m, fence):
        n_levels = len(fence)
        r = sum(fence)

        self.v_to_level = dict()

        for input_node in range(1, n + 1):
            self.v_to_level[input_node] = 0

        node_num = n + 1
        for lvl in range(0, n_levels):
            for tmpi in range(0, fence[lvl]):
                self.v_to_level[node_num] = lvl + 1
                node_num += 1

        assert node_num == n + r + 1, "Didn't construct proper node_to_level mapping."

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

        # Every step has exactly two inputs, but limited to topology
        for i in new_nodes:
            lst = []
            for k in range(1, i):
                for j in range(1, k):
                    if self.safe_topological_ijk(i, j, k):
                        lst.append(self.pool.v_to_id("s", [i, j, k]))
            formula.append(lst)

        # Main clause, check truth table correspondense
        for i in new_nodes:
            for k in range(1, i):
                for j in range(1, k):
                    # All the fuss is about the next check:
                    if self.safe_topological_ijk(i, j, k):
                        for t in truth_table:
                            self.generate_truth_table_clauses(
                                n, i, j, k, t, formula)

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
                    if self.safe_topological_ijk(ish, j, i):
                        lst.append(self.pool.v_to_id("s", [ish, j, i]))
            for ish in range(i + 1, last_new_node):
                for j in range(i + 1, ish):
                    if self.safe_topological_ijk(ish, i, j):
                        lst.append(self.pool.v_to_id("s", [ish, i, j]))
            formula.append(lst)

        if self.pipeline.pretty_print:
            H.pretty_print_formula(self.pool, formula)

        print("Formula size in clauses", len(formula.clauses))

        return r, formula

    def generate_truth_table_clauses_support_three(self, n, i, j, k, p, t, formula):
        for a in range(0, 2):
            for b in range(0, 2):
                for c in range(0, 2):
                    for d in range(0, 2):
                        lst = [
                            -1 * self.pool.v_to_id("q", [i, j, k, p]),
                            self.not_equal("x", [i, t], a),
                            self.not_equal("z", [i, b, c, d], 1 - a)
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

                        if p <= n:
                            if H.nth_bit_of(t, p) != d:
                                continue
                        else:
                            lst.append(self.not_equal("x", [p, t], d))

                        formula.append(lst)

    def construct_formula_support_three(self, f_truthtables, n, m, r):
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

        # For every step, at least one is true:
        # exists `i j k` so it is a 2-input step, j < k
        # exists `i j k p` so it is a 3-input step j < k < p
        for i in new_nodes:
            lst = []
            for k in range(1, i):
                for j in range(1, k):
                    if self.safe_topological_ijk(i, j, k):
                        lst.append(self.pool.v_to_id("s", [i, j, k]))
            for p in range(1, i):
                for k in range(1, p):
                    for j in range(1, k):
                        if self.safe_topological_ijkp(i, j, k, p):
                            lst.append(self.pool.v_to_id("q", [i, j, k, p]))
            formula.append(lst)

        # Main clause, check truth table correspondense, 2 argument operators
        for i in new_nodes:
            for k in range(1, i):
                for j in range(1, k):
                    if self.safe_topological_ijk(i, j, k):
                        for t in truth_table:
                            self.generate_truth_table_clauses(
                                n, i, j, k, t, formula)

        # Main clause, check truth table correspondense, 3 argument operators
        for i in new_nodes:
            for p in range(1, i):
                for k in range(1, p):
                    for j in range(1, k):
                        if self.safe_topological_ijkp(i, j, k, p):
                            for t in truth_table:
                                self.generate_truth_table_clauses_support_three(
                                    n, i, j, k, p, t, formula)

        for i in new_nodes:
            for p in range(1, i):
                for k in range(1, p):
                    for j in range(1, k):
                        for k2 in range(1, i):
                            for j2 in range(1, k2):
                                if self.safe_topological_ijkp(i, j, k, p) and self.safe_topological_ijk(i, j, k):
                                    formula.append([
                                        -1 * self.pool.v_to_id("q", [i, j, k, p]),
                                        -1 * self.pool.v_to_id("s", [i, j2, k2])
                                    ])

        print("Formula size in clauses", len(formula.clauses))
        return formula
