import pysat
from pysat.solvers import Minisat22


class TPoolHolder():
    def __init__(self, start_from=1):
        self.id_pool = pysat.formula.IDPool(start_from=start_from)

    def v_to_id(self, name):
        return self.id_pool.id(name)

    def id_to_v(self, id):
        return self.id_pool.obj(id)


# Just a simple Tseytin encoding of a schema
# where only AND's and NOT's are present.
def make_formula_from_my_graph(g, pool):
    formula = pysat.formula.CNF()

    for name in g.node_names:
        if name.startswith('i'):
            child = g.children[name][0]
            formula.append([
                -1 * pool.v_to_id(name),
                -1 * pool.v_to_id(child)
            ])
            formula.append([
                pool.v_to_id(name),
                pool.v_to_id(child)
            ])

        if name.startswith('a'):
            left_child, right_child = g.children[name]
            formula.append([
                pool.v_to_id(left_child),
                -1 * pool.v_to_id(name)
            ])
            formula.append([
                pool.v_to_id(right_child),
                -1 * pool.v_to_id(name)
            ])
            formula.append([
                -1 * pool.v_to_id(left_child),
                -1 * pool.v_to_id(right_child),
                pool.v_to_id(name)
            ])

    return formula
