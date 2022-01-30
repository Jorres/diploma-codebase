#!/bin/zsh

# for test_shortname in "4_3" "6_4"; do
for test_shortname in "7_4_naive" "7_4"; do
    echo "${test_shortname}"

    cryptominisat5 --printsol=0 ./hard-instances/cnf/"${test_shortname}".cnf \
        > ./hard-instances/naive-external/crypto_"${test_shortname}".txt

    # abc -c "miter ./hard-instances/BubbleSort_${test_shortname}.aig ./hard-instances/PancakeSort_${test_shortname}.aig" -c "sat -v" > ./hard-instances/naive-external/abc_"${test_shortname}".txt
done
