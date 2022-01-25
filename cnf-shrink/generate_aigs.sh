#!/bin/bash

# for i in "8 4" "9 4" "10 4" "8 5" "8 6" "8 7" "7 4" "6 4" "4 3"; do 
#     a=( $i )

#     sed -i "s/define k K/define k ${a[0]}/" sort_algs/BubbleSort.alg
#     sed -i "s/define n N/define n ${a[1]}/" sort_algs/BubbleSort.alg
#     wine ../Transalg.exe -f aig -i sort_algs/BubbleSort.alg -o "new_sorts/BubbleSort_${a[0]}_${a[1]}.aig"
#     sed -i "s/define k ${a[0]}/define k K/" sort_algs/BubbleSort.alg
#     sed -i "s/define n ${a[1]}/define n N/" sort_algs/BubbleSort.alg

#     sed -i "s/define k K/define k ${a[0]}/" sort_algs/PancakeSort.alg
#     sed -i "s/define n N/define n ${a[1]}/" sort_algs/PancakeSort.alg
#     wine ../Transalg.exe -f aig -i sort_algs/PancakeSort.alg -o "new_sorts/PancakeSort_${a[0]}_${a[1]}.aig"
#     sed -i "s/define k ${a[0]}/define k K/" sort_algs/PancakeSort.alg
#     sed -i "s/define n ${a[1]}/define n N/" sort_algs/PancakeSort.alg
# done

# python generate_labels_for_aig.sh
wine ../Transalg.exe -f aig -i complex_examples/tresh.alg -o "complex_examples/tresh.aag"
wine ../Transalg.exe -f aig -i complex_examples/multiplier.alg -o "complex_examples/multiplier.aag"
wine ../Transalg.exe -f aig -i complex_examples/A5_1.alg -o "complex_examples/A5_1.aag"
