import aiger
import time
import random
import itertools

from collections import defaultdict
from pysat.solvers import Minisat22
from aiger_cnf import aig2cnf

import formula_builder as FB
import graph as G

def get_from_cnf(cnf, var):
    if var in cnf:
        return 1
    assert -1 * var in cnf
    return 0

aig = aiger.load("./sorts/BubbleSort_7_4.aig")
g = G.Graph()
g.from_aig(aig)
inputs = [0 for i in range(28)]
inputs[0] = 1
results = g.calculate_schema_on_inputs(inputs)

pool = FB.TPoolHolder()
formula = FB.make_formula_from_my_graph(g, pool)
exec_1 = None
with Minisat22(bootstrap_with=formula) as solver:
    new_assumptions = list()
    for i in range(28):
        iname = 'v' + str(i)
        modifier = -1
        if inputs[i]:
            modifier = 1
        new_assumptions.append(modifier * pool.v_to_id(iname))

    for execution in solver.enum_models(assumptions=new_assumptions):
        exec_1 = execution

for i in range(28):
    o_name = 'o' + str(i)
    var_name = g.output_name_to_node_name[o_name]
    cnf_name = g.output_var_to_cnf_var(o_name, pool)
    print(cnf_name)

    print("Graph: {}, CNF: {}".format(
        results[var_name], get_from_cnf(exec_1, cnf_name)))

# Result - I've tried to replicate the example and it does not get replicated.
# Meaning - the cause of bad observed behaviour is a bug in my code.
# Good news - you can just compare what happens in there vs what happens here.
