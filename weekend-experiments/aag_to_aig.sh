#!/bin/zsh
for f in ./aiger-abc-dump/*.aag; do aigtoaig -s $f ./aiger-abc-dump/${${f##*/}%.*}.aig; done

touch ./aiger-abc-dump/dumped_BubbleSort_5_4.aag
touch ./aiger-abc-dump/dumped_PancakeSort_5_4.aag
