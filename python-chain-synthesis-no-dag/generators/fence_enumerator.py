from itertools import permutations


def partitions(n):
    if n == 0:
        yield []
        return

    for p in partitions(n-1):
        yield [1] + p
        if p and (len(p) < 2 or p[1] > p[0]):
            yield [p[0] + 1] + p[1:]


# TODO this class is a proof-of-concept and is non-asymptotically 
# inefficient. It works around 500 times slower than a reference implementation
# in C++. Consider replacing this. 
class TFenceEnumerator:
    def __init__(self, schema_size):
        self.schema_size = schema_size
        self.partiter = partitions(schema_size)
        self.fenceset = set()

    def next_partition(self):
        try:
            self.part = next(self.partiter)
            self.permiter = permutations(list(range(0, len(self.part))))
        except StopIteration:
            self.part = None

    def next_permutation(self):
        try:
            self.perm = next(self.permiter)
        except StopIteration:
            self.perm = None

    def iter(self):
        while True:
            self.next_partition()
            if self.part is not None:
                levels = len(self.part)
                while True:
                    self.next_permutation()
                    if self.perm is not None:
                        fence = tuple([self.part[self.perm[i]]
                                       for i in range(0, levels)])
                        # TODO inefficiency probably stems from the fact that we 
                        # have to check here whether we already had this partition.
                        # Or from a very slow recursive implementation of permutations.
                        if fence in self.fenceset:
                            continue
                        self.fenceset.add(fence)
                        yield fence
                    else:
                        break
            else:
                return None

    def tmptest(self):
        while True:
            self.next_partition()
            if self.part is not None:
                while True:
                    self.next_permutation()
                    if self.perm is None:
                        break
                    print(self.perm)
            else:
                return None


def main():
    fg = TFenceEnumerator(10)
    fgy = fg.iter()
    for a in fgy:
        print(a)


if __name__ == "__main__":
    main()
