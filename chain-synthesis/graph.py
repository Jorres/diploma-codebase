import json
from collections import defaultdict


class TGraph:
    def __init__(self, r, model, pretty_print, pool):
        if pretty_print:
            print("The schema consists of", r, "additional nodes")

        gr = dict()
        f_to_node = dict()

        node_truthtables_2 = defaultdict(lambda: defaultdict(dict))
        node_truthtables_3 = defaultdict(
            lambda: defaultdict(lambda: defaultdict(dict)))

        node_arity = dict()

        for variable in model:
            key = json.loads(pool.id_to_v(abs(variable)))

            if key['char'] == "g":
                if variable > 0:
                    h, i = key['ids']
                    f_to_node[h] = i
                    if pretty_print:
                        print("Output", h, "is located at vertex", i)

            if key['char'] == "f":
                i, b, c = key['ids']
                result = variable > 0
                node_truthtables_2[i][b][c] = result
                node_truthtables_2[i][0][0] = False
                if pretty_print:
                    print("Vertex", i, "produces from", b, c,
                          "value", result)

            if key['char'] == "z":
                i, b, c, d = key['ids']
                result = variable > 0
                node_truthtables_3[i][b][c][d] = result
                if pretty_print:
                    print("Vertex", i, "produces from", b, c, d,
                          "value", result)

            if key['char'] == "s":
                i, j, k = key['ids']
                if variable > 0:
                    assert (i not in node_arity) or (node_arity[i] == 2)
                    node_arity[i] = 2
                    gr[i] = (j, k)
                    if pretty_print:
                        print("Vertex", i, "is calculated from", j, k)

            if key['char'] == "q":
                i, j, k, p = key['ids']
                if variable > 0:
                    assert (i not in node_arity) or (node_arity[i] == 3)
                    node_arity[i] = 3
                    gr[i] = (j, k, p)
                    if pretty_print:
                        print("Vertex", i, "is calculated from", j, k, p)

            self.children = gr
            self.node_truthtables_2 = node_truthtables_2
            self.node_truthtables_3 = node_truthtables_3
            self.f_to_node = f_to_node
            self.node_arity = node_arity
            self.schema_size = r
