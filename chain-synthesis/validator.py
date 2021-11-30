import helpers as H


def validate(gr, f_truthtables, n, m):
    node_to_f = dict()
    for f in gr.f_to_node:
        node_to_f[gr.f_to_node[f]] = f

    # Check every possible, inputs == bitstring
    for inputs in range(0, 2 ** n):
        propagated_values = dict()
        for v in range(1, n + 1):
            propagated_values[v] = H.nth_bit_of(inputs, v) == 1
        for v in range(n + 1, n + gr.schema_size + 1):
            if gr.node_arity[v] == 2:
                # vertex `v` depends on i, j: j < i < v
                i, j = gr.children[v]

                propagated_values[v] = gr.node_truthtables_2[v][propagated_values[i]
                                                                ][propagated_values[j]]
            else:
                i, j, k = gr.children[v]

                propagated_values[v] = gr.node_truthtables_3[v][propagated_values[i]
                                                                ][propagated_values[j]][propagated_values[k]]

        for target_f in range(1, m + 1):
            v = gr.f_to_node[target_f]
            assert propagated_values[v] == f_truthtables[target_f][inputs], "faulty node {} calculating function {}".format(
                v, target_f)
