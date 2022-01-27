import json

lines = list()
with open("./friday_results/results.txt", "r") as f:
    result = json.load(f)
    lines.append("Test_name Size_before Size_after Time")
    for experiment in result:
        name = experiment['name'].split('/')[-1][:-4]
        graph_size = experiment['graph_size']
        after_pruning = graph_size - experiment['total_pruned']
        time = experiment['time_elapsed']
        lines.append(f"{name} {graph_size} {after_pruning} {time}\n")

with open("./friday_results/parsed_results.txt", "w") as f:
    f.writelines(lines)
