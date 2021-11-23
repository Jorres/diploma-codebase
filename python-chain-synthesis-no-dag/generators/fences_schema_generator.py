import json
import time

import helpers as H
import generators.fence_enumerator as F

import pysat


class TFenceGenerator:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def refresh(self):
        self.pool = H.TPoolHolder()

    def try_solve(self, f_truthtables, n, m, cur_size):
        fence_enumerator = F.TFenceEnumerator(cur_size)
        total_elapsed = 0

        # TODO if you want to parallel stuff, just use the next line as a main threadpool-controlling
        # loop and give the rest to worker threads
        fences = fence_enumerator.iter()

        for fence in fences:
            if fence is None:
                break
            else:
                cur_size, formula = self.construct_formula(
                    f_truthtables, n, m, fence)
                t1 = time.time()
                solved, model = self.pipeline.launch_solver(cur_size, formula)
                t2 = time.time()
                total_elapsed += t2 - t1
                if solved:
                    return True, model, total_elapsed

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

        return r, formula
