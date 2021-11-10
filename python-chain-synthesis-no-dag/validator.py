import helpers as H


def validate(gr, f_to_node, f_truthtables, node_truthtables,
             n, m, schema_size):
    for inputs in range(0, 2 ** n):
        propagated_values = dict()
        for v in range(1, n + 1):
            propagated_values[v] = H.nth_bit_of(inputs, v) == 1
        for v in range(n + 1, n + schema_size + 1):
            # vertex `v` depends on i, j: j < i < v
            i, j = gr[v]
            propagated_values[v] = node_truthtables[v][propagated_values[i]][propagated_values[j]]

        for target_f in range(1, m + 1):
            assert(propagated_values[f_to_node[target_f]] ==
                   f_truthtables[target_f][inputs])
