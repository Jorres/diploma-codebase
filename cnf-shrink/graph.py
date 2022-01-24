import aiger

from collections import defaultdict


class Node:
    def __init__(self):
        pass


class Graph:
    def __init__(self, filename):
        aig = aiger.load(filename)
        self.from_aig(aig)

    def add_edge(self, child, parent):
        self.children[parent].append(child)
        self.parents[child].append(parent)

    def init_datafields(self):
        self.children = defaultdict(list)
        self.parents = defaultdict(list)
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
                child = node_to_name[i.children[0]]
                self.add_edge(child, name)
                last_inv += 1
            # Two children mean and gate
            elif le == 2:
                name = 'a' + str(last_and)
                left_child = node_to_name[i.children[0]]
                right_child = node_to_name[i.children[1]]
                self.add_edge(left_child, name)
                self.add_edge(right_child, name)
                last_and += 1
            else:
                assert False, "Graph node has wrong number of children"
            node_to_name[i] = name
            self.node_names.append(name)

        assert len(self.node_names) == len(order)
        print("Not gates: {}, and gates: {}".format(last_inv, last_and))
        return node_to_name

    def from_aig(self, aig):
        self.init_datafields()

        # Gives topological sorting of the graph
        # old_order = aiger.common.eval_order(aig)

        # order_layers = aiger.common.eval_order(aig, concat=False)
        # order_layers = list(order_layers)[::-1]
        # order = funcy.lcat(order_layers)

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

    # assumes `inputs` is an int, bits of this int correspond to input variables
    # in the schema
    def calculate_schema_on_inputs(self, inputs):
        result = dict()  # map from node_name to node value on these inputs

        assert inputs < 2 ** self.n_inputs

        for i in range(self.n_inputs):
            ith_input_var = (inputs & (1 << i)) > 0
            name = 'v' + str(i)
            result[name] = ith_input_var
            print(name)

        for name in self.node_names:
            if name.startswith('i'):
                child = self.children[name][0]
                print(name, child)
                assert child in result
                result[name] = not result[child]
            elif name.startswith('a'):
                child_left = self.children[name][0]
                child_right = self.children[name][1]
                print(name, child_left, child_right)
                assert child_left in result
                assert child_right in result
                result[name] = result[child_left] and result[child_right]

        for name in self.node_names:
            assert name in result

        return result

    def relabel_graph_in_top_to_bottom_fashion(self):
        relabeling = dict()
        queue = list()
        visited = set()

        last_inv = 0
        last_and = 0

        new_node_names = list()

        for input_id in range(self.n_inputs):
            input_name = 'v' + str(input_id)
            queue.append(input_name)

        while queue:
            v = queue.pop(0)

            if v.startswith('i'):
                relabeling[v] = 'i' + str(last_inv)
                last_inv += 1
            elif v.startswith('a'):
                relabeling[v] = 'a' + str(last_and)
                last_and += 1
            else:
                relabeling[v] = v

            new_node_names.append(relabeling[v])

            for to in self.parents[v]:
                if to not in visited:
                    queue.append(to)
                    visited.add(to)

        new_children = defaultdict(list)
        new_parents = defaultdict(list)

        for gate in self.node_names:
            new_gate = relabeling[gate]
            for old_parent in self.parents[gate]:
                new_parents[new_gate].append(relabeling[old_parent])
            for old_child in self.children[gate]:
                new_children[new_gate].append(relabeling[old_child])

        self.children = new_children
        self.parents = new_parents
        self.node_names = new_node_names

        # output_name_to_node_name
        for output_id in range(len(self.outputs)):
            output_name = 'o' + str(output_id)
            old = self.output_name_to_node_name[output_name]
            self.output_name_to_node_name[output_name] = relabeling[old]


