import sys

import validator as V
import helpers as H
import schema_generator as S


def main():
    n = int(sys.argv[1])
    m = int(sys.argv[2])
    amount = int(sys.argv[3])

    for num in range(0, amount):
        print("Running example...", num)
        n, m, f_truthtables = H.make_precise_test(n, m)

        max_size = 100

        schema_generator = S.TSchemaGenerator(should_pretty_print=False)

        gr, f_to_node, node_truthtables, found_scheme_size = schema_generator.generate_schema(
            n, m, f_truthtables, max_size)
        elapsed_time = schema_generator.last_sat_attempt_time
        print(elapsed_time)
        if elapsed_time > 1:
            with open("initial_tests.txt", "a") as myfile:
                # myfile.write(str(elapsed_time) + " ")
                myfile.write(str(n) + " " + str(m) + " " +
                             str(found_scheme_size) + "\n")
                # myfile.write("on size " + str(found_scheme_size) + "\n")
                for j in range(0, 2 ** n):
                    for i in range(0, m):
                        myfile.write(str(f_truthtables[i + 1][j]))
                    myfile.write('\n')
                # myfile.write('---\n')

        V.validate(gr, f_to_node, f_truthtables,
                   node_truthtables, n, m, found_scheme_size)


if __name__ == "__main__":
    main()
