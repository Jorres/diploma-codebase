from threading import Timer
import formula_builder as FB
import json

import hyperparameters as H


def print_to_file(filename, data):
    with open(filename, "a+") as f:
        f.write(data + "\n")


def interrupt(s):
    s.interrupt()


def solve_with_timeout(solver, assumptions, timeout):
    timer = Timer(timeout, interrupt, [solver])
    timer.start()

    result = solver.solve_limited(assumptions=assumptions, expect_interrupt=True)

    if result is None:
        solver.clear_interrupt()
    else:
        timer.cancel()

    return result


def solve_with_conflict_limit(solver, assumptions, limit):
    solver.conf_budget(limit)
    result = solver.solve_limited(assumptions=assumptions)
    return result


def get_bit_from_domain(bitvector, gate_id):
    if (bitvector & (1 << gate_id)) > 0:
        return 1
    else:
        return -1


def prepare_shared_cnf_from_two_graphs(g1, g2):
    pool = FB.TPoolHolder()
    # pool = FB.PicklablePool()
    shared_cnf = FB.make_united_miter_from_two_graphs(g1, g2, pool)
    return shared_cnf.clauses, pool


def dump_dict(data, file):
    with open(file, "a+") as f:
        f.write(json.dumps(data, indent=4))


def replace_in_list(lst, what, with_what):
    replaced = False
    for i in range(len(lst)):
        if lst[i] == what:
            lst[i] = with_what
            replaced = True
            break
    assert replaced, "Replacement expected, but didn't happen"


def extract_domains_with_saturation_one_into_cnf(cnf, pool, domains, metainfo):
    one_saturated_domains = 0
    one_defined = 0
    for saturation, bucket, domain, tag in domains:
        if len(domain) == 1:
            one_saturated_domains += 1
            for gate_id, gate_name in enumerate(bucket):
                bitvector = domain[0]
                modifier = get_bit_from_domain(bitvector, gate_id)
                cnf.append([modifier * pool.v_to_id(gate_name)])
                one_defined += 1
        else:
            break
    metainfo["one_defined"] = one_defined
    metainfo["one_saturated_domains"] = one_saturated_domains
    return domains[one_saturated_domains:]


def take_domains_until_threshold(domains, metainfo, max_product_size=H.MAX_CARTESIAN_PRODUCT_SIZE):
    cartesian_size = 1
    best_domains = list()
    total_vars_in_decomp = 0
    for saturation, bucket, domain, tag in domains:
        if cartesian_size * len(domain) > max_product_size:
            break
        best_domains.append((domain, bucket))
        total_vars_in_decomp += len(bucket)
        cartesian_size *= len(domain)

    metainfo["actual_cartesian_size"] = cartesian_size
    metainfo["total_vars_in_decomp"] = total_vars_in_decomp
    return best_domains, cartesian_size
