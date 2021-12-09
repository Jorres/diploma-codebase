import fire

import benchmarker as B
import random_tester as R
import schema_generator_pipeline as S


def benchmark(test_suite_filename, description, algo, iterations=1):
    """
    Perform a benchmark on test suite from a file.
    :param test_suite_filename: file to take tests from
    :param description: a string to be stored in benchmark 
    results for easier understanding of the change made
    :param algo: one of `brute`, `fences`
    :param iterations: how many times to run the benchmark
    to reduce runtime drift (default 1)
    """
    B.benchmark(test_suite_filename, description, algo, iterations)
    pass


def run_fixed(filename, max_size, algo):
    """
    Run and validate one test from a file.
    :param filename: name of the file with one defined test
    :param max_size: maximum size of generated schema, in 
    :param algo: one of `brute`, `fences`
    additional nodes
    """
    S.run_fixed(filename, max_size, algo)


def run_random(n, m, amount, max_size, algo):
    """
    Run and validate `amount` tests where size of each 
    test does not exceed `n` in variables and `m` in 
    functions.
    :param n: max number of parameters for boolean function
    :param m: max number of boolean functions
    :param amount: number of tests to generate
    :param max_size: maximum size of generated schema, in 
    :param algo: one of `brute`, `fences`
    additional nodes
    """
    R.run_random(n, m, amount, max_size, algo)


def compare_on_random(n, m, amount, max_size):
    """
    """
    R.compare_on_random(n, m, amount, max_size)


if __name__ == "__main__":
    # import cProfile, pstats
    # profiler = cProfile.Profile()
    # profiler.enable()
    fire.core.Display = lambda lines, out: print(*lines, file=out)
    fire.Fire({
        "benchmark": benchmark,
        "run_fixed": run_fixed,
        "run_random": run_random,
        "compare_on_random": compare_on_random
    })
    # profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('cumtime')
    # stats.print_stats()
    # filename = 'profile.prof'
    # profiler.dump_stats(filename)
