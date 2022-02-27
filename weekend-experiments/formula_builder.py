import pysat
from pysat.solvers import Minisat22


class TPoolHolder():
    def __init__(self, start_from=1):
        self.id_pool = pysat.formula.IDPool(start_from=start_from)

    def v_to_id(self, name):
        return self.id_pool.id(name)

    def id_to_v(self, id):
        return self.id_pool.obj(id)


class PicklablePool:
    def __init__(self):
        self.v_to_id_dict = dict()
        self.id_to_v_dict = dict()
        self.cnt = 1

    def v_to_id(self, name):
        if name not in self.v_to_id_dict:
            self.v_to_id_dict[name] = self.cnt
            self.id_to_v_dict[self.cnt] = name
            self.cnt += 1

        return self.v_to_id_dict[name]


    def id_to_v(self, id):
        assert id in self.id_to_v_dict
        return self.id_to_v_dict[id]


def skip_nots(g, node):
    modifier = 1
    while node.startswith("i"):
        assert len(g.children[node]) == 1
        node = g.children[node][0]
        modifier *= -1
    return node, modifier


def encode_and(formula, v, l, r, g, pool):
    # l, modifier_l = skip_nots(g, l)
    # r, modifier_r = skip_nots(g, r)

    # l_lit = pool.v_to_id(l) * modifier_l
    # r_lit = pool.v_to_id(r) * modifier_r
    l_lit = pool.v_to_id(l)
    r_lit = pool.v_to_id(r)
    and_lit = pool.v_to_id(v)

    formula.append([
        l_lit,
        -1 * and_lit
    ])
    formula.append([
        r_lit,
        -1 * and_lit
    ])
    formula.append([
        -1 * l_lit,
        -1 * r_lit,
        and_lit
    ])


def encode_output_not(formula, v, child, pool):
    formula.append([
        -1 * pool.v_to_id(v),
        -1 * pool.v_to_id(child)
    ])
    formula.append([
        pool.v_to_id(v),
        pool.v_to_id(child)
    ])


def process_node(formula, g, name, pool):
    if name.startswith('i'): # and name in g.output_node_names:
        child = g.children[name][0]
        encode_output_not(formula, name, child, pool)

    if name.startswith('a'):
        l, r = g.children[name]
        encode_and(formula, name, l, r, g, pool)


def make_formula_from_my_graph(g, pool):
    formula = pysat.formula.CNF()

    for name in g.node_names:
        process_node(formula, g, name, pool)

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
            process_node(formula, g1, g1.node_names[p1], pool)
            p1 += 1
        else:
            process_node(formula, g2, g2.node_names[p2], pool)
            p2 += 1

    while p1 < len(g1.node_names):
        process_node(formula, g1, g1.node_names[p1], pool)
        p1 += 1

    while p2 < len(g2.node_names):
        process_node(formula, g2, g2.node_names[p2], pool)
        p2 += 1
    return formula


def generate_miter_without_xor(shared_cnf, pool, g1, g2):
    assert g1.n_inputs == g2.n_inputs
    return shared_cnf


def append_xor_to_miter(shared_cnf, pool, g1, g2, mode):
    for output_id in range(g1.n_outputs):
        # Add clause for output xor gate
        xor_gate = pool.v_to_id(f"xor_{output_id}")
        output_code_name = f"o{output_id}"
        left_output = g1.output_var_to_cnf_var(output_code_name, pool)
        right_output = g2.output_var_to_cnf_var(output_code_name, pool)

        # XOR Tseytin encoding
        # xorgate <=> left xor right
        shared_cnf.append([-1 * left_output, -1 * right_output, -1 * xor_gate])
        shared_cnf.append([left_output, right_output, -1 * xor_gate])
        shared_cnf.append([left_output, -1 * right_output, xor_gate])
        shared_cnf.append([-1 * left_output, right_output, xor_gate])

    if mode == "or":
        # OR together all new xor_ variables
        lst = []
        for output_id in range(g1.n_outputs):
            lst.append(pool.v_to_id(f"xor_{output_id}"))
        shared_cnf.append(lst)
    elif mode == "stairs":
        # construct a ladder-like structure from OR's
        a = "xor_0"
        for output_id in range(1, g1.n_outputs):
            c = f"stairs_or_{output_id}"
            b = f"xor_{output_id}"

            a_var = pool.v_to_id(a)
            b_var = pool.v_to_id(b)
            c_var = pool.v_to_id(c)

            shared_cnf.append([a_var, b_var, -1 * c_var])
            shared_cnf.append([-1 * a_var, c_var])
            shared_cnf.append([-1 * b_var, c_var])

            a = c

        shared_cnf.append([pool.v_to_id(a)])
    else:
        assert False

    return shared_cnf


def generate_miter_scheme(shared_cnf, pool, g1, g2, mode="or"):
    generate_miter_without_xor(shared_cnf, pool, g1, g2)
    return append_xor_to_miter(shared_cnf, pool, g1, g2, mode)
