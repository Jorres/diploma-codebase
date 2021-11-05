## Installation 

1. Create virtual environment (optional)
2. Run `pipx install -r requirements.txt`

## Usage

### Formatting the graph

In the following snippet, `n` is the number of vertices and `m` is the number
of edges, and lines `x_i y_i` correspond to edges starting at `x_i` and ending at `y_i`:

Vertices are labeled starting from 1.

```
n m
x_1 y_1
...
x_m y_m
```

### Run

In the following snippet, N is the maximum number of colors to try to paint the graph.

```
python main.py N /path/to/graph/file
```

### Encoding

1. In every iteration of the algorithm with `max_colors=colors`,
   there are `|V| * colors` variables, `a_i` corresponding to vertice `a` having color `i`.
2. Every variable must have at least one color assigned to it: 
   `(a_1 || .. || a_colors)` for `a` in `V`
3. Every edge must have differently colored vertices:
   `(not a_i || not b_i)` for `edge = <a, b>` and `i` in `1..colors`

### TODO 

- Add condition: every variable must have at most one color assigned to it
- Add tests (including big ones)
- Spend just a bit of time to try and runtime-profile the whole thing
