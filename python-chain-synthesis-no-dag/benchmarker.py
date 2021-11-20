import helpers as H
import schema_generator as S


def benchmark(test_suite_file):
    f = open(test_suite_file, "r")
    lines = f.readlines()
    f.close()

    schema_generator = S.TSchemaGenerator(
        should_pretty_print=False, should_limit_time=False)

    curshift = 0
    test_id = 1
    while curshift < len(lines):
        n, m, f_truthtables, schema_size, curshift = H.read_bench_test(
            lines, curshift)
        schema_generator.generate_fixed_size_schema(
            n, m, f_truthtables, schema_size)
        print(test_id, " : ", schema_generator.last_sat_attempt_time)
