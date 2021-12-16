import aiger
from collections import defaultdict
import inspect


class Graph:
    def add_edge(self, child, parent):
        self.children[parent].append(child)
        self.parents[child].append(parent)

    def __init__(self, aig):
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
                print(i.name)
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
        print("Outputs: ", outputs)

        self.node_names = node_names
        self.outputs = outputs

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
            # to keep top-sort
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
        # self.debug_print()

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
