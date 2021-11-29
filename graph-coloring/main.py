import sys
from pysat.formula import CNF
from pysat.solvers import Lingeling


global last_var_id
last_var_id = 1
global v_to_id_dict
v_to_id_dict = dict()
global id_to_v_dict
id_to_v_dict = dict()


def v_to_id(v, color):
    global last_var_id

    key = str(v) + "_" + str(color)

    if key not in v_to_id_dict:
        v_to_id_dict[key] = last_var_id
        id_to_v_dict[last_var_id] = [v, color]
        last_var_id += 1
    return v_to_id_dict[key]


def id_to_v(id):
    return id_to_v_dict[id]


def read(filename):
    f = open(filename, "r")
    lines = f.readlines()
    f.close()

    n, m = map(int, lines[0].split(' '))
    return n, m, lines


def build_formula(n, m, lines, colors):
    formula = CNF()

    colors = list(range(1, colors + 1))

    # A variable is colored at least once
    for v in range(1, n + 1):
        formula.append(list(map(lambda color: v_to_id(v, color), colors)))

    # Ends of an edge are colored differently
    for line in lines[1:]:
        a, b = map(int, line.split(' '))
        for color in colors:
            formula.append([-v_to_id(a, color), -v_to_id(b, color)])

    return formula


def try_solve(formula):
    with Lingeling(bootstrap_with=formula.clauses, with_proof=True) as ling:
        solution_exists = ling.solve()
        if solution_exists is False:
            print(ling.get_proof())
        return solution_exists, ling.get_model()


def interpret(model):
    for variable in model:
        if variable > 0:
            v, color = id_to_v(variable)
            print("Vertex", v, "is colored with color", color)


def main():
    max_colors = int(sys.argv[1])
    filename = sys.argv[2]

    n, m, lines = read(filename)
    global_solved = False
    for colors in range(2, max_colors):
        formula = build_formula(n, m, lines, colors)
        solved, model = try_solve(formula)
        if solved:
            global_solved = True
            interpret(model)
            break

    if not global_solved:
        print("No solution for colors 1 to", max_colors)


main()
