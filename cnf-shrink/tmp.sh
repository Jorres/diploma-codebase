#!/bin/zsh

python main.py
cryptominisat5 --printsol=0 old_cnf_P_10_4.cnf
cryptominisat5 --printsol=0 topsorted_cnf_P_10_4.cnf
