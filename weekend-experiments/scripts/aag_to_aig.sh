#!/bin/zsh

for f in ../hard-instances/*.aag; do aigtoaig -s $f ../hard-instances/${${f##*/}%.*}.aig; done
