import sys
import os
from tqdm import tqdm
import json

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from formula_builder import TPoolHolder, make_formula_from_my_graph
from graph import Graph
from pycryptosat import Solver


def find_backbones_in_graph(g):
    pool = TPoolHolder()
    f = make_formula_from_my_graph(g, pool)
    solver = Solver()
    solver.add_clauses(f.clauses)

    false_backbones = list()
    true_backbones = list()

    for name in tqdm(g.node_names):
        cnf_var = pool.v_to_id(name)
        results = list()
        for bit in [-1, 1]:
            assumptions = [bit * cnf_var]
            result, model = solver.solve(assumptions=assumptions)
            results.append(result)
        if results == [True, False]:
            false_backbones.append(name)
        if results == [False, True]:
            true_backbones.append(name)
        assert results != [False, False]

    backbones_info = dict()
    backbones_info["false"] = len(false_backbones)
    backbones_info["true"] = len(true_backbones)
    backbones_info["name"] = g.name
    backbones_info["no_backbones"] = (
        len(g.node_names) - len(false_backbones) - len(true_backbones)
    )
    with open("./hard-instances/backbones/results.txt", "a") as f:
        s = json.dumps(backbones_info, indent=4)
        f.write(f"{s}\n")


def backbones_experiment():
    for dirpath, dnames, fnames in os.walk("./hard-instances"):
        for f in fnames:
            if f.endswith("aag"):
                path = f"{dirpath}/{f}"
                g = Graph(path, "L")
                # g.remove_identical()
                find_backbones_in_graph(g)


if __name__ == "__main__":
    backbones_experiment()
