import json
import os
import os.path

import helpers as H
import schema_generator as S


def benchmark(test_suite_file, iterations):
    test_suite_file = os.path.basename(test_suite_file)
    f = open(os.path.join("test_suites", test_suite_file), "r")
    lines = f.readlines()
    f.close()

    schema_generator = S.TSchemaGenerator(
        should_pretty_print=False, should_limit_time=False)

    total_result_files = 0

    for suite_result in os.listdir('benchmark_results'):
        if test_suite_file in suite_result:
            total_result_files += 1

    filename = os.path.join("benchmark_results", "results_{}_{}".format(
        test_suite_file, total_result_files + 1))

    benchmark_results = dict()

    curshift = 0
    test_id = 1
    with open(filename, "w+") as resultfile:
        while curshift < len(lines):
            n, m, f_truthtables, schema_size, curshift = H.read_bench_test(
                lines, curshift)
            sum_time = 0
            test_result = dict()
            test_result['test_id'] = test_id
            test_result['runtimes'] = list()
            for _ in range(0, iterations):
                schema_generator.generate_fixed_size_schema(
                    n, m, f_truthtables, schema_size)
                sum_time += schema_generator.last_sat_attempt_time
                test_result['runtimes'].append(
                    schema_generator.last_sat_attempt_time)

            test_result['avg_runtime'] = sum_time / iterations
            benchmark_results[test_id] = test_result
            test_id += 1

        resultfile.write(json.dumps(benchmark_results, indent=4))
