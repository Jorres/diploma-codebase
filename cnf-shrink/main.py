import pysat
import graph as G

from pysat.solvers import Minisat22
import aiger
from aiger_cnf import aig2cnf

import helpers as H


def attempt_prune_and_gate(g, formula, pool, last_min):
    with Minisat22(bootstrap_with=formula.clauses) as solver:
        for i in range(last_min, len(g.node_names)):
            name_1 = g.node_names[i]
            if name_1.startswith("v"):
                continue
            print(name_1)
            for j in range(i + 1, len(g.node_names)):
                name_2 = g.node_names[j]
                if name_2.startswith("v"):
                    continue
                results = []
                for bit_i in [-1, 1]:
                    for bit_j in [-1, 1]:
                        var_i = pool.v_to_id(name_1)
                        var_j = pool.v_to_id(name_2)
                        var_i *= bit_i
                        var_j *= bit_j
                        results.append(solver.solve(
                            assumptions=[var_i, var_j]))
                if results == [True, False, False, True]:
                    print("Found equivalent pair")
                    last_min = max(i, j)
                    pruned = g.prune(name_1, name_2, True)
                    return g, True, last_min, pruned
                if results == [False, True, True, False] and not (name_1.startswith("i")) and not (name_2.startswith("i")):
                    print("Found neg-equivalent pair")
                    last_min = max(i, j)
                    pruned = g.prune(name_1, name_2, False)
                    return g, True, last_min, pruned
        return g, False, last_min, 0


def validate(g, aig):
    start_cnf = aig2cnf(aig.aig)
    shift = -1
    for clause in start_cnf.clauses:
        for var in clause:
            shift = max(shift, var)

    pool = H.TPoolHolder(start_from=shift + 1)
    my_cnf = H.make_formula_from_my_graph(g, pool)
    final_cnf = my_cnf.clauses
    for clause in start_cnf.clauses:
        if len(clause) == 1:
            continue
        final_cnf.append(list(clause))

    for input in aig.inputs:
        # Add clause for input equality
        input_aig_var = start_cnf.input2lit[input]
        input_graph_var = g.what_input_var(input, pool)

        final_cnf.append([-1 * input_aig_var, input_graph_var])
        final_cnf.append([input_aig_var, -1 * input_graph_var])

    for i, output in enumerate(aig.outputs):
        # Add clause for output xor gate
        c = pool.v_to_id("xor_" + str(i))
        a = start_cnf.output2lit[output]
        b = g.what_output_var(output, pool)
        final_cnf.append([-1 * a, -1 * b, -1 * c])
        final_cnf.append([a, b, -1 * c])
        final_cnf.append([a, -1 * b, c])
        final_cnf.append([-1 * a, b, c])

    # OR together all new xor_ variables
    lst = []
    for i in range(len(aig.outputs)):
        lst.append(pool.v_to_id("xor_" + str(i)))
    final_cnf.append(lst)

    # Finally, check the formula for SAT\UNSAT
    with Minisat22(bootstrap_with=final_cnf) as solver:
        print("Running SAT-solver to determine scheme equivalency")
        result = solver.solve()
        print(result)
        if not result:
            print("Hoorah, UNSAT means schemes are equivalent")
        if result:
            print("Your schema is broken :( #sorrynotsorry")


def main():
    test_path = "./sorts/BubbleSort_7_4.aig"
    aig_instance = aiger.load(test_path)
    pool = H.TPoolHolder()
    g = G.Graph(aig_instance)

    total_pruned = 0
    last_min = 0
    while True:
        formula = H.make_formula_from_my_graph(g, pool)
        g, was_pruned, last_min, pruned_this_time = attempt_prune_and_gate(
            g, formula, pool, last_min)
        total_pruned += pruned_this_time
        if not was_pruned:
            break
    print(total_pruned)
    validate(g, aig_instance)



if __name__ == "__main__":
    main()
