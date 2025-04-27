# Node values: '0','1','X','D','Db'
class Gate:
    def __init__(self, type_, inputs, output):
        self.type = type_    # 'AND' or 'OR'
        self.inputs = inputs
        self.output = output

    def non_controlling_value(self):
        # AND non-controlling = 1, OR non-controlling = 0
        return '1' if self.type == 'AND' else '0'


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
        g = Gate(type_, inputs, output)
        self.gates.append(g)
        self.values.setdefault(output, 'X')
        for inp in inputs:
            self.values.setdefault(inp, 'X')
        self.fault_gate_map[output] = g

    def primary_inputs(self):
        return self.pi

    def primary_outputs(self):
        return self.po

    def set(self, node, value):
        print(f">>> SET {node} = {value}")
        self.values[node] = value
        self.evaluate()
        print(f"    Values after eval: {self.values}")

    def unset(self, node):
        print(f"<<< UNSET {node} -> X")
        self.values[node] = 'X'
        self.evaluate()
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
                good_val = self._eval_gate(g.type, in_vals)

                # inject fault at site
                if self.fault and g.output == self.fault.node:
                    stuck = self.fault.stuck_value
                    if good_val is None or good_val == stuck:
                        new_val = stuck
                    else:
                        new_val = 'D' if stuck == '0' else 'Db'
                else:
                    new_val = good_val

                if new_val is not None and self.values[g.output] != new_val:
                    self.values[g.output] = new_val
                    changed = True

    def _eval_gate(self, type_, in_vals):
        # blocking X before D/Db propagation
        if type_ == 'AND':
            if '0' in in_vals:
                return '0'
            if 'X' in in_vals:
                return None
            if 'D' in in_vals:
                return 'D'
            if 'Db' in in_vals:
                return 'Db'
            return '1'
        else:  # OR
            if '1' in in_vals:
                return '1'
            if 'X' in in_vals:
                return None
            if 'D' in in_vals:
                return 'D'
            if 'Db' in in_vals:
                return 'Db'
            return '0'


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
    print(f"    [check_test] activated={act}, propagated={prop}")
    return act and prop


def backtrace(node, value, circ, indent=''):
    """
    Trace from an internal node back to a PI that can produce `value` at `node`.
    """
    print(f"{indent}Backtrace: need {node}={value}")
    if node in circ.primary_inputs():
        return node, value
    gate = circ.fault_gate_map[node]
    # choose an input still X, else pick first input
    for inp in gate.inputs:
        if circ.get(inp) == 'X':
            return backtrace(inp, value, circ, indent+'  ')
    return backtrace(gate.inputs[0], value, circ, indent+'  ')


def getObjective(fault, circ, stack):
    indent = '  ' * len(stack)
    print(f"{indent}[getObjective] stack={stack}")

    # 1) Activation phase via backtrace
    if not fault_activated(fault, circ):
        desired = opposite(fault.stuck_value)
        pi_node, pi_val = backtrace(fault.node, desired, circ, indent+'  ')
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
                        print(f"{indent}  -> propagate: set {pi_node} = {pi_val}"
                              f" (for net {net} non-controlling={nc} of {d.type})")
                        return pi_node, pi_val

    # 3) dead end
    print(f"{indent}  -> no objective (dead end)")
    return None

# 2) rec podem function (Algorithm 14.10)
def _podem_rec(fault, circ, stack):
    indent = '  ' * len(stack)
    print(f"{indent}Depth {len(stack)}: {circ.values}")
    if check_test(fault, circ):
        print(f"{indent}*** Test found!")
        return True

    obj = getObjective(fault, circ, stack)
    if obj is None:
        print(f"{indent}Dead end")
        return False

    node, val = obj
    stack.append((node, val))

    # Try the assignment
    circ.set(node, val)
    if _podem_rec(fault, circ, stack):
        return True

    # Backtrack and try opposite
    circ.unset(node)
    stack.pop()
    alt = opposite(val)
    print(f"{indent}Try opposite: {node} = {alt}")
    stack.append((node, alt))
    circ.set(node, alt)
    if _podem_rec(fault, circ, stack):
        return True

    # Both failed
    circ.unset(node)
    stack.pop()
    print(f"{indent}Backtrack beyond {node}")
    return False


def podem(fault, circ):
    print("---- Starting PODEM ----")
    for pi in circ.primary_inputs():
        circ.set(pi, 'X')
    circ.set_fault(fault)
    if _podem_rec(fault, circ, []):
        tv = {pi: circ.get(pi) for pi in circ.primary_inputs()}
        print("---- Test vector found:", tv)
        return tv
    print("---- No test found ----")
    return None


# --- Test harness: AND → OR → AND chain ---


c = Circuit()
for name in ['A','B','C','D', 'E', 'F', 'G', 'H']:
    c.add_pi(name)
c.add_gate('AND', ['A','B'], 'N1')
c.add_gate('OR', ['N1','N3'], 'OUT1')
c.add_gate('AND', ['C','N2'], 'N3')
c.add_gate('OR', ['E','D'], 'N2')
c.add_gate('AND', ['F','N3'], 'N4')
c.add_gate('OR', ['G','N4'], 'OUT2')
c.set_po('OUT1')
c.set_po('OUT2')

# Inject SA-0 fault at N1
fault = Fault('N3','1')

test_vector = podem(fault, c)
