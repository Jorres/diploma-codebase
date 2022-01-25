import pysat
import time

from pysat.solvers import Minisat22

import formula_builder as FB

class PairEliminator():
    def __init__(self):
        self.prune_runtimes = []

    def prune_from_checkpoint(self, g, formula, pool, last_pruned_id):
        removed_set = set()
        with Minisat22(bootstrap_with=formula.clauses) as solver:
            for i in range(last_pruned_id, len(g.node_names)):
                name_1 = g.node_names[i]
                if name_1.startswith("v"):
                    continue
                print(name_1)
                for j in range(i + 1, len(g.node_names)):
                    name_2 = g.node_names[j]
                    if name_2.startswith("v"):
                        continue

                    # TODO this is temporary hack, because I forgot
                    # to cut and replace, refer to another todo
                    if name_1 == name_2:
                        continue

                    gate_type_1 = name_1[0]
                    gate_type_2 = name_2[0]

                    assert gate_type_1 in ['v', 'i', 'a']
                    assert gate_type_2 in ['v', 'i', 'a']

                    if gate_type_1 != gate_type_2:
                        continue

                    results = []
                    for bit_i in [-1, 1]:
                        for bit_j in [-1, 1]:
                            var_i = pool.v_to_id(name_1)
                            var_j = pool.v_to_id(name_2)
                            var_i *= bit_i
                            var_j *= bit_j
                            t1 = time.time()
                            results.append(solver.solve(
                                assumptions=[var_i, var_j]))
                            t2 = time.time()
                            self.prune_runtimes.append(t2 - t1)

                    if results == [True, False, False, True]:
                        assert name_2 not in removed_set
                        removed_set.add(name_2)
                        print("Found equivalent pair", name_1, name_2)
                        last_pruned_id = i
                        pruned = g.prune_pair(name_1, name_2, True)
                        return g, True, last_pruned_id, pruned
                    # Pruning negative is unsupported yet
                    # if results == [False, True, True, False] and not (name_1.startswith("i")) and not (name_2.startswith("i")):
                    #     assert name_2 not in removed_set
                    #     removed_set.add(name_2)
                    #     print("Found neg-equivalent pair", name_1, name_2)
                    #     last_pruned_id = i
                    #     pruned = g.prune_pair(name_1, name_2, False)
                    #     return g, True, last_pruned_id, pruned
            return g, False, last_pruned_id, 0


    def try_prune_all_pairs(self, g):
        total_pruned = 0
        last_pruned_id = 0
        pool = FB.TPoolHolder()
        while True:
            formula = FB.make_formula_from_my_graph(g, pool)
            g, was_pruned, last_pruned_id, pruned_this_time = self.prune_from_checkpoint(
                g, formula, pool, last_pruned_id)
            if not was_pruned:
                break
            total_pruned += pruned_this_time
        return g, total_pruned
