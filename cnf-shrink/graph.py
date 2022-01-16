import aiger

from collections import defaultdict


class Node:
    def __init__(self):
        pass


class Graph:
    def add_edge(self, child, parent):
        self.children[parent].append(child)

    def init_datafields(self):
        self.children = defaultdict(list)
        self.node_names = []

        # Since output nodes are also regular gates,
        # we need to store a mapping like: 'o18' -> 'i333'
        self.output_name_to_node_name = dict()

        self.n_inputs = 0

    def graph_edges_from_topsort(self, order, aig):
        last_inv = 0
        last_and = 0

        node_to_name = dict()
        name = ""
        for i in order:
            le = len(i.children)
            # Zero children mean simple input
            if le == 0:
                name = i.name
                self.n_inputs += 1
            # One child means inverter gate
            elif le == 1:
                name = 'i' + str(last_inv)
                prename = node_to_name[i.children[0]]
                self.add_edge(prename, name)
                last_inv += 1
            # Two children mean and gate
            elif le == 2:
                name = 'a' + str(last_and)
                prename_left = node_to_name[i.children[0]]
                prename_right = node_to_name[i.children[1]]
                self.add_edge(prename_left, name)
                self.add_edge(prename_right, name)
                last_and += 1
            else:
                assert False, "Graph node has wrong number of children"
            node_to_name[i] = name
            self.node_names.append(name)

        assert len(self.node_names) == len(order)
        return node_to_name

    def from_aig(self, aig):
        self.init_datafields()

        # Gives topological sorting of the graph
        order = aiger.common.eval_order(aig)
        print("Total vertices in graph:", len(order))

        node_to_name = self.graph_edges_from_topsort(order, aig)

        self.outputs = set()
        for output in aig.outputs:
            assert output in aig.node_map
            output_node_name = node_to_name[aig.node_map[output]]
            self.output_name_to_node_name[output] = output_node_name
            self.outputs.add(output_node_name)

    def debug_print(self):
        print("-----   DEBUG PRINTING GRAPH   -----")
        for name in self.node_names:
            print(name, end=' ')
            if len(self.children[name]) == 2:
                print(self.children[name][0],
                      self.children[name][1])
            elif len(self.children[name]) == 1:
                print(self.children[name][0])
            else:
                print()
        print("----- END DEBUG PRINTING GRAPH -----")

    def input_var_to_cnf_var(self, input, pool):
        return pool.v_to_id(input)

    def output_var_to_cnf_var(self, output, pool):
        return pool.v_to_id(self.output_name_to_node_name[output])

    def calculate_schema_on_inputs(self, inputs):
        result = dict()  # map from node_name to node value on these inputs
        for i, input_val in enumerate(inputs):
            name = 'v' + str(i)
            result[name] = inputs[i]

        for name in self.node_names:
            if name.startswith('i'):
                child = self.children[name][0]
                assert child in result
                result[name] = not result[child]
            elif name.startswith('a'):
                child_left = self.children[name][0]
                child_right = self.children[name][1]
                assert child_left in result
                assert child_right in result
                result[name] = result[child_left] and result[child_right]

        for name in self.node_names:
            assert name in result

        return result
