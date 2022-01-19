import aiger

test_path = "./sorts/BubbleSort_7_4.aig"

aig_instance = aiger.load(test_path)

print(len(list(aig_instance.__iter_nodes__())))

nodes = 0
inverters = 0
ands = 0
for node in aig_instance.__iter_nodes__()[0]:
    nodes += 1
    s = str(type(node))
    if "Inverter" in s:
        inverters += 1
    elif "And" in s:
        ands += 1
        

print(nodes)
print("Ands", ands)
print("Invs", inverters)



