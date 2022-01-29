#!/bin/bash

# for i in "8 4" "9 4" "10 4" "8 5" "8 6" "8 7" "7 4" "6 4" "4 3" "10 5"; do 
FOLDER="aiger-abc-dump"
for i in "5 4"; do
    a=( $i )

    sed -i "s/define k K/define k ${a[0]}/" "${FOLDER}"/BubbleSort.alg
    sed -i "s/define n N/define n ${a[1]}/" "${FOLDER}"/BubbleSort.alg
    wine ../Transalg.exe -f aig -i "${FOLDER}"/BubbleSort.alg -o "./${FOLDER}/BubbleSort_${a[0]}_${a[1]}.aag"
    dos2unix "./${FOLDER}/BubbleSort_${a[0]}_${a[1]}.aag" 
    sed -i "s/define k ${a[0]}/define k K/" "${FOLDER}"/BubbleSort.alg
    sed -i "s/define n ${a[1]}/define n N/" "${FOLDER}"/BubbleSort.alg

    sed -i "s/define k K/define k ${a[0]}/" "${FOLDER}"/PancakeSort.alg
    sed -i "s/define n N/define n ${a[1]}/" "${FOLDER}"/PancakeSort.alg
    wine ../Transalg.exe -f aig -i "${FOLDER}"/PancakeSort.alg -o "./${FOLDER}/PancakeSort_${a[0]}_${a[1]}.aag"
    dos2unix "./${FOLDER}/PancakeSort_${a[0]}_${a[1]}.aag" 
    sed -i "s/define k ${a[0]}/define k K/" "${FOLDER}"/PancakeSort.alg
    sed -i "s/define n ${a[1]}/define n N/" "${FOLDER}"/PancakeSort.alg
done

python generate_labels_for_aig.py "${FOLDER}"
python main.py

./aag_to_aig.sh "${FOLDER}" 
