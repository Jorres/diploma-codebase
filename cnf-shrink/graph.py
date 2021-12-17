import aiger
from collections import defaultdict
import inspect


class Node:
    def __init__(self):
        pass


class Graph:
    def add_edge(self, child, parent):
        self.children[parent].append(child)
        self.parents[child].append(parent)

    def init_datafields(self):
        self.last_new_inv = 0
        self.children = defaultdict(list)
        self.parents = defaultdict(list)
        self.aig_input_to_short_input = dict()
        self.aig_output_to_short_output = dict()

        self.last_i_gate = 0
        self.last_v_gate = 0
        self.last_a_gate = 0
        self.last_output = 0

        # this is a small custom dict, it has all the node ids
        # and their mapping to names. For example, 
        # 713 is really an inverter to a literal 712. 
        # So it contains two entries, for both 712 and 713, pointing
        # to 2 node objects.
        self.literal_to_node = dict()

    def make_empty_node(self, node_type):
        name = ""
        if node_type == "v":
            name = "v" + str(self.last_v_gate)
            self.last_v_gate += 1
        elif node_type == "i":
            name = "i" + str(self.last_i_gate)
            self.last_i_gate += 1
        elif node_type == "a":
            name = "a" + str(self.last_a_gate)
            self.last_a_gate += 1
        else:
            assert False, "unexpected node_type"

        node = Node()
        node.children = []
        node.name = name
        return node

    def put_into_order(self, order, literal, node):
        order.append(node)
        self.literal_to_node[literal] = node

    def process_child_maybe_negation(self, order, a, b, parent_children):
        b_var_literal = (b - b % 2)

        if b % 2 == 1:
            if b not in self.literal_to_node:
                i_node = self.make_empty_node("i")
                i_node.children = [self.literal_to_node[b_var_literal]]
                self.put_into_order(order, b, i_node)
                parent_children.append(i_node)
            else:
                parent_children.append(self.literal_to_node[b])
        else:
            parent_children.append(self.literal_to_node[b_var_literal])

    def from_file(self, filename):
        lines = []
        with open(filename) as f:
            lines = f.readlines()
        first_line_vals = lines[0].split(" ")
        assert len(first_line_vals) == 6, "Unexpected header"
        header = lines[0].split(" ")
        header.pop(0)

        n, n_inputs, l, n_outputs, n_ands = map(int, header)

        order = []
        aig_outputs = []

        self.init_datafields()

        # Populating order by entities that have only `children []` and `names`
        for i in range(0, n_inputs):
            vnode = self.make_empty_node("v")
            input_literal = int(lines[i + 1]) 
            assert input_literal % 2 == 0, "Even input literal assumption failed"
            self.put_into_order(order, input_literal, vnode)

        for i in range(0, n_ands):
            a, b, c = map(int, lines[i + n_inputs + n_outputs + 1].split(" "))
            anode = self.make_empty_node("a")
            self.process_child_maybe_negation(order, a, b, anode.children)
            self.process_child_maybe_negation(order, a, c, anode.children)
            assert len(anode.children) == 2, "And gate doesn't have length 2"
            self.put_into_order(order, a, anode)

        for i in range(0, n_outputs):
            o = int(lines[i + 1 + n_inputs])
            if o % 2 == 1:
                assert o not in self.literal_to_node, 'The same output meets twice'
                inode = self.make_empty_node("i")
                i_literal = o
                son_literal = o - 1
                inode.children = [self.literal_to_node[son_literal]]
                self.put_into_order(order, i_literal, inode)
            else:
                # do nothing, the node has already been inserted
                # it is `and` gate or an input
                pass
            aig_outputs.append("o" + str(self.last_output))
            self.last_output += 1

        last_input = 0
        last_inv = 0
        last_and = 0

        node_names = []
        node_to_name = dict()

        print("Total vertices in graph:", len(order))

        name = ""
        for i in order:
            le = len(i.children)
            # Zero children mean simple input
            if le == 0:
                name = 'v' + str(last_input)
                last_input += 1
                self.aig_input_to_short_input[i.name] = name
            # One child means inverter gate
            if le == 1:
                name = 'i' + str(last_inv)
                prename = node_to_name[i.children[0]]
                self.add_edge(prename, name)
                last_inv += 1
            # Two children mean and gate
            if le == 2:
                name = 'a' + str(last_and)
                prename_left = node_to_name[i.children[0]]
                prename_right = node_to_name[i.children[1]]
                self.add_edge(prename_left, name)
                self.add_edge(prename_right, name)
                last_and += 1

            node_to_name[i] = name
            node_names.append(name)

        assert last_and == self.last_a_gate
        assert last_input == self.last_v_gate
        assert last_inv == self.last_i_gate

        outputs = set()

        for output in aig_outputs:
            self.aig_output_to_short_output[output] = output
            outputs.add(output)

        print('Inputs', self.aig_input_to_short_input)
        print('Outputs', self.aig_output_to_short_output)

        self.node_names = node_names
        self.outputs = outputs

        self.debug_print()

    def from_aig(self, aig):
        last_input = 0
        last_inv = 0
        last_and = 0
        self.last_new_inv = 0

        node_names = []
        node_to_name = dict()

        self.children = defaultdict(list)
        self.parents = defaultdict(list)
        self.aig_input_to_short_input = dict()
        self.aig_output_to_short_output = dict()

        order = aiger.common.eval_order(aig)

        print("Total vertices in graph:", len(order))

        name = ""
        for i in order:
            le = len(i.children)
            # Zero children mean simple input
            if le == 0:
                name = 'v' + str(last_input)
                last_input += 1
                self.aig_input_to_short_input[i.name] = name
            # One child means inverter gate
            if le == 1:
                name = 'i' + str(last_inv)
                prename = node_to_name[i.children[0]]
                self.add_edge(prename, name)
                last_inv += 1
            # Two children mean and gate
            if le == 2:
                name = 'a' + str(last_and)
                prename_left = node_to_name[i.children[0]]
                prename_right = node_to_name[i.children[1]]
                self.add_edge(prename_left, name)
                self.add_edge(prename_right, name)
                last_and += 1

            node_to_name[i] = name
            node_names.append(name)

        outputs = set()

        for output in aig.outputs:
            assert output in aig.node_map
            self.aig_output_to_short_output[output] = node_to_name[aig.node_map[output]]
            outputs.add(node_to_name[aig.node_map[output]])
        print('Inputs', self.aig_input_to_short_input)
        print('Outputs', self.aig_output_to_short_output)

        self.node_names = node_names
        self.outputs = outputs
        self.debug_print()

    def replace_in_list(self, children, what, with_what):
        for i in range(0, len(children)):
            if children[i] == what:
                children[i] = with_what
                return
        assert False, "Failed to substitute in parent of a pruned node"

    def cut_only(self, v):
        ans = 0
        for child in self.children[v]:
            self.parents[child].remove(v)
            if len(self.parents[child]) == 0 and child not in self.outputs:
                ans += self.cut_only(child)

        # Clean the node from all the structures in the graph
        ans += 1
        print("removing", v)
        self.children.pop(v)
        self.parents.pop(v)

        try:
            self.node_names.remove(v)
        except ValueError:
            # Sometimes we replace deleted node name
            # earlier in the pruning process to keep topological
            # order 
            pass
        return ans

    def update_aig_output_mapping(self, old_value, new_value):
        # Here we iterate over the whole mapping because I don't
        # want to precalculate and store one more data memoization.
        for aig_name, old_stored_value in self.aig_output_to_short_output:
            if old_stored_value == old_value:
                self.aig_output_to_short_output[aig_name] = new_value
                return
        assert False, "Previous output to replace not found"

    def prune(self, to_prune, to_leave, are_equivalent):
        # self.debug_print()
        if to_prune in self.outputs and to_leave in self.outputs:
            assert False, "Pruning one of two outputs is unsupported yet"

        # TODO this could be optimized, just precalculate topological number once
        for v in self.node_names:
            if v == to_prune:
                tmp = to_prune
                to_prune = to_leave
                to_leave = tmp
                break
            if v == to_leave:
                break

        was_new_inverter_added = False
        # From here, `and_b` is topologically earlier than `and_a`.

        if are_equivalent:
            for parent in self.parents[to_prune]:
                self.replace_in_list(self.children[parent], to_prune, to_leave)
                self.parents[to_leave].append(parent)
            if to_prune in self.outputs:
                self.update_aig_output_mapping(to_prune, to_leave)
                self.outputs.remove(to_prune)
                self.outputs.add(to_leave)
        else:
            new_inv_name = 'i_new' + str(self.last_new_inv)
            print("Inserting new inverter node", new_inv_name)
            was_new_inverter_added = True
            self.last_new_inv += 1

            self.parents[to_leave].append(new_inv_name)
            self.children[new_inv_name].append(to_leave)

            for parent in self.parents[to_prune]:
                self.replace_in_list(
                    self.children[parent], to_prune, new_inv_name)
                self.parents[new_inv_name].append(parent)

            if to_prune in self.outputs:
                self.update_aig_output_mapping(to_prune, new_inv_name)
                self.outputs.remove(to_prune)
                self.outputs.add(new_inv_name)

            self.replace_in_list(self.node_names, to_prune, new_inv_name)

        res = self.cut_only(to_prune)
        if was_new_inverter_added:
            res -= 1
        return res

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

    def what_input_var(self, aig_input_name, pool):
        short_name = self.aig_input_to_short_input[aig_input_name]
        return pool.v_to_id(short_name)

    def what_output_var(self, aig_output_name, pool):
        short_name = self.aig_output_to_short_output[aig_output_name]
        return pool.v_to_id(short_name)
