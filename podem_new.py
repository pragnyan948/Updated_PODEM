import pprint as pp
import time
import pdb
back_track_counter = 0
DEBUG=False
def read_netlist(file_name):
    net_dict = dict();
    inputs_list = []
    outputs_list = []
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
            if DEBUG:
                print(gate_name, gate_type, inputs)
                print("debug", gate_name, gate_type, inputs, gate_name)
            net_dict[gate_name] = Gate(gate_name, gate_type, inputs, gate_name)
        else:
            gate_name = each_line.split("(")[1].split(")")[0].strip()
            gate_type = each_line.split("(")[0].strip()
            inputs = []
            if DEBUG:
                print(gate_name, gate_type, inputs)
            net_dict[gate_name] = Gate(gate_name, gate_type, inputs, gate_name)
            if gate_type == "INPUT":
                inputs_list.append(gate_name)
            if gate_type == "OUTPUT":
                outputs_list.append(gate_name)
    return net_dict, inputs_list, outputs_list

class Gate:
    #NAND NOR AND OR NOT
    def __init__(self, name, type_, inputs, output):
        if DEBUG:
            print("debug2", name, type_, inputs, output)
        self.type = type_    # 'AND' or 'OR'
        self.inputs = inputs
        self.output = output
        self.value = 'X'
        self.name = name

    def non_controlling_value(self):
        # AND non-controlling = 1, OR non-controlling = 0
        if self.type == 'AND' or self.type == "NAND":
            return '1'
        else:
            return '0'
    def __str__(self):
        return "GateInst={}, GateType={}, Inputs={}, Output={}".format(self.name, self.type, self.inputs, self.output)
    def __repr__(self):
        return "GateInst={}, GateType={}, Inputs={}, Output={}".format(self.name, self.type, self.inputs, self.output)


class Circuit:
    def __init__(self):
        self.pi = []              # list of primary input names
        self.po = []              # list of primary output names
        self.gates = []           # list of Gate objects
        self.values = {}          # node_name -> logic value
        self.fault_gate_map = {}  # output node -> Gate driving it
        self.fault = None         # Fault object

    def set_fault(self, fault):
        self.fault = fault

    def add_pi(self, name):
        self.pi.append(name)
        self.values[name] = 'X'

    def set_po(self, name):
        self.po.append(name)

    def add_gate(self, type_, inputs, output):
        if DEBUG:
            print("d3", inputs)
        g = Gate(output, type_, inputs, output)
        self.gates.append(g)
        self.values.setdefault(output, 'X')
        for inp in inputs:
            self.values.setdefault(inp, 'X')
        self.fault_gate_map[output] = g

    def primary_inputs(self):
        return self.pi

    def primary_outputs(self):
        return self.po
    def reset(self):
        self.values = {i: 'X' for i in self.values.keys()}
        self.fault = None
        for g in self.gates:
            g.value = 'X'
        if DEBUG:
            print("Reset values", self.values)
            print("Reset gates", self.gates)
    def set(self, node, value):
        if DEBUG:
            print(f">>> SET {node} = {value}")
        self.values[node] = value
        self.evaluate()
        if DEBUG:
            print(f"    Values after eval: {self.values}")

    def unset(self, node):
        if DEBUG:
            print(f"<<< UNSET {node} -> X")
        self.values[node] = 'X'
        self.evaluate()
        if DEBUG:
            print(f"    Values after eval: {self.values}")

    def get(self, node):
        return self.values[node]

    def evaluate(self):
        changed = True
        while changed:
            changed = False
            for g in self.gates:
                in_vals = [self.values[i] for i in g.inputs]
                # compute the good circuit value
                if DEBUG:
                    print("eval1 debug", g.name)
                good_val = self._eval_gate(g.type, in_vals)
                if DEBUG:
                    print("eval3 debug", good_val)

                # inject fault at site
                if self.fault and g.output == self.fault.node:
                    stuck = self.fault.stuck_value
                    if good_val is None or good_val=='X' or good_val == stuck:
                        new_val = good_val
                        #new_val = stuck
                        if DEBUG:
                            print(f"    [good value] {g.output} = {good_val} [new_val] {g.output} = { new_val} (stuck {stuck})")
                    else:
                        new_val = 'D' if stuck == '0' else 'Db'
                else:
                    new_val = good_val

                if new_val is not None and self.values[g.output] != new_val:
                    self.values[g.output] = new_val
                    changed = True

    def _eval_gate(self, type_, in_vals):
        # blocking X before D/Db propagation
        if DEBUG:
            print("debug eval", type_, in_vals)

        if type_ == 'NOT':
            val = in_vals[0]
            if val == '0':
                return '1'
            if val == '1':
                return '0'
            if val == 'X':
                return 'X'
            if val == 'D':
                return 'Db'
            if val == 'Db':
                return 'D'
            return 'X'

        if type_ == 'AND':
            if '0' in in_vals:
                return '0'
            if 'X' in in_vals:
                return 'X'
            if 'Db' in in_vals and 'D' in in_vals:
                return '0'  # D and Db cancel each other
            if 'Db' in in_vals:
                return 'Db'
            if 'D' in in_vals:
                return 'D'
            return '1'

        if type_ == 'NAND':
            and_val = self._eval_gate('AND', in_vals)
            if and_val == 'X':
                return 'X'
            if and_val == '0':
                return '1'
            if and_val == '1':
                return '0'
            if and_val == 'D':
                return 'Db'
            if and_val == 'Db':
                return 'D'
            return 'X'

        if type_ == 'OR':
            if '1' in in_vals:
                return '1'
            if 'X' in in_vals:
                return 'X'
            if 'Db' in in_vals and 'D' in in_vals:
                return '1'  # OR(D, Db) = 1
            if 'D' in in_vals:
                return 'D'
            if 'Db' in in_vals:
                return 'Db'
            return '0'

        if type_ == 'NOR':
            or_val = self._eval_gate('OR', in_vals)
            if or_val == 'X':
                return 'X'
            if or_val == '0':
                return '1'
            if or_val == '1':
                return '0'
            if or_val == 'D':
                return 'Db'
            if or_val == 'Db':
                return 'D'
            return 'X'

        raise ValueError(f"Unknown gate type: {type_}")



class Fault:
    def __init__(self, node, stuck_value):
        self.node = node
        self.stuck_value = stuck_value


def opposite(val):
    return '1' if val == '0' else '0' if val == '1' else val


def fault_activated(fault, circ):
    v = circ.get(fault.node)
    return (fault.stuck_value == '0' and v == 'D') or \
           (fault.stuck_value == '1' and v == 'Db')


def fault_propagated(fault, circ):
    return any(circ.get(po) in ('D', 'Db') for po in circ.primary_outputs())


def check_test(fault, circ):
    act = fault_activated(fault, circ)
    prop = fault_propagated(fault, circ)
    if DEBUG:
        print(f"    [check_test] activated={act}, propagated={prop}")
    return act and prop


def backtrace(node, value, circ, indent=''):
    """
    Trace from an internal node back to a PI that can produce `value` at `node`.
    """
    if DEBUG:
        print(f"{indent}Backtrace: need {node}={value}")
    if node in circ.primary_inputs():
        return node, value
    gate = circ.fault_gate_map[node]
    # choose an input still X, else pick first input
    for inp in gate.inputs:
        if circ.get(inp) == 'X':
            return backtrace(inp, value, circ, indent+'  ')
    #return backtrace(gate.inputs[0], value, circ, indent+'  ')
    return (None, None)


def getObjective(fault, circ, stack):
    indent = '  ' * len(stack)
    if DEBUG:
        print(f"{indent}[getObjective] stack={stack}")

    # 1) Activation phase via backtrace
    if not fault_activated(fault, circ):
        desired = opposite(fault.stuck_value)
        pi_node, pi_val = backtrace(fault.node, desired, circ, indent+'  ')
        if pi_node is None:
            return None
        if DEBUG:
            print(f"{indent}  -> activate: set {pi_node} = {pi_val}")
        return pi_node, pi_val

    # 2) Propagation phase via backtrace (Algorithm 14.11)
    if not fault_propagated(fault, circ):
        for d in circ.gates:
            if any(circ.get(i) in ('D','Db') for i in d.inputs) \
               and circ.get(d.output) not in ('D','Db'):
                for net in d.inputs:
                    if circ.get(net) == 'X':
                        nc = d.non_controlling_value()
                        # backtrace from net to a PI
                        pi_node, pi_val = backtrace(net, nc, circ, indent+'  ')
                        if DEBUG:
                            print(f"{indent}  -> propagate: set {pi_node} = {pi_val}"
                              f" (for net {net} non-controlling={nc} of {d.type})")
                        if pi_node is None:
                            return None
                        return pi_node, pi_val

    # 3) dead end
    if DEBUG:
        print(f"{indent}  -> no objective (dead end)")
    return None

# 2) rec podem function (Algorithm 14.10)
def _podem_rec(fault, circ, stack):
    global back_track_counter
    indent = '  ' * len(stack)
    if DEBUG:
        print(f"{indent}Depth {len(stack)}: {circ.values}")
    if check_test(fault, circ):
        if DEBUG:
            print(f"{indent}*** Test found!")
        return True

    obj = getObjective(fault, circ, stack)
    if obj is None:
        if DEBUG:
            print(f"{indent}Dead end")
        return False
    #pdb.set_trace()

    node, val = obj
    stack.append((node, val))

    # Try the assignment
    circ.set(node, val)
    #pdb.set_trace()
    
    if _podem_rec(fault, circ, stack):
        return True


    back_track_counter = back_track_counter + 1
    # Backtrack and try opposite
    circ.unset(node)
    stack.pop()
    alt = opposite(val)
    if DEBUG:
        print(f"{indent}Try opposite: {node} = {alt}")
    stack.append((node, alt))
    circ.set(node, alt)
    if _podem_rec(fault, circ, stack):
        return True

    # Both failed
    circ.unset(node)
    stack.pop()
    back_track_counter = back_track_counter + 1
    if DEBUG:
        print(f"{indent}Backtrack beyond {node}")
    return False


def podem(fault, circ):
    if DEBUG:
        print("---- Starting PODEM ----")
        print("Fault:", fault.node, fault.stuck_value)
    global back_track_counter
    back_track_counter = 0
    circ.reset()
    for pi in circ.primary_inputs():
        circ.set(pi, 'X')
    circ.set_fault(fault)
    if DEBUG:
        print("Values", circ.values)
    if _podem_rec(fault, circ, []):
        tv = {pi: circ.get(pi) for pi in circ.primary_inputs()}
        if DEBUG:
            print("No of back tracks:", back_track_counter)
        print("Fault:", fault.node, fault.stuck_value)
        print("---- Test vector found:", tv)
        
        return (tv, back_track_counter)
    if DEBUG:
        print("---- No test found ----")
        print("No of back tracks:", back_track_counter)
    return (None, back_track_counter)


# --- Test harness: AND → OR → AND chain ---


#for name in ['A','B','C','D', 'E', 'F', 'G', 'H']:
#    c.add_pi(name)
#c.add_gate('AND', ['A','B'], 'N1')
#c.add_gate('OR', ['N1','N3'], 'OUT1')
#c.add_gate('AND', ['C','N2'], 'N3')
#c.add_gate('OR', ['E','D'], 'N2')
#c.add_gate('AND', ['F','N3'], 'N4')
#c.add_gate('OR', ['G','N4'], 'OUT2')
#c.set_po('OUT1')
#c.set_po('OUT2')


# Inject SA-0 fault at N1
#fault = Fault('N3','0')

#test_vector = podem(fault, c)

def basic_podem(circuit_file, fault_list):
    #netlist = read_netlist("/ece/home/kola0161/vda2/simple_circuit.bench")

    # U23352.U2360/1
    netlist, netlist_inputs, netlist_outputs = read_netlist(circuit_file)
    #netlist, netlist_inputs, netlist_outputs = read_netlist("/ece/home/kola0161/vda2/ppt_circuit.txt")

    c = Circuit()
    for gate in netlist.keys():
        gate_type = netlist[gate].type
        if DEBUG:
            print(gate, gate_type)
        if gate_type != "INPUT" and gate_type != "OUTPUT":
            if DEBUG:
                print("debug", netlist[gate].inputs)
                print("debug", netlist[gate].output)
            c.add_gate(gate_type, netlist[gate].inputs, netlist[gate].output)
    for inp in netlist_inputs:
        c.add_pi(inp)
    for out in netlist_outputs:
        c.set_po(out)
    #pp.pprint(netlist)
    test_patterns,max_time_untestable, conflicts = {}, {},0
    #fault = Fault('U2','0')
    detected_faults = 0
    for each_fault in fault_list:
        out_node = each_fault.split(".")[0]
        in_node = each_fault.split(".")[1].split("/")[0]
        fault_val = each_fault.split("/")[1]
    
        fault = Fault(in_node, fault_val)
        start_time=time.time()
        (test_vector, backtracks) = podem(fault, c)
        time_elapsed=time.time()-start_time
        #pdb.set_trace()
        if backtracks > 0:
            conflicts+= 1
        if test_vector != None:
            detected_faults = detected_faults + 1
            test_patterns[each_fault]=test_vector
            print("ran podem and fault detected ", each_fault, " backtracks=", backtracks)
        else:
            print("fault ", each_fault," undetected , backtracks=", backtracks," max_time_untestable:",time_elapsed)
            max_time_untestable[each_fault]=time_elapsed
    return detected_faults, backtracks,conflicts, max_time_untestable, test_patterns