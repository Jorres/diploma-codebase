import json
import os
import os.path

from math import floor

import helpers as H
import schema_generator as S


def benchmark(test_suite_file, description, iterations):
    test_suite_file = os.path.basename(test_suite_file)
    f = open(os.path.join("test_suites", test_suite_file), "r")
    lines = f.readlines()
    f.close()

    schema_generator = S.TSchemaGenerator(
        should_pretty_print=False, should_limit_time=False)

    current_bench_id = 0

    for suite_result in os.listdir('benchmark_results'):
        if test_suite_file in suite_result:
            current_bench_id += 1

    filename = os.path.join("benchmark_results", "results_{}_{}".format(
        test_suite_file, current_bench_id + 1))

    benchmark_results = dict()

    curshift = 0
    test_id = 1
    benchmark_results['description'] = description
    with open(filename, "w+") as resultfile:
        while curshift < len(lines):
            n, m, f_truthtables, schema_size, curshift = H.read_bench_test(
                lines, curshift)
            print("Benchmarking example ", test_id)
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

    compare_with_previous(benchmark_results, test_id,
                          test_suite_file, current_bench_id)


def compare_with_previous(current_results, total_tests, suite_name, current_bench_id):
    if current_bench_id == 0:
        print("Nothing to compare with, first run!")
        return

    filename = os.path.join("benchmark_results", "results_{}_{}".format(
        suite_name, current_bench_id))

    with open(filename) as json_file:
        previous_results = json.load(json_file)
        print("New to old ratios. Smaller - better.")
        print("0.2 is five times faster, 5 is five times slower.")
        for i in range(1, total_tests):
            prev = previous_results[str(i)]['avg_runtime']
            cur = current_results[i]['avg_runtime']
            print(cur / prev)
            # if prev > cur:
            #     print("Faster by ", floor(100 * (1 - cur / prev)), "%")
            # else:
            #     print("Slower by ", floor(100 * (1 - prev / cur)), "%")
