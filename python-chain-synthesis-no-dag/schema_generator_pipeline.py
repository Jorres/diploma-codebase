import json
import random

# from pysat.solvers import Lingeling
from pysat.solvers import Minisat22
from collections import defaultdict
from threading import Timer

import helpers as H
import validator as V

import generators.brute_schema_generator as Br
import generators.fences_schema_generator as Fe


def interrupt(s):
    s.interrupt()


class TSchemaPipeline():
    def __init__(self, should_pretty_print, should_limit_time=True, mode="brute"):
        self.limit_time = should_limit_time
        self.pretty_print = should_pretty_print
        if mode == "brute":
            self.generator = Br.TBruteGenerator(self)
        elif mode == "fences":
            self.generator = Fe.TFenceGenerator(self)

    # Measurements when solving with increasing size vs when solving on fixed size
    # are skewed. Hypothesis: increasing size allows solver to accumulate some data
    def launch_solver(self, size_allowed, formula):
        '''
        This function is used internally by schema generators, they access it through 
        reference to the pipeline.
        '''
        with Minisat22(bootstrap_with=formula.clauses, use_timer=True) as solver:
            if self.limit_time:
                # TODO this is no longer a good upper bound limitation.
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
            else:
                print(solver.accum_stats())
                print("UNSAT with ", size_allowed, " , time = ",
                      '{0:.2f}s'.format(solver.time()))
                return False, None

    def generate_schema(self, n, m, f_truthtables, schema_size):
        '''
        A generic starting point for solving algorithm. `mode` is either
        `brute` or `fences`.
        '''
        for cur_size in range(1, int(schema_size)):
            solved, gr, f_to_node, node_truthtables, cur_size = self.generate_fixed_size_schema(
                n, m, f_truthtables, cur_size)
            if solved:
                return gr, f_to_node, node_truthtables, cur_size

        print("No solution with schema size up to", schema_size)
        return

    def generate_fixed_size_schema(self, n, m, f_truthtables, cur_size):
        self.generator.refresh()
        solved, model, elapsed = self.generator.try_solve(
            f_truthtables, n, m, cur_size)
        if solved:
            self.last_sat_attempt_time = elapsed
            gr, f_to_node, node_truthtables = self.interpret_as_graph(
                cur_size, model)
            return True, gr, f_to_node, node_truthtables, cur_size
        else:
            return False, None, None, None, None

    def interpret_as_graph(self, r, model):
        if self.pretty_print:
            print("The schema consists of", r, "additional nodes")

        gr = dict()
        f_to_node = dict()

        node_truthtables = defaultdict(lambda: defaultdict(dict))

        for variable in model:
            key = json.loads(self.generator.pool.id_to_v(abs(variable)))

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


def run_fixed(truth_tables_file, schema_size, mode):
    random.seed()

    f = open(truth_tables_file, "r")
    lines = f.readlines()
    f.close()
    n, m, f_truthtables, _ = H.read_one_test(lines, curshift=0)

    schemaGenerator = TSchemaPipeline(should_pretty_print=True, mode=mode)
    gr, f_to_node, node_truthtables, found_scheme_size = schemaGenerator.generate_schema(
        n, m, f_truthtables, schema_size)

    V.validate(gr, f_to_node, f_truthtables,
               node_truthtables, n, m, found_scheme_size)
