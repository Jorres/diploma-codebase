import json
import os
import os.path

import helpers as H
import schema_generator_pipeline as S


def benchmark(test_suite_file, description, mode, iterations):
    test_suite_file = os.path.basename(test_suite_file)
    f = open(os.path.join("test_suites", test_suite_file), "r")
    lines = f.readlines()
    f.close()

    schema_generator = S.TSchemaPipeline(
        should_pretty_print=False, mode=mode)

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
    total_time = 0
    while curshift < len(lines):
        n, m, f_truthtables, curshift = H.read_one_test(
            lines, curshift)
        print("Benchmarking example ", test_id)
        test_time = 0
        test_result = dict()
        test_result['test_id'] = test_id
        gr = schema_generator.generate_schema(
            n, m, f_truthtables, 20)
        test_time += schema_generator.acc_time
        if mode == "fences":
            test_result['time_per_topology'] = schema_generator.time_per_topology
        test_result['total_runtime'] = schema_generator.acc_time
        test_result['sat_runtime'] = schema_generator.last_sat_attempt_time
        test_result['schema_size'] = gr.schema_size

        total_time += test_time
        benchmark_results[test_id] = test_result
        test_id += 1

    benchmark_results['total_average_time'] = total_time / test_id
    benchmark_results['total_time'] = total_time

    with open(filename, "w+") as resultfile:
        resultfile.write(json.dumps(benchmark_results, indent=4))
