import sys

import schema_generator as S
import validator as V
import helpers as H


def main():
    max_n = int(sys.argv[1])
    max_m = int(sys.argv[2])
    # Throw a bunch of random functions, for now
    # Random functions go brrr
    schema_generator = S.TSchemaGenerator(should_pretty_print=False)
    for num in range(0, 100):
        n, m, f_truthtables = H.make_random_test(max_n, max_m)

        gr, f_to_node, node_truthtables, found_scheme_size = schema_generator.generate_schema(
            n, m, f_truthtables, 100)

        V.validate(gr, f_to_node, f_truthtables,
                   node_truthtables, n, m, found_scheme_size)


if __name__ == "__main__":
    main()
