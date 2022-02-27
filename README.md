# diploma-codebase

## weekend-experiments

(yes, I know, not the best name for the folder. TLDR will
change the name later, python cryptominisat bindings depend on it)

#### `experiments` subfolder

Contains small scripts to usually check a small isolated hypothesis.

#### `hard instances` subfolder

Contains `alg` and `aag` sources of sorting algorithms as well as
some crypto `aag`s.

#### `tests` subfolder

Tests are meant to be smoke tests. They are not comprehensive by a
any means, but if THEY fail, something is definitely way off.

Just launch `pytest`. Tests try to cover graph parsing, equivalence checking
and utilities.

#### Entrypoint to checking equivalence: `main.py`

`main` function contains a wrapper that takes source files (aags, fraags) from 
`./weekend-experiments/hard-instances/`. Three main ways to check for equivalence:
1. Naive way -  `naive_equivalence_check`
2. Using tree decomposition -  `domain_equivalence_check(..., "tree-based")`
3. Full cartesian product traversal -  `domain_equivalence_check(..., "all-domains-at-once")`

All of the approaches generate JSON-reports in `./weekend-experiments/hard-instances/metainfo`, that
contain info about runtimes, the most difficult instances, and constructed domains.


## chain-synthesis

Experiment with schema synthesis using DAG topologies. Discontinued. 
