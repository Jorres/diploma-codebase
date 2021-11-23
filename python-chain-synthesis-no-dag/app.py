import fire

import benchmarker as B
import random_tester as R
import schema_generator_pipeline as S
import suite_generator as G


def generate_suite(n, m, amount, max_size, allow_small_s="false"):
    """
    Run a long, long computation that prints to
    `benchmark_results/*.txt` several tests that run SAT 
    longer than 1 second.

    Generated tests may not be smallest
    in terms of schema size due to generation algorithm
    limiting SAT execution time to avoid long UNSATs.

    :param n: number of parameters for boolean function
    :param m: number of boolean functions
    :param amount: number of tests to generate
    :param max_size: maximum size of generated schema, in 
    additional nodes
    :param allow_small: generate small tests. Useful for 
    testing a whole benchmark pipeline without waiting for 
    too long.
    """
    allow_small = allow_small_s.lower() == "true"
    G.generate_suite(n, m, amount, max_size, allow_small)


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


if __name__ == "__main__":
    import cProfile, pstats
    profiler = cProfile.Profile()
    profiler.enable()
    fire.Fire({
        "generate_suite": generate_suite,
        "benchmark": benchmark,
        "run_fixed": run_fixed,
        "run_random": run_random
    })
    profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('cumtime')
    # stats.print_stats()
    filename = 'profile.prof'
    profiler.dump_stats(filename)

# %load_ext snakeviz
# %snakeviz main()
