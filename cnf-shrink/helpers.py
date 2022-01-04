import pysat
from pysat.solvers import Minisat22


class TPoolHolder():
    def __init__(self, start_from=1):
        self.vpool = pysat.formula.IDPool(start_from=start_from)

    def v_to_id(self, name):
        return self.vpool.id(name)

    def id_to_v(self, id):
        return self.vpool.obj(id)


def make_formula_from_my_graph(g, pool):
    formula = pysat.formula.CNF()

    for name in g.node_names:
        if name.startswith('i'):
            prev_name = g.children[name][0]
            formula.append([
                -1 * pool.v_to_id(name),
                -1 * pool.v_to_id(prev_name)
            ])
            formula.append([
                pool.v_to_id(name),
                pool.v_to_id(prev_name)
            ])
        if name.startswith('a'):
            prev_left_name = g.children[name][0]
            prev_right_name = g.children[name][1]

            formula.append([
                pool.v_to_id(prev_left_name),
                -1 * pool.v_to_id(name)
            ])
            formula.append([
                pool.v_to_id(prev_right_name),
                -1 * pool.v_to_id(name)
            ])
            formula.append([
                -1 * pool.v_to_id(prev_left_name),
                -1 * pool.v_to_id(prev_right_name),
                pool.v_to_id(name)
            ])
    return formula
