import datetime
import os.path

from math import floor

import validator as V
import helpers as H
import schema_generator as S


def generate_suite(n, m, amount, max_size):
    filename = os.path.join("test_suites", "suite_{}".format(
        floor(datetime.datetime.now().timestamp())))

    for num in range(0, amount):
        print("Running example ", num)
        n, m, f_truthtables = H.make_precise_test(n, m)

        schema_generator = S.TSchemaGenerator(should_pretty_print=False)

        gr, f_to_node, node_truthtables, found_scheme_size = schema_generator.generate_schema(
            n, m, f_truthtables, max_size)
        elapsed_time = schema_generator.last_sat_attempt_time
        if elapsed_time > 0.00001:
            with open(filename, "a") as testfile:
                testfile.write(str(n) + " " + str(m) + " " +
                               str(found_scheme_size) + "\n")
                for j in range(0, 2 ** n):
                    for i in range(0, m):
                        testfile.write(str(f_truthtables[i + 1][j]))
                    testfile.write('\n')

        V.validate(gr, f_to_node, f_truthtables,
                   node_truthtables, n, m, found_scheme_size)

# These guys said they `generalized` and I'm afraid I will have to generalize 
# as well. But for now, I will just arrange an iteration over only those of my DAG's
# that have this property of every vertex having exactly two inputs. 


# It should not be too difficult though. Implementing this `generalization`. An idea 
# is quite simple, and if an idea is simple, implementation should be too!
