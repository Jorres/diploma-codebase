#!/bin/bash

for f in ./data/miters-aig/*.aig
do
    CNF="./data/miters-cnf/$(basename $f .aig)-aig.cnf"
    echo "fraig->cnf: $f -> $CNF"
    # aigtocnf -m "$f" "$CNF"
    aigtocnf "$f" "$CNF"
done
