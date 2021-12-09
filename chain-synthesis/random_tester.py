import schema_generator_pipeline as S
import validator as V
import helpers as H


def run_random(max_n, max_m, amount, max_size, mode):
    schema_generator = S.TSchemaPipeline(should_pretty_print=False, mode=mode)
    for num in range(0, amount):
        n, m, f_truthtables = H.make_random_test(max_n, max_m)

        gr = schema_generator.generate_schema(n, m, f_truthtables, max_size)

        V.validate(gr, f_truthtables, n, m)


def compare_on_random(max_n, max_m, amount, max_size):
    schema_generator_brute = S.TSchemaPipeline(
        should_pretty_print=False, mode='brute')
    schema_generator_fences = S.TSchemaPipeline(
        should_pretty_print=False, mode='fences')
    for _ in range(0, amount):
        n, m, f_truthtables = H.make_random_test(max_n, max_m)

        gr_brute = schema_generator_brute.generate_schema(
            n, m, f_truthtables, max_size)
        gr_fences = schema_generator_fences.generate_schema(
            n, m, f_truthtables, max_size)

        V.validate(gr_brute, f_truthtables, n, m)
        V.validate(gr_fences, f_truthtables, n, m)

        if gr_brute.schema_size != gr_fences.schema_size:
            print(n, m, f_truthtables)
            print(gr_brute.schema_size, gr_fences.schema_size)
            assert False
