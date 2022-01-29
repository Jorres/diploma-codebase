import json

lines = list()
with open("./results/10_4.txt", "r") as f:
    result = json.load(f)
    lines.append("Left Right Cartesian_size Gates_substituted Skipped Solved Inferred Time\n")
    for experiment in result:
        left = experiment['left_schema'].split('/')[-1][:-4]
        right = experiment['right_schema'].split('/')[-1][:-4]
        cartesian_size = experiment['cartesian_size']
        one_defined = experiment['one_defined']
        skipped = experiment['skipped']
        solved = experiment['solved']
        time = experiment['time']
        total_vars_substituted = experiment['one_defined'] + \
            experiment['total_vars_in_decomp']

        lines.append(
            f"{left} {right} {cartesian_size} {total_vars_substituted} {skipped} {solved} {one_defined} {time}\n")

with open("./friday_results/equivalence_results.txt", "w") as f:
    f.writelines(lines)
