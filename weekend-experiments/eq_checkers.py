import pysat
import time

from pycryptosat import Solver

import utils as U
import formula_builder as FB


def validate_naively(g1, g2, metainfo, cnf_file):
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)
    final_cnf = FB.generate_miter_scheme(shared_cnf, pool, g1, g2)
    pysat.formula.CNF(from_clauses=final_cnf).to_file(cnf_file)

    solver = Solver()
    solver.add_clauses(final_cnf)

    t1 = time.time()
    result, solution = solver.solve()
    t2 = time.time()

    metainfo["solver_only_time_no_preparation"] = t2 - t1
    return not result


def validate_with_open_xors(g1, g2, metainfo):
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)

    # TODO re-use input variables instead of adding clauses on inputs equality (!!!)
    for input_id in range(0, g1.n_inputs):

        # Add clauses for input equality
        input_g1_var = g1.input_var_to_cnf_var(f"v{input_id}{g1.tag}", pool)
        input_g2_var = g2.input_var_to_cnf_var(f"v{input_id}{g2.tag}", pool)

        shared_cnf.append([-1 * input_g1_var, input_g2_var])
        shared_cnf.append([input_g1_var, -1 * input_g2_var])

    solver = Solver()
    solver.add_clauses(shared_cnf)

    assert g1.n_outputs == g2.n_outputs
    for output_id in range(g1.n_outputs):
        output_name = f"o{output_id}"
        output_var_1 = g1.output_var_to_cnf_var(output_name, pool)
        output_var_2 = g2.output_var_to_cnf_var(output_name, pool)

        conj_table = list()
        one_xor_runtime = list()
        for bit_left in [-1, 1]:
            for bit_right in [-1, 1]:
                assumptions = [bit_left * output_var_1, bit_right * output_var_2]

                t1 = time.time()
                res, solution = solver.solve(assumptions=assumptions)
                conj_table.append(res)
                t2 = time.time()

                one_xor_runtime.append(t2 - t1)
        metainfo[f"runtimes_{output_id}"] = one_xor_runtime

        if conj_table == [True, False, False, True]:
            print(f"Output {output_id} equivalent")
        else:
            print(f"Output {output_id} non-equivalent")
            return False

    return True