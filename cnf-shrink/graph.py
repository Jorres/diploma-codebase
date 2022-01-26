import aiger

from collections import defaultdict
import utils as U


class Node:
    def __init__(self):
        pass


class Graph:
    def __init__(self, filename):
        aig = aiger.load(filename)

        with open(filename, "r") as f:
            header = f.readline().strip().split(" ")
            if len(header) != 6:
                raise ValueError
            _, max_id, inputs, latches, outputs, ands = header
            if int(latches) > 0:
                raise ValueError

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

    def replace_in_list(self, where, what, with_what):
        for i in range(0, len(where)):
            if where[i] == what:
                where[i] = with_what
                return
        assert False

    def cut_only(self, v):
        pruned_gates = U.PrunedGates(ands=0, nots=0)

        for child in self.children[v]:
            self.parents[child].remove(v)
            if len(self.parents[child]) == 0 and child not in self.outputs:
                pruned_at_child = self.cut_only(child)
                pruned_gates.ands += pruned_at_child.ands
                pruned_gates.nots += pruned_at_child.nots

        # Clean the node from all the structures in the graph
        if v.startswith("a"):
            pruned_gates.ands += 1
        else:
            assert v.startswith("i")
            pruned_gates.nots += 1

        print("Pruning ", v)
        self.children.pop(v)
        self.parents.pop(v)

        self.node_names.remove(v)

        # try:
        #     self.node_names.remove(v)
        # except ValueError:
        #     # Sometimes we replace deleted node name earlier
        #     # in the pruning process to keep topological order
        #     pass

        return pruned_gates

    def prune_pair(self, to_prune, to_leave, are_equivalent):
        assert to_prune != to_leave
        if to_prune in self.outputs and to_leave in self.outputs:
            assert False, "Pruning outputs is unsupported yet"

        # Just to make sure that `to_prune` is topologically later than `to_leave`.
        # TODO this could be optimized, just precalculate topological number once.
        for v in self.node_names:
            if v == to_prune:
                tmp = to_prune
                to_prune = to_leave
                to_leave = tmp
                break
            if v == to_leave:
                break

        if are_equivalent:
            for parent in self.parents[to_prune]:
                self.replace_in_list(self.children[parent], to_prune, to_leave)
                self.parents[to_leave].append(parent)

            if to_prune in self.outputs:
                for output_name in self.output_name_to_node_name:
                    if self.output_name_to_node_name[output_name] == to_prune:
                        self.output_name_to_node_name[output_name] == to_leave
                self.outputs.remove(to_prune)
                self.outputs.add(to_leave)

            return self.cut_only(to_prune)
        else:
            assert False, "Pruning neg-equivalent is unsupported yet"
            # new_inv_name = 'i_new' + str(self.last_new_inv)
            # print("Inserting new inverter node", new_inv_name)
            # self.last_new_inv += 1

            # self.parents[to_leave].append(new_inv_name)
            # self.children[new_inv_name].append(to_leave)

            # for parent in self.parents[to_prune]:
            #     self.replace_in_list(
            #         self.children[parent], to_prune, new_inv_name)
            #     self.parents[new_inv_name].append(parent)

            # if to_prune in self.outputs:
            #     self.outputs.remove(to_prune)
            #     self.outputs.add(new_inv_name)

            # # TODO 'cut' vs 'copy' replace problem
            # self.replace_in_list(self.node_names, to_prune, new_inv_name)
            # return self.cut_only(to_prune) - 1

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

    def to_file(self, filename):
        n_and_gates = len(
            list(filter(lambda name: name.startswith('a'), self.node_names)))
        name_to_literal = dict()
        first_unoccupied_literal = 2 * self.n_inputs + 2

        max_variable_index = self.n_inputs + n_and_gates
        header = f"aag {max_variable_index} {self.n_inputs} 0 {len(self.outputs)} {n_and_gates}\n"

        input_lines = list()
        for input_id in range(self.n_inputs):
            name_to_literal['v' + str(input_id)] = 2 * input_id
            input_lines.append(f"{2 * input_id + 2}\n")

        and_lines = list()
        for node_name in self.node_names:
            if node_name.startswith('i'):
                assert len(self.children[node_name]) == 1
                child = self.children[node_name][0]
                child_literal = name_to_literal[child]
                name_to_literal[node_name] = (child_literal + 1) % 2
            if node_name.startswith('a'):
                assert len(self.children[node_name]) == 2
                left_child, right_child = self.children[node_name]
                left_literal = name_to_literal[left_child]
                right_literal = name_to_literal[right_child]
                name_to_literal[node_name] = first_unoccupied_literal
                first_unoccupied_literal += 2
                and_lines.append(f"{name_to_literal[node_name]} {left_literal} {right_literal}\n")

        output_lines = list()
        for output_name in self.outputs:
            current_output_literal = name_to_literal[output_name]
            output_lines.append(f"{current_output_literal}\n")

        # assert max_variable_index == first_unoccupied_literal / 2 
        print(max_variable_index, first_unoccupied_literal / 2)

        with open(filename, "w+") as f:
            f.write(header)
            f.writelines(input_lines)
            f.writelines(output_lines)
            f.writelines(and_lines)

            for i in range(0, self.n_inputs):
                f.write("i{} v{}\n".format(i, i))
            for i in range(0, len(self.outputs)):
                f.write("o{} o{}\n".format(i, i))

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
