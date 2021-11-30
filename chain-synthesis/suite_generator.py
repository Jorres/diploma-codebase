import datetime
import os.path

from math import floor

import validator as V
import helpers as H
import schema_generator_pipeline as S


def generate_suite(n, m, amount, max_size, allow_small):
    filename = os.path.join("test_suites", "suite_{}".format(
        floor(datetime.datetime.now().timestamp())))

    for num in range(0, amount):
        print("Running example ", num)
        n, m, f_truthtables = H.make_precise_test(n, m)

        schema_generator = S.TSchemaPipeline(should_pretty_print=False, mode="brute")

        gr = schema_generator.generate_schema(n, m, f_truthtables, max_size)
        elapsed_time = schema_generator.last_sat_attempt_time

        lower_bound = 1
        if allow_small:
            print("Generating small test")
            lower_bound = 0.000001
        if elapsed_time > lower_bound:
            with open(filename, "a") as testfile:
                testfile.write(str(n) + " " + str(m) + " " +
                               str(gr.schema_size) + "\n")
                for j in range(0, 2 ** n):
                    for i in range(0, m):
                        testfile.write(str(f_truthtables[i + 1][j]))
                    testfile.write('\n')

        V.validate(gr, f_truthtables, n, m)
