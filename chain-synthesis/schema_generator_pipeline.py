import random

import helpers as H
import validator as V
import graph as G

import generators.brute_schema_generator as Br
import generators.fences_schema_generator as Fe


class TSchemaPipeline():
    def __init__(self, should_pretty_print, mode="brute"):
        self.pretty_print = should_pretty_print
        if mode == "brute":
            self.generator = Br.TBruteGenerator(self)
        elif mode == "fences":
            self.generator = Fe.TFenceGenerator(self)

    def generate_schema(self, n, m, f_truthtables, schema_size):
        self.acc_time = 0
        self.time_per_topology = []
        self.generator.clean_formulas()
        for cur_size in range(1, int(schema_size)):
            solved, gr = self.generate_fixed_size_schema(n, m, f_truthtables, cur_size)
            if solved:
                return gr

        print("No solution with schema size up to", schema_size)
        return None

    def generate_fixed_size_schema(self, n, m, f_truthtables, cur_size):
        self.generator.refresh()
        solved, model, elapsed = self.generator.try_solve(
            f_truthtables, n, m, cur_size)
        self.acc_time += elapsed
        if solved:
            self.last_sat_attempt_time = elapsed
            gr = G.TGraph(cur_size, model, self.pretty_print, self.generator.pool)
            return True, gr
        else:
            return False, None


def run_fixed(truth_tables_file, schema_size, mode):
    random.seed(1)

    f = open(truth_tables_file, "r")
    lines = f.readlines()
    f.close()
    n, m, f_truthtables, _ = H.read_one_test(lines, curshift=0)

    schemaGenerator = TSchemaPipeline(should_pretty_print=True, mode=mode)
    gr = schemaGenerator.generate_schema(n, m, f_truthtables, schema_size)

    V.validate(gr, f_truthtables, n, m)
