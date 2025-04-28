import pprint as pp

def read_netlist(file_name):
    net_dict = dict();
    with open(file_name, 'r') as rp:
        all_lines = rp.readlines()
    for each_line in all_lines:
        each_line = each_line.strip()
        if "#" in each_line or each_line == "":
            continue
        elif "=" in each_line:
            gate_name = each_line.split("=")[0].strip()
            gate_type = each_line.split("=")[1].split("(")[0].strip()
            inputs = each_line.split("(")[1].split(")")[0].split(", ")
            #print(gate_name, gate_type, inputs)
            net_dict[gate_name] = Gate(gate_type, gate_name, inputs)
        else:
            gate_name = each_line.split("(")[1].split(")")[0].strip()
            gate_type = each_line.split("(")[0].strip()
            inputs = []
            #print(gate_name, gate_type, inputs)
            net_dict[gate_name] = Gate(gate_type, gate_name, inputs)
    return net_dict

# Basic Gate class
class Gate:
    def __init__(self, typ, name, inputs):
        self.typ = typ
        self.name = name
        self.inputs = inputs
        self.value = 'X'
    def __str__(self):
        return "GateInst={}, GateType={}, Inputs={}".format(self.name, self.typ, self.inputs)
    def __repr__(self):
        return "GateInst={}, GateType={}, Inputs={}".format(self.name, self.typ, self.inputs)

#netlist = read_netlist("/ece/home/kola0161/vda2/simple_circuit.bench")
#netlist = read_netlist("/ece/home/nalla052/EE5302/Project/Benchmark/I99T/i99t/b03/b03_opt_C.bench")
#pp.pprint(netlist)
