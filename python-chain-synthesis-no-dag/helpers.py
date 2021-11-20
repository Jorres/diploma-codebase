import json
import pysat
import random

from collections import defaultdict


class TPoolHolder():
    '''Holds an instance of pysat idpool'''

    def __init__(self):
        self.vpool = pysat.formula.IDPool()

    def v_to_id(self, char, ids):
        key = json.dumps({'char': char, 'ids': ids})
        return self.vpool.id(key)

    def id_to_v(self, id):
        return self.vpool.obj(id)


def pretty_print_formula(pool, formula):
    for clause in formula.clauses:
        for val in clause:
            print(abs(val) // val, end=" ")
            key = json.loads(pool.id_to_v(abs(val)))
            print(key['char'], key['ids'], end=" ")
        print()


def nth_bit_of(num, bit_id):
    bit_id -= 1
    return (num >> bit_id) & 1


def read_truthtable(lines, curline, n, m):
    f_truthtables = defaultdict(dict)
    curline += 1
    for j in range(0, 2 ** n):
        jth_bits = lines[curline].strip()
        assert(len(jth_bits) == m)
        for i in range(0, m):
            ith_fun_jth_bit = int(jth_bits[i])
            f_truthtables[i + 1][j] = ith_fun_jth_bit
        curline += 1

    return f_truthtables, curline


def read_one_test(lines, curshift):
    curline = curshift
    n, m = map(int, lines[curline].split(" "))
    f_truthtables, curline = read_truthtable(lines, curline, n, m)
    return n, m, f_truthtables, curline


def read_bench_test(lines, curshift):
    curline = curshift
    n, m, result_size = map(int, lines[curline].split(" "))
    f_truthtables, curline = read_truthtable(lines, curline, n, m)
    return n, m, f_truthtables, result_size, curline


def make_random_test(max_n, max_m):
    n = random.randint(2, max_n)
    m = random.randint(2, max_m)
    return make_precise_test(n, m)


def make_precise_test(n, m):
    f_truthtables = defaultdict(dict)

    for i in range(0, m):
        for j in range(0, 2 ** n):
            ith_fun_jth_bit = random.randint(0, 1)
            f_truthtables[i + 1][j] = ith_fun_jth_bit
    return n, m, f_truthtables

