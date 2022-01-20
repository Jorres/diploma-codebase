# Domain-based equivalence checking

## Repo structure 

### main.py

Contains entrypoint into the task. Functions of interest are:
    - `naive_equivalence_check(schema_file_1, schema_file_2)` -
      determines equivalency by running one large miter-schema task
    - `domain_equivalence_check(schema_file_1, schema_file_2)` - 
      tries to determine equivalence using domain optimization

### graph.py

Represents a boolean schema. Can be 
    - initialized from an aig (which you get by running `aiger.load(aiger_file_path)`),
    - stores mapping between node names and outputs (e.g. `i380` -> `o23`)
    - can be fed an input to be calculated through the schema, outputs a dict with a value of every 
      gate in the execution

### formula_builder.py

A simple Tseytin encoder of an AIG-based graph into a CNF

### generate_aigs.sh and generate_labels_for_aig.py

A script that generates AIG encodings for sorting algorithms 
using Transalg.

## Tests

1. We have three sorting algorithms. If a test has the word `Faulty` in it, 
   then it has been slightly modified (usually some output has been inverted)
   to be surely non-equivalent to the sorting algorithm it is based on.
2. InsertSort is believed to be broken. Reason: 
    - when loaded through my custom graph and fed with an input, outputs have more 1-bits than inputs, 
      which absolutely makes no sense for a sorting algorithm
    - it is not equivalent to any of other sorting algorithms neither naively nor with a domain optimization
      (obviously, due to previous argument, it is simply not a sorting algorithm)
    - runtimes of SAT oracle checking equivalence (with itself) are also much higher (it is not a strong 
      argument by any means but kind of increases suspicion)
   
