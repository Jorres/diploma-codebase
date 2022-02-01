from collections import defaultdict
import copy


class Parser:
    def __init__(self):
        self.input_to_lit = list()
        self.output_to_lit = list()
        self.lit_parents = defaultdict(list)
        self.lit_children = defaultdict(list)

    def parse_header(self, header_line):
        header = header_line.strip().split(" ")
        assert len(header) == 6, "Failed to parse header"
        aag, m, i, l, o, a = header
        m, i, l, o, a = list(map(int, [m, i, l, o, a]))

        assert l == 0, "Latches not supported"
        assert aag == "aag", "Wrong header, `aag` expected"
        assert m == i + a, "Maximum index looks off"
        return m, i, l, o, a

    def parse_inputs(self, input_lines):
        for input_line in input_lines:
            input_lit = int(input_line)
            self.input_to_lit.append(input_lit)
            assert input_lit % 2 == 0

    def parse_outputs(self, output_lines):
        for output_line in output_lines:
            output_lit = int(output_line)
            if output_lit % 2 == 1:
                self.add_edge(output_lit - 1, output_lit)
            self.output_to_lit.append(output_lit)

    def add_edge(self, child, parent):
        if parent not in self.lit_parents[child]:
            self.lit_parents[child].append(parent)
        if child not in self.lit_children[parent]:
            self.lit_children[parent].append(child)

    def maybe_add_negation(self, child, parent):
        if child % 2 == 0:
            self.add_edge(child, parent)
        else:
            self.add_edge(child, parent)
            self.add_edge(child - 1, child)

    def parse_ands(self,  and_lines):
        for and_line in and_lines:
            and_line_split = and_line.split(" ")
            assert len(and_line_split) == 3, f"Wrong and gate string: {and_line}"
            and_lit, left_child, right_child = map(int, and_line_split)

            self.maybe_add_negation(left_child, and_lit)
            self.maybe_add_negation(right_child, and_lit)

    def parse(self, filename):
        with open(filename, 'r') as f:
            lines = f.readlines()

        m, i, l, o, a = self.parse_header(lines[0])
        input_start = 1
        input_end = input_start + i
        self.parse_inputs(lines[input_start:input_end])
        output_end = input_end + o
        self.parse_outputs(lines[input_end:output_end])
        and_end = output_end + a
        self.parse_ands(lines[output_end:and_end])

        # assert len(lines) == 1 + i + o + a, "Parsing anything but I, O, A is yet unsupported"

        return self.lit_parents, self.lit_children, self.input_to_lit, self.output_to_lit


