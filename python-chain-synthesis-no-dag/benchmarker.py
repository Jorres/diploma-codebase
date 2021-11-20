import helpers as H
import schema_generator as S

TEST_SUITE_FILE = "initial_tests.txt"


def main():
    f = open(TEST_SUITE_FILE, "r")
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


if __name__ == "__main__":
    main()
