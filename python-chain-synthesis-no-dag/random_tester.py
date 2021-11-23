import json 

import schema_generator_pipeline as S
import validator as V
import helpers as H


def run_random(max_n, max_m, amount, max_size, mode):
    # Throw a bunch of random functions, for now
    # Random functions go brrr
    schema_generator = S.TSchemaPipeline(should_pretty_print=False, mode=mode)
    for num in range(0, amount):
        n, m, f_truthtables = H.make_random_test(max_n, max_m)

        gr, f_to_node, node_truthtables, found_scheme_size = schema_generator.generate_schema(
            n, m, f_truthtables, max_size)

        V.validate(gr, f_to_node, f_truthtables,
                   node_truthtables, n, m, found_scheme_size)
