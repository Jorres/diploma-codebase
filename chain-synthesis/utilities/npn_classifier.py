import os 

from itertools import permutations

import helpers as H


def what_function(f, perm, neg):
    # 0 0 0 0 => 0
    # 0 0 0 1 => 0
    # . . . .
    # 1 1 1 0 => 0
    # 1 1 1 1 => 0
    r_f = 0
    for var_set in range(0, 2 ** 4):
        var_set_neg = var_set ^ neg
        # print(var_set, var_set_neg)
        var_set_neg_perm = 0
        for bit_id in range(0, 4):
            bit = H.nth_bit_of(var_set_neg, perm[bit_id] + 1)
            if bit == 1:
                var_set_neg_perm |= (1 << bit_id)
        # print("vsnp", var_set_neg_perm)

        # var_set = 1, that corresponds to 0001
        # var_set_neg_perm = 0 that corresponds to 0000 of initial f
        # initial f gave zero on that
        if H.nth_bit_of(f, var_set_neg_perm + 1) == 1:
            r_f |= (1 << var_set)
    return r_f


def give_representatives(n):
    which_repr = dict()
    fs = set()
    for f in range(0, 2 ** (2 ** n)):
        compl_f = (~f) % (1 << 2 ** n)
        print(f, compl_f)

        min_f = 2 ** (2 ** n) + 1
        for perm in permutations(list(range(0, n))):
            for neg in range(0, 2 ** n):
                # here:
                # neg encodes negation of 4 variables,
                # perm encodes permutations of these variables.
                fsh = what_function(f, perm, neg)
                if fsh < min_f:
                    min_f = fsh
                fsh = what_function(compl_f, perm, neg)
                if fsh < min_f:
                    min_f = fsh
        print(len(fs))
        fs.add(min_f)
    return list(fs)


if __name__ == "__main__":
    for i in range(0, 10):
        assert what_function(i, [0, 1, 2, 3], 0) == i
    assert what_function(2, [1, 0, 2, 3], 0) == 4

    # 0000 0\1
    # 0001 0\2
    # 0010 0\4
    # 0011 0\8
    # 0100
    # 0101
    # 0110

    # f = 0 is the function that spits 0 on all inputs.
    # f = 1  is the function that spits 1 on 0000 only.
    # f = 2 is the function that spits 1 on 0001 only.
    # f = 3 is the function that spits 1 on 0001, 0000 only.
    # f = 4 is the function that spits 1 on 0010 only.
    # f = 8 is the function that spits 1 on 0100 only.


    n = 4
    with open(os.path.join('test_suites', 'suite_4npn'), 'w+') as file:
        for f in give_representatives(n):
            file.write("4 1\n")
            for bit in range(0, 2 ** n):
                file.write(str(H.nth_bit_of(f, bit + 1)) + "\n")

# In order to find the representative ^f for a given function
# f, one needs to visit all functions in [f] to find the smallest
# one. If f has no helpful properties—such as symmetries in the
# inputs — one needs to apply all possible
# combinations of 2^n input negations and n! input permutations
# for both f and !f.
