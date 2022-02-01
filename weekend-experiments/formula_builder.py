import pysat
from pysat.solvers import Minisat22


class TPoolHolder():
    def __init__(self, start_from=1):
        self.id_pool = pysat.formula.IDPool(start_from=start_from)

    def v_to_id(self, name):
        return self.id_pool.id(name)

    def id_to_v(self, id):
        return self.id_pool.obj(id)


def encode_and(formula, v, l, r, pool):
    formula.append([
        pool.v_to_id(l),
        -1 * pool.v_to_id(v)
    ])
    formula.append([
        pool.v_to_id(r),
        -1 * pool.v_to_id(v)
    ])
    formula.append([
        -1 * pool.v_to_id(l),
        -1 * pool.v_to_id(r),
        pool.v_to_id(v)
    ])


def encode_not(formula, v, child, pool):
    formula.append([
        -1 * pool.v_to_id(v),
        -1 * pool.v_to_id(child)
    ])
    formula.append([
        pool.v_to_id(v),
        pool.v_to_id(child)
    ])


def process_node(formula, g, name, pool, tag):
    if name.startswith('i'):
        child = g.children[name][0]
        encode_not(formula, name, child, pool)

    if name.startswith('a'):
        l, r = g.children[name]
        encode_and(formula, name, l, r, pool)


def make_formula_from_my_graph(g, pool):
    formula = pysat.formula.CNF()

    for name in g.node_names:
        process_node(formula, g, name, pool, None)

    return formula


# The trick of this function is to encode both schemas
# more or less simultaneously, top-to-bottom. In this way
# XOR variables in miter will be closer index-wise, this
# may help the solver as it relies on cnf variable order.
def make_united_miter_from_two_graphs(g1, g2, pool):
    ratio = len(g1.node_names) / len(g2.node_names)
    formula = pysat.formula.CNF()

    p1 = 0
    p2 = 0

    while p1 < len(g1.node_names) and p2 < len(g2.node_names):
        cur_ratio = (p1 + 1) / (p2 + 1)
        if cur_ratio < ratio:
            process_node(formula, g1, g1.node_names[p1], pool, "L")
            p1 += 1
        else:
            process_node(formula, g2, g2.node_names[p2], pool, "R")
            p2 += 1

    while p1 < len(g1.node_names):
        process_node(formula, g1, g1.node_names[p1], pool, "L")
        p1 += 1

    while p2 < len(g2.node_names):
        process_node(formula, g2, g2.node_names[p2], pool, "R")
        p2 += 1
    return formula
