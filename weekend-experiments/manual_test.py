import os
from graph import Graph

def main():
    g = Graph("./hard-instances/BubbleSort_7_4.aag")
    g.remove_identical()
    g.to_file("./hard-instances/BubbleSort_7_4_dumped.aag")
    os.system("./aag_to_aig.sh")

main()
