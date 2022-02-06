import copy
import aiger

from collections import defaultdict
import utils as U
import aig_parser as P


class Graph:
    def __init__(self, filename, tag, validate_with_aiger=False):
        if validate_with_aiger:
            aiger.load(filename)
            with open(filename, "r") as f:
                header = f.readline().strip().split(" ")
                if len(header) != 6:
                    raise ValueError
                _, max_id, inputs, latches, outputs, ands = header
                if int(latches) > 0:
                    raise ValueError

        lit_parents, lit_children, lit_inputs, lit_outputs = P.Parser().parse(filename)

        topsort = self.make_topsort(lit_parents, lit_children, lit_inputs)

        self.children = defaultdict(list)
        self.parents = defaultdict(list)
        self.node_names = []
        self.tag = tag

        # Since output nodes are also regular gates,
        # we need to store a mapping like: 'o18' -> 'a333'
        self.output_name_to_node_name = dict()

        self.n_inputs = len(lit_inputs)
        self.n_outputs = len(lit_outputs)

        name_to_lit, lit_to_name = self.graph_edges_from_topsort(topsort, lit_children)

        self.source_name_to_lit = name_to_lit
        self.source_lit_to_name = lit_to_name

        for output_id, output_lit in enumerate(lit_outputs):
            output_name = f"o{output_id}"
            self.output_name_to_node_name[output_name] = lit_to_name[output_lit]

        self.name = filename

    def shortname(self):
        if "/" not in self.name:
            return self.name
        return self.name.split("/")[-1]

    def make_topsort(self, lit_parents, lit_children, lit_inputs):
        topsort = list()

        visited = set()
        children_visited = defaultdict(int)
        q = copy.deepcopy(lit_inputs)

        while len(q) > 0:
            v = q.pop(0)
            visited.add(v)
            topsort.append(v)
            for to in lit_parents[v]:
                children_visited[to] += 1
                if to in visited:
                    continue
                if children_visited[to] < len(lit_children[to]):
                    continue
                q.append(to)

        return topsort

    def add_edge(self, child, parent):
        self.children[parent].append(child)
        self.parents[child].append(parent)

    def graph_edges_from_topsort(self, topsort, lit_children):
        last_inv = 0
        last_inp = 0
        last_and = 0

        lit_to_name = dict()
        name_to_lit = dict()
        self.node_to_depth = dict()

        for lit in topsort:
            le = len(lit_children[lit])
            # Zero children mean simple input
            if le == 0:
                name = f"v{last_inp}"
                self.node_to_depth[name] = 0
                last_inp += 1
            # One child means inverter gate
            elif le == 1:
                name = f"i{last_inv}{self.tag}"
                child = lit_to_name[lit_children[lit][0]]
                self.add_edge(child, name)
                self.node_to_depth[name] = self.node_to_depth[child] + 1
                last_inv += 1
            # Two children mean and gate
            elif le == 2:
                name = f"a{last_and}{self.tag}"
                left_child = lit_to_name[lit_children[lit][0]]
                right_child = lit_to_name[lit_children[lit][1]]
                self.add_edge(left_child, name)
                self.add_edge(right_child, name)
                self.node_to_depth[name] = (
                    max(self.node_to_depth[left_child], self.node_to_depth[right_child])
                    + 1
                )
                last_and += 1
            else:
                assert False, "Graph node has wrong number of children"
            lit_to_name[lit] = name
            name_to_lit[name] = lit
            self.node_names.append(name)

        assert len(self.node_names) == len(topsort)
        print("Not gates: {}, and gates: {}".format(last_inv, last_and))
        return name_to_lit, lit_to_name

    def input_var_to_cnf_var(self, input, pool):
        return pool.v_to_id(input)

    def output_var_to_cnf_var(self, output, pool):
        return pool.v_to_id(self.output_name_to_node_name[output])

    # assumes `inputs` is an int, bits of this int correspond to input variables
    # in the schema
    def calculate_schema_on_inputs(self, inputs):
        result = dict()  # map from node_name to calculation result bit on given input

        assert inputs < 2 ** self.n_inputs

        for i in range(self.n_inputs):
            ith_input_var = (inputs & (1 << i)) > 0
            name = f"v{i}"
            result[name] = ith_input_var

        for name in self.node_names:
            if name.startswith("i"):
                child = self.children[name][0]
                assert child in result
                result[name] = not result[child]
            elif name.startswith("a"):
                child_left = self.children[name][0]
                child_right = self.children[name][1]
                assert child_left in result
                assert child_right in result
                result[name] = result[child_left] and result[child_right]

        for name in self.node_names:
            assert name in result

        return result

    def to_file(self, filename):
        # No longer works because of self.name_to_lit absence
        a = len(list(filter(lambda p: p.startswith("a"), self.node_names)))
        m = a + self.n_inputs

        name_to_lit = dict()

        header = f"aag {m} {self.n_inputs} 0 {self.n_outputs} {a}\n"

        input_lines = list()
        first_free_lit = 2

        for input_id in range(self.n_inputs):
            input_lit = first_free_lit
            input_lines.append(f"{input_lit}\n")
            name_to_lit[f"v{input_id}"] = first_free_lit
            first_free_lit += 2

        and_lines = list()
        for name in self.node_names:
            if name.startswith("a"):
                left_name, right_name = self.children[name]
                and_lit = first_free_lit
                left_child_lit = name_to_lit[left_name]
                right_child_lit = name_to_lit[right_name]
                name_to_lit[name] = and_lit
                and_lines.append(f"{and_lit} {left_child_lit} {right_child_lit}\n")
                first_free_lit += 2
            elif name.startswith("i"):
                child = self.children[name][0]
                assert name_to_lit[child] % 2 == 0
                name_to_lit[name] = name_to_lit[child] + 1

        output_lines = list()
        for output_id in range(self.n_outputs):
            output_lit = name_to_lit[self.output_name_to_node_name[f"o{output_id}"]]
            output_lines.append(f"{output_lit}\n")

        with open(filename, "w") as f:
            f.write(header)
            f.writelines(input_lines)
            f.writelines(output_lines)
            f.writelines(and_lines)

    def replace_node_with_other_node(self, to_replace, with_what, to_replace_set):
        to_replace_set.add(to_replace)
        visited_children = set()

        for child in self.children[to_replace]:
            if child in visited_children:
                continue
            U.replace_in_list(self.parents[child], to_replace, with_what)
            visited_children.add(child)

        for parent in self.parents[to_replace]:
            U.replace_in_list(self.children[parent], to_replace, with_what)
            self.parents[with_what].append(parent)

        for output_id in range(self.n_outputs):
            if self.output_name_to_node_name[f"o{output_id}"] == to_replace:
                self.output_name_to_node_name[f"o{output_id}"] = with_what

        for parent in self.parents[to_replace]:
            if parent.startswith("a"):
                left, right = self.children[parent]
                if left == right:
                    self.replace_node_with_other_node(parent, left, to_replace_set)

    def calculate_dists_from(self, name):
        q = [name]
        dist = dict()
        dist[name] = 0

        visited = set()
        visited.add(name)
        while len(q) > 0:
            v = q.pop(0)
            for to in self.children[v] + self.parents[v]:
                if to not in visited:
                    dist[to] = dist[v] + 1
                    q.append(to)
                    visited.add(to)

        return dist

    def get_number_from_name(self, name):
        if name.startswith("v"):
            return name[1:]
        else:
            return name[1:-1]

    def remove_identical(self):
        # These dictionaries map children into nodes. E.g.
        # node a123 has children i100, i101, then
        # in existing_ands there is entry "i100i101" -> a123
        existing_ands = dict()
        existing_nots = dict()

        to_replace = set()
        for node in self.node_names:  # node_names are stored in topological order
            if node in to_replace:
                continue

            if node.startswith("i"):
                assert len(self.children[node]) == 1
                child = self.children[node][0]
                if child in existing_nots:
                    self.replace_node_with_other_node(
                        node, existing_nots[child], to_replace
                    )
                else:
                    existing_nots[child] = node
            elif node.startswith("a"):
                assert len(self.children[node]) == 2
                left, right = self.children[node]

                # Make sure i100i101 and i101i100 actually map to one node
                # by ordering by gate_id.
                # Also, cutting down the last character since it is usually the tag.
                if self.get_number_from_name(left) > self.get_number_from_name(right):
                    tmp = left
                    left = right
                    right = tmp

                and_key = left + right
                if and_key in existing_ands:
                    self.replace_node_with_other_node(
                        node, existing_ands[and_key], to_replace
                    )
                else:
                    existing_ands[and_key] = node

        new_node_names = list()
        for name in self.node_names:
            if name not in to_replace:
                new_node_names.append(name)
        self.node_names = new_node_names

        replaced_ands = list(filter(lambda n: n.startswith("a"), to_replace))
        replaced_nots = list(filter(lambda n: n.startswith("i"), to_replace))

        print(
            f"Removed {len(replaced_ands)}, {len(replaced_nots)} in {self.shortname()}"
        )
