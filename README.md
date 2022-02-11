# diploma-codebase

## chain-synthesis

Experiment with schema synthesis using DAG topologies.

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

