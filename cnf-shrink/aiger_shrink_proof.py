import math
from collections import defaultdict


with open('./aiger_shrink_proof.txt') as f:
    content = f.readlines()

content = [list(map(int, x.strip().split(" "))) for x in content]


outputs = [
    2325, 2331, 2337, 2343, 2349, 2355,
    2361, 2367, 2239, 2245, 2251, 2257,
    2019, 2025, 2031, 2037, 1689, 1695,
    1701, 1707, 1249, 1255, 1261, 1267,
    699, 705, 711, 717
]

visited_ands = set()
visited_invs = set()

q = outputs

graph = defaultdict(list)
for s in content:
    if len(s) == 3:
        graph[s[0]].append(s[1])
        graph[s[0]].append(s[2])

while q:
    v = q.pop()
    if v in visited_ands or v in visited_invs:
        continue
    if v % 2 == 1:
        visited_invs.add(v)
        v -= 1
    visited_ands.add(v)
    if v in graph:
        q.append(graph[v][0])
        q.append(graph[v][1])

print(len(visited_ands) + len(visited_invs))
print(len(visited_ands))
print(len(visited_invs))

