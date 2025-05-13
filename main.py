import time
from collections import defaultdict
import pdb
import os
import re
from prettytable import PrettyTable
import psutil
from read_netlist import read_netlist
import csv
import ast
import sys
import podem_new
sys.setrecursionlimit(100000)
DEBUG=False

def read_csv_file(file_path):

    data = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f, skipinitialspace=True)  
        for row in reader:
            for key in ['#List of Collapsed Faults', '#Controllabilty-0', '#Controllabilty-1', '#Observability']:
                row[key] = ast.literal_eval(row[key])
            row['#Inputs'] = int(row['#Inputs'])
            row['#Collapsed Faults'] = int(row['#Collapsed Faults'])
            data.append(row)

    #for entry in data:
        #print(entry)

    gate_dict = {}

    for row in data:
        key = (str(row['Gate'])+'-'+str(row['#Inputs']))  
        gate_dict[key] = row  

    #for k, v in gate_dict.items():
        #print(f"Key: {k} ? Value: {v}")
    return gate_dict

def memory_usage():
    # Get current process memory usage in bytes
    process = psutil.Process(os.getpid())  
    return process.memory_info().rss / 1024 / 1024  # Convert to MB
def count_input_usage(bench_file):
    usage_count = defaultdict(int)

    with open(bench_file, 'r') as file:
        for line in file:
            line = line.strip()
            if '=' in line:  
                parts = line.split('=')
                inputs = parts[1].split('(')[1].strip(')').split(',')
                inputs = [i.strip() for i in inputs]
                for inp in inputs:
                    usage_count[inp] += 1
    #pdb.set_trace()
    return usage_count

def get_subfolder_numbers(parent_folder):

    subfolders = os.listdir(parent_folder)

    folder_numbers = []
    for folder in subfolders:
        match = re.match(r'b(\d+)', folder)  
        if match:
            folder_numbers.append(int(match.group(1)))  
    
    return folder_numbers

def filter_benchmark(parent_folder):
    folder_numbers = sorted(get_subfolder_numbers(parent_folder))

    print(f"Subfolder numbers: {folder_numbers}")
    mode="baseline"
    #count_bench=1
    bench_set=set()

    # change this to test only 1 circuit
    # folder_numbers = [17]
    for count_bench in folder_numbers:
        if count_bench in {4,5,7, 11, 12,14, 15, 16, 17, 18, 19, 20, 21, 22, 23}:
            continue
        str_count=str(count_bench)if count_bench>9 else "0"+str(count_bench)
        directory_name=parent_folder+"b"+str_count
        bench_file = directory_name+"/b"+ str_count+"_opt_C.bench"
        usage_data = count_input_usage(bench_file)

        #for signal, count in usage_data.items():
            #print(f"{signal}: {count}")
        max_signal = max(usage_data, key=usage_data.get)
        max_count = usage_data[max_signal]
        #print("Max Fanout of the Benchmark b"+str_count+":", max_count)
        if max_count>0:
            bench_set.add(count_bench)
        #pdb.set_trace()
        
    print("Filtered Benchamrks: ", bench_set)
    return bench_set

def obtain_list_faults(file_path, circuit_data):
    #Get gate faults from the csv file
    data=read_csv_file("Fault_Collapsing.csv")
    usage_data = count_input_usage(file_path)

    converted_faults = []
    collapsed_faults = []
    num_gates, num_gate_nodes, num_inputs, num_outputs=0, 0, 0, 0

    for key in circuit_data.keys():
        value=circuit_data[key]
        type=value.typ
        inputs=value.inputs
        output=value.name
        if type=='INPUT':
            num_inputs+=1
        elif type=='OUTPUT':
            num_outputs+=1
        else:
            num_gates+=1
            num_gate_nodes+=len(inputs)+1 #1 for gate output node
            list_faults=data.get(str(type)+'-'+str(len(inputs)))["#List of Collapsed Faults"]
            input_mapping = {f'I{i+1}': output+"."+inputs[i] for i in range(len(inputs))}
            output_mapping = {'O1': output+"."+output}  

            for fault in list_faults:
                wire, val = fault.split('/')
                if wire in input_mapping:
                    new_fault = f"{input_mapping[wire]}/{val}"
                elif wire in output_mapping:
                    new_fault = f"{output_mapping[wire]}/{val}"
                else:
                    new_fault = fault  
                converted_faults.append(new_fault)
        

    for fault in converted_faults:
        key=fault.split('.')[1].split('/')[0]
        #print("Key: ", key)
        if usage_data[key] == 1:
            if f'{key}.{key}/1' in fault or f'{key}.{key}/0' in fault:
                continue
            else:
                collapsed_faults.append(fault)
        else:
            if key in fault:
                collapsed_faults.append(fault)
    if DEBUG:
        print("Benchmark: ", file_path)
        print("Number of inputs: ", num_inputs)
        print("Number of outputs: ", num_outputs)
        print("Number of gates: ", num_gates)
        print("Maximum Fanout of the Benchmark: ", max(usage_data.values()))
        print("Number of Stuck at Faults that can occur: ", 2*num_gate_nodes)
        print("Number of Stuck at Faults after Gate collapsing", len(converted_faults))   
        print("Number of Stuck at Faults after fanout free node collapsing", len(collapsed_faults))
    #pdb.set_trace()
    
    return collapsed_faults


#CO_0: Observability of the nodes to propagate 0 to primary outputs
#CO_1: Observability of the nodes to propagate 1 to primary outputs
#CC_0: Controllability of the nodes to be set at 0 from primary inputs
#CC_1: Controllability of the nodes to be set at 1 from primary inputs
def COP_map(circuit_data):
    data=read_csv_file("Fault_Collapsing.csv")
    #pdb.set_trace()
    CO, CC_0, CC_1={}, {}, {}
    CC_0_map, CC_1_map, CO_map={}, {}, {}
    input_mapping, output_mapping={}, {}
    #forward traversal
    
    def controllability_eval(CC_map, CC0_in, CC1_in):
        inputs = []
        output = None
        offset = 0
        use_min = False
        CC_in={}
        for item in CC_map:
            signal, value = item.split(':')
            if signal.startswith('O'):
                output = signal
                if 'min' in value.lower():
                    use_min = True
                    offset = int(value.lower().replace('min', '').replace('+', '').strip())
                else:
                    offset = int(value.replace('+', '').strip())
            else:
                inputs.append(signal)
                CC_in[signal] = CC0_in[signal] if value == '0' else CC1_in[signal]

        if use_min:
            CC = min(CC_in[inp] for inp in inputs) + offset
        else:
            CC = sum(CC_in[inp] for inp in inputs) + offset
        return CC    
        
    def compute_node_controllability(node):
        #pdb.set_trace()
        if node in CC_0 and node in CC_1:
            return  
        value = circuit_data[node]
        type = value.typ
        inputs = value.inputs
        output = value.name if type != 'INPUT' and type!='OUTPUT' else "_".join(value.name.split("_")[1:])
        #pdb.set_trace()

        if type == 'INPUT':
            CC_0[output] = 1
            CC_1[output] = 1
            return
        if type == 'OUTPUT':
            CO[output] = 0
            return

        for inp in inputs:
            if inp not in CC_0:
                compute_node_controllability(inp)

        CC_0_map[output] = data.get(str(type) + '-' + str(len(inputs)))["#Controllabilty-0"]
        CC_1_map[output] = data.get(str(type) + '-' + str(len(inputs)))["#Controllabilty-1"]
        
        input_mapping[output] = {f'I{i+1}': inputs[i] for i in range(len(inputs))}
        CC0_in, CC0_in= {}, {}
        CC0_in = {f'I{i+1}': CC_0[inp] for i, inp in enumerate(inputs)}
        CC1_in = {f'I{i+1}': CC_1[inp] for i, inp in enumerate(inputs)}

        # CC0 and CC1
        CC_0[output] = controllability_eval(CC_0_map[output], CC0_in, CC1_in)
        CC_1[output] = controllability_eval(CC_1_map[output], CC0_in, CC1_in)


    def observability_eval(CO_map, CO, CC0_in, CC1_in, index):
        inputs = []
        output = None
        offset = 0
        use_min = False
        CC_in={}

        for item in CO_map:
            signal, value = item.split(':')
            if signal.startswith('O'):
                output = signal
                if 'min' in value.lower():
                    use_min = True
                    offset = int(value.lower().replace('min', '').replace('+', '').strip())
                else:
                    offset = int(value.replace('+', '').strip())
            else:
                if value == '1':
                    #pdb.set_trace()
                    bool_CC1 = signal.split('-')[0][-1]
                    inp=signal.split('-')[1]
                    if int(inp[-1])==index+1:
                        #pdb.set_trace()
                        inp='I1'
                    inputs.append(inp)
                    CC_in[inp] = CC1_in[inp] if bool_CC1 else CC0_in[inp]


        if use_min:
            CO_in = min(CC_in[inp] for inp in inputs) + offset+CO
        else:
            CO_in = sum(CC_in[inp] for inp in inputs) + offset+CO
        #pdb.set_trace()
        
        return CO_in    


    def compute_node_observability(node):
        value = circuit_data[node]
        type = value.typ
        inputs = value.inputs
        output = value.name if type != 'INPUT' and type!='OUTPUT' else "_".join(value.name.split("_")[1:])
        if type == 'INPUT' or type=='OUTPUT':
            return
        # Recursively compute observability of output node first
        if output not in CO or CO[output] == -1:
            for out_node in reversed(list(circuit_data.keys())):
                if output in circuit_data[out_node].inputs:
                    compute_node_observability(out_node)

        # Now compute CO for the inputs
        CO_map[output] = data.get(str(type) + '-' + str(len(inputs)))["#Observability"]
        input_mapping[output] = {f'I{i+1}': inputs[i] for i in range(len(inputs))}
        CC0_in = {f'I{i+1}': CC_0[inp] for i, inp in enumerate(inputs)}
        CC1_in = {f'I{i+1}': CC_1[inp] for i, inp in enumerate(inputs)}
        #print("Output: ", output)
        #print("Inputs: ", inputs)
        
        for index, inp in enumerate(inputs):
            CO_temp = observability_eval(CO_map[output], CO[output], CC0_in, CC1_in, index)
            if inp not in CO or CO[inp] == -1:
                CO[inp] = CO_temp
            else:
                CO[inp] = min(CO[inp], CO_temp)
            #print(f"CO[{inp}] = {CO[inp]}")
        #pdb.set_trace()

    # Forward traversal (compute controllability first)
    for node in circuit_data.keys():
        compute_node_controllability(node)
    if DEBUG:
        print("length of CC0:        ", len(CC_0))
        print("length of CC1:        ",len(CC_1))
    for key in CC_0.keys():
        if key not in CO:
            CO[key] = -1
    # Backward traversal (compute observability)
    #pdb.set_trace()

    for node in reversed(list(circuit_data.keys())):
        #print(node)
        compute_node_observability(node)
    #pdb.set_trace()
    if DEBUG:
        print("length of CO:", len(CO))
    #pdb.set_trace()
    
    return CO, CC_0, CC_1



#F_D: Number of Detected Faults
#D_B: Total Number of Decisions Backtracked
#C: Total Number of Conflicts
#F: Total Number of Faults

def run_algorithm(circuit_data, fault_list, mode):
    start_time=time.time()
    mem_before = memory_usage()
    #1) BASIC PODEM for comparison 2) OBSERVABILITY & CONTROLLABILITY-AWARE PODEM
    if mode=="baseline":
        if DEBUG:
            print("Running Basic PODEM")
        F_D, D_B,C, max_time_untestable, test_patterns=podem_new.basic_podem(file_path, fault_list,mode, None, None, None)
        #F_D, D_B,C, max_time_untestable, test_patterns=basic_podem(circuit_data, fault_list)
    else:
        if DEBUG:
            print("Running OBSERVABILITY & CONTROLLABILITY-AWARE PODEM")
        CO, CC_0, CC_1=COP_map(circuit_data)
        F_D, D_B,C, max_time_untestable, test_patterns=podem_new.basic_podem(file_path, fault_list,mode, CC_0, CC_1, CO)
        #F_D, D_B,C, max_time_untestable, test_patterns=0, 0, 100, 0, 0
    #pdb.set_trace()
    time_elapsed=time.time()-start_time
    mem_usage = memory_usage()-mem_before

    F=len(fault_list)

    coverage=F_D/F
    
    conflict_eff=D_B/C if C!=0 else 'No conflicts'
    if DEBUG:
        print("test_patterns: ", test_patterns)
        print("Summary for benchmark ", bench)
        print("Number of Faults: ", F)
        print("Number of Detected Faults: ", F_D)
        print("Number of Decisions Backtracked: ", D_B)
        print("Number of Conflicts: ", C)
        print("Fault Coverage: ", coverage)
        print("Time consumed by the algorithm:",time_elapsed)
        print("Memory consumed by the algorithm:",mem_usage)
        print("Untestable Fault Detection Efficiency:", max_time_untestable)
        print("Conflict Resolution Efficiency:", conflict_eff)
    return test_patterns, coverage, time_elapsed, mem_usage, max_time_untestable, conflict_eff


parent_folder="./Benchmark/I99T/i99t/"
bench_set=filter_benchmark(parent_folder)
#fault_list:2d array of length of bench set 
table = PrettyTable()

table.field_names = ["Circuit", "Coverage (Baseline)", "Coverage (Proposed)", "Time Elapsed (Baseline)", "Time Elapsed (Proposed)",
                     "Memory Usage (Baseline)", "Memory Usage (Proposed)", "Max Time Untestable (Baseline)",  "Max Time Untestable (Proposed)", 
                     "Conflict Eff (Baseline)", "Conflict Eff (Proposed)"]


for bench_idx, bench in enumerate(bench_set):
    #pdb.set_trace()
    file_path = f"{parent_folder}b{bench:02d}/b{bench:02d}_opt_C.bench"
    data_circuit=read_netlist(file_path)
    fault_list=obtain_list_faults(file_path, data_circuit)
    #pdb.set_trace()
    #print(fault_list)

    # enable this to enable PODEM
    # podem_new.basic_podem(file_path, fault_list)

    test_patterns_b, coverage_b, time_elapsed_b, mem_usage_b, max_time_untestable_b, conflict_eff_b=run_algorithm(data_circuit, fault_list, "baseline")
    test_patterns, coverage, time_elapsed, mem_usage, max_time_untestable, conflict_eff=run_algorithm(data_circuit, fault_list, "proposed")

    table.add_row([bench, coverage_b,coverage, time_elapsed_b,  time_elapsed, mem_usage_b, mem_usage,
                       max_time_untestable_b, max_time_untestable, conflict_eff_b, conflict_eff])
    #print(table)
    #pdb.set_trace()


print(table)
with open("Output_PODEM_vs_Proposed PODEM.txt", "w") as file:
    file.write(table.get_string())
