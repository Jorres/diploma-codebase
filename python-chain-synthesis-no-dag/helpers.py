import json 
import pysat

vpool = pysat.formula.IDPool()


def v_to_id(char, ids):
    key = json.dumps({'char': char, 'ids': ids})
    return vpool.id(key)


def id_to_v(id):
    return vpool.obj(id)


def clean_pool():
    # Temporary hack, for some reason `vpool.restart()` didn't work,
    # debug later, rn irrelevant
    vpool = pysat.formula.IDPool()


def pretty_print_formula(formula):
    for clause in formula.clauses:
        for val in clause:
            print(abs(val) // val, end=" ")
            key = json.loads(id_to_v(abs(val)))
            print(key['char'], key['ids'], end=" ")
        print()


def nth_bit_of(num, bit_id):
    bit_id -= 1
    return (num >> bit_id) & 1

