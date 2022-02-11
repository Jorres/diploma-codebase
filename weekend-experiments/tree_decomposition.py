from tqdm import tqdm
import sys

import utils as U


def prepare_first_layer_of_baskets(domains):
    for domain, _ in domains:
        assert len(domain) > 1
    baskets = [Basket.from_one_domain(bucket, domain)
               for domain, bucket in domains]
    return baskets


def bitvector_to_assumptions(bitvector, gate_names, pool):
    assumptions = list()
    assert len(bitvector) == len(gate_names)
    for single_int, bucket in zip(bitvector, gate_names):
        for gate_id, gate_name in enumerate(bucket):
            modifier = U.get_bit_from_domain(single_int, gate_id)
            assumptions.append(modifier * pool.v_to_id(gate_name))
    return assumptions


class Basket:
    def __init__(self, bitvectors, gate_names):
        self.bitvectors = bitvectors
        self.gate_names_for_bitvectors = gate_names

    @classmethod
    def from_two_baskets(cls, bitvector, gate_names):
        return cls(bitvector, gate_names)

    @classmethod
    def from_one_domain(cls, bucket, domain):
        # print(f"{bucket=} {domain=}")
        bitvectors = list()
        for bitvector in domain:
            # print(f"{bitvector=}")
            bitvectors.append([bitvector])
        # print(f"{bitvectors=}")
        gate_names_for_bitvectors = [bucket]
        return cls(bitvectors, gate_names_for_bitvectors)

    def debug_print(self):
        print(f"{self.bitvectors=} {self.gate_names_for_bitvectors=}")

    def merge(self, other, solver, pool):
        skipped = 0
        shared_gate_names = self.gate_names_for_bitvectors + other.gate_names_for_bitvectors
        resulting_bucket_bitvectors = list()
        for left_bitvectors in self.bitvectors:
            for right_bitvectors in other.bitvectors:
                shared_bitvector = left_bitvectors + right_bitvectors
                assumptions = bitvector_to_assumptions(
                    shared_bitvector, shared_gate_names, pool)
                res = U.solve_with_conflict_limit(solver, assumptions, 600)
                # SAT means these bitvectors are still compatible, put into next bucket.
                # or, alternatively, it is a very long unsat, therefore we still should
                # solve it sometime later.
                if res or res is None:
                    resulting_bucket_bitvectors.append(shared_bitvector)
                else:  # ok, UNSAT reached, skip it
                    # print(f"skipped {shared_bitvector}")
                    skipped += 1
                    assert not res
                    continue

        # print(f"{resulting_bucket_bitvectors=} {shared_gate_names=}")

        return Basket.from_two_baskets(resulting_bucket_bitvectors, shared_gate_names), skipped
