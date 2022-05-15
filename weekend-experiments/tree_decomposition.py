from tqdm import tqdm
import sys
import os
import math
import time

import utils as U
import formula_builder as FB
import hyperparameters as H

import pysat
import pysat.formula
from pysat.solvers import Maplesat as PysatSolver


def prepare_first_layer_of_baskets(domains):
    for domain, _, _ in domains:
        assert len(domain) > 1
    baskets = [
        Basket.from_one_domain(bucket, domain) for domain, bucket, tag in domains
    ]
    return baskets


def bitvector_to_assumptions(bitvector, gate_names, pool):
    assumptions = list()
    assert len(bitvector) == len(gate_names)
    for single_int, bucket in zip(bitvector, gate_names):
        for gate_id, gate_name in enumerate(bucket):
            modifier = U.get_bit_from_domain(single_int, gate_id)
            assumptions.append(modifier * pool.v_to_id(gate_name))
    return assumptions


def merge_baskets(baskets, solver, pool):
    skipped = 0

    if len(baskets) == 0:
        return Basket([[]], []), 0

    final_basket = baskets[0]

    for cur_basket in tqdm(baskets[1:], desc="Merging baskets", leave=False):
        final_basket, cur_skipped = final_basket.merge(cur_basket, solver, pool)
        skipped += cur_skipped
        print(f"Skipped {cur_skipped}")

    return final_basket, skipped


class Basket:
    def __init__(self, bitvectors, gate_names):
        self.bitvectors = bitvectors
        self.gate_names_for_bitvectors = gate_names
        assert len(gate_names) % H.BUCKET_SIZE

    @classmethod
    def from_two_baskets(cls, bitvector, gate_names):
        return cls(bitvector, gate_names)

    @classmethod
    def from_one_domain(cls, bucket, domain):
        bitvectors = list()
        for bitvector in domain:
            bitvectors.append([bitvector])
        gate_names_for_bitvectors = [bucket]
        return cls(bitvectors, gate_names_for_bitvectors)

    def size(self):
        return len(self.gate_names_for_bitvectors)

    def debug_print(self):
        print(f"{self.bitvectors=} {self.gate_names_for_bitvectors=}")

    def merge(self, other, solver, pool):
        skipped = 0
        shared_gate_names = (
            self.gate_names_for_bitvectors + other.gate_names_for_bitvectors
        )
        resulting_bucket_bitvectors = list()
        for left_bitvectors in self.bitvectors:
            for right_bitvectors in other.bitvectors:
                shared_bitvector = left_bitvectors + right_bitvectors
                assumptions = bitvector_to_assumptions(
                    shared_bitvector, shared_gate_names, pool
                )
                res = U.solve_with_conflict_limit(solver, assumptions, 600)
                # SAT means these bitvectors are still compatible, put into next bucket.
                # or, alternatively, it is a very long unsat, therefore we still should
                # solve it sometime later.
                if res or res is None:
                    resulting_bucket_bitvectors.append(shared_bitvector)
                else:  # ok, UNSAT reached, skip it
                    skipped += 1
                    continue

        return (
            Basket.from_two_baskets(resulting_bucket_bitvectors, shared_gate_names),
            skipped,
        )


def generate_inccnf(
    g1, g2, basket_left, basket_right, metainfo, file_name, d_left, d_right
):
    t1 = time.time()
    tmp_file = f"{file_name}.tmp"
    cubes = list()
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)
    cnf = FB.generate_miter_scheme(shared_cnf, pool, g1, g2)
    for bitvector_left in tqdm(basket_left.bitvectors, desc="Left bucket"):
        for bitvector_right in tqdm(
            basket_right.bitvectors, desc="Right bucket", leave=False
        ):
            assumptions_left = bitvector_to_assumptions(
                bitvector_left, basket_left.gate_names_for_bitvectors, pool
            )
            assumptions_right = bitvector_to_assumptions(
                bitvector_right, basket_right.gate_names_for_bitvectors, pool
            )
            cubes.append(
                "a "
                + " ".join([str(a) for a in assumptions_left])
                + " "
                + " ".join([str(a) for a in assumptions_right])
                + " 0\n"
            )

    pysat.formula.CNF(from_clauses=cnf).to_file(tmp_file)

    lines = list()
    with open(tmp_file, "r") as tmp:
        for line in tmp.readlines():
            if line.startswith("p cnf"):
                lines.append("p inccnf\n")
            else:
                lines.append(line)

    with open(file_name, "w") as f:
        f.writelines(lines)
        f.writelines(cubes)
    t2 = time.time()
    metainfo["dumping_icnf"] = t2 - t1
    U.dump_dict(
        metainfo, file_name.replace("icnfs", "icnf_generation_metadata") + ".meta"
    )
    os.system(f"rm {tmp_file}")

    # unbalancedness_order_filename = f"${file_name}.order"

    # for (saturation, bucket, domain, tag) in d_left:
    #     for elem in bucket:
    #         print(f"${elem=} ${pool.v_to_id(elem)}")
    # for (saturation, bucket, domain, tag) in d_right:
    #     for elem in bucket:
    #         print(f"${elem=} ${pool.v_to_id(elem)}")


def iterate_over_two_megabackets(g1, g2, basket_left, basket_right):
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)
    cnf = FB.generate_miter_scheme(shared_cnf, pool, g1, g2)
    with PysatSolver(bootstrap_with=cnf) as solver:
        for bitvector_left in tqdm(basket_left.bitvectors, desc="Left bucket"):
            for bitvector_right in tqdm(
                basket_right.bitvectors, desc="Right bucket", leave=False
            ):
                assumptions_left = bitvector_to_assumptions(
                    bitvector_left, basket_left.gate_names_for_bitvectors, pool
                )
                assumptions_right = bitvector_to_assumptions(
                    bitvector_right, basket_right.gate_names_for_bitvectors, pool
                )

                res = solver.solve(assumptions=assumptions_left + assumptions_right)
                if res:
                    return False

    return True


def filter_complex_cubes(g1, g2, basket_left, basket_right, complex_cubes_filename):
    print(complex_cubes_filename)
    shared_cnf, pool = U.prepare_shared_cnf_from_two_graphs(g1, g2)
    cnf = FB.generate_miter_scheme(shared_cnf, pool, g1, g2)

    with open(complex_cubes_filename, "w") as f:
        with PysatSolver(bootstrap_with=cnf) as solver:
            for bitvector_left in tqdm(basket_left.bitvectors, desc="Left bucket"):
                for bitvector_right in tqdm(
                    basket_right.bitvectors, desc="Right bucket", leave=False
                ):
                    assumptions_left = bitvector_to_assumptions(
                        bitvector_left, basket_left.gate_names_for_bitvectors, pool
                    )
                    assumptions_right = bitvector_to_assumptions(
                        bitvector_right, basket_right.gate_names_for_bitvectors, pool
                    )

                    for elem in assumptions_left:
                        f.write(str(elem) + " ")
                    for elem in assumptions_right:
                        f.write(str(elem) + " ")
                    f.write("\n")

                    # res = U.solve_with_conflict_limit(
                    #     solver, assumptions_left + assumptions_right, 1000
                    # )

                    # if res is None:
                    #     for elem in assumptions_left:
                    #         f.write(str(elem) + " ")
                    #     for elem in assumptions_right:
                    #         f.write(str(elem) + " ")
                    #     f.write("\n")
                    # assert res is not True

