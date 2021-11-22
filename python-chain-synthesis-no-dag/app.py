import fire

import benchmarker as B
import random_tester as R
import schema_generator as S
import suite_generator as G


def generate_suite(n, m, amount, max_size):
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
    """
    G.generate_suite(n, m, amount, max_size)


def benchmark(test_suite_filename, iterations=1):
    """
    Perform a benchmark on test suite from a file.
    :param test_suite_filename: file to take tests from
    :param iterations: how many times to run the benchmark
    to reduce runtime drift (default 1)
    """
    B.benchmark(test_suite_filename, iterations)
    pass


def run_fixed(filename, max_size):
    """
    Run and validate one test from a file.
    :param filename: name of the file with one defined test
    :param max_size: maximum size of generated schema, in 
    additional nodes
    """
    S.run_fixed(filename, max_size)


def run_random(n, m, amount, max_size):
    """
    Run and validate `amount` tests where size of each 
    test does not exceed `n` in variables and `m` in 
    functions.
    :param n: max number of parameters for boolean function
    :param m: max number of boolean functions
    :param amount: number of tests to generate
    :param max_size: maximum size of generated schema, in 
    additional nodes
    """
    R.run_random(n, m, amount, max_size)


if __name__ == "__main__":
    fire.Fire({
        "generate_suite": generate_suite,
        "benchmark": benchmark,
        "run_fixed": run_fixed,
        "run_random": run_random
    })
