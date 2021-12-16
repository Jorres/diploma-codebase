import aiger
from aiger_cnf import aig2cnf

x, y = map(aiger.atom, ('x', 'y'))
expr = (x & y)
cnf = aig2cnf(expr.aig)
print(cnf.clauses)
print(cnf.input2lit)
print(cnf.output2lit)
