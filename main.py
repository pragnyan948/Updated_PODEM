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

def read_csv_file(file_path):

    data = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f, skipinitialspace=True)  
        for row in reader:
            for key in ['#List of Collapsed Faults', '#Controllabilty-0', '#Controllabilty-1', '#Observability-0', '#Observability-1']:
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
        #print(f"Key: {k} → Value: {v}")
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
    for count_bench in folder_numbers:
        str_count=str(count_bench)if count_bench>9 else "0"+str(count_bench)
        directory_name=parent_folder+"b"+str_count
        bench_file = directory_name+"/b"+ str_count+"_opt_C.bench"
        usage_data = count_input_usage(bench_file)

        #for signal, count in usage_data.items():
            #print(f"{signal}: {count}")
        max_signal = max(usage_data, key=usage_data.get)
        max_count = usage_data[max_signal]
        #print("Max Fanout of the Benchmark b"+str_count+":", max_count)
        if max_count>40:
            bench_set.add(count_bench)
        #pdb.set_trace()
        
    print("Filtered Benchamrks: ", bench_set)
    return bench_set

#TO DO:Obtain List Faults
def obtain_list_faults(file_path, circuit_data):
    #Get gate faults from the csv file
    data=read_csv_file("Fault_Collapsing.csv")
    usage_data = count_input_usage(file_path)

    converted_faults = []
    collapsed_faults = []
    num_gates=0
    num_gate_nodes=0
    for key in circuit_data.keys():
        value=circuit_data[key]
        type=value.typ
        inputs=value.inputs
        output=value.name
        if type!='INPUT' and type!='OUTPUT':
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
    print("Benchmark: ", file_path)
    print("Number of gates: ", num_gates)
    print("Maximum Fanout of the Benchmark: ", max(usage_data.values()))
    print("Number of Stuck at Faults that can occur: ", 2*num_gate_nodes)
    print("Number of Stuck at Faults after Gate collapsing", len(converted_faults))   
    print("Number of Stuck at Faults after fanout free node collapsing", len(collapsed_faults))
    #pdb.set_trace()
    
    return collapsed_faults

#TO DO: Observability and Controllability Map
#CO_0: Observability of the nodes to propagate 0 to primary outputs
#CO_1: Observability of the nodes to propagate 1 to primary outputs
#CC_0: Controllability of the nodes to be set at 0 from primary inputs
#CC_1: Controllability of the nodes to be set at 1 from primary inputs
def COP_map(circuit_data):
    #forward traversal
    #Read gates
        #Get controllability of the gate from csv file
        #Add it to the dynamic programming table
    #backward traversal
    #Read gates
        #Get observability of the gate from csv file
        #Add it to the dynamic programming table
    return CO_0, CO_1, CC_0, CC_1

#TO DO: Basic PODEM
#F_D: Number of Detected Faults
#D_B: Total Number of Decisions Backtracked
#C: Total Number of Conflicts
#F: Total Number of Faults
def basic_podem(basic_circuit, fault_list):
    return F_D, D_B,C, max_time_untestable

#TO DO: Proposed PODEM
def proposed_podem(basic_circuit, fault_list):

    return F_D, D_B,C, max_time_untestable

def run_algorithm(circuit_data, fault_list, mode):
    start_time=time.time()
    mem_before = memory_usage()
    # TO DO: DEVELOP 1) BASIC PODEM for comparison 2) OBSERVABILITY & CONTROLLABILITY-AWARE PODEM
    if mode=="baseline":
        F_D, D_B,C, max_time_untestable, test_patterns=basic_podem(circuit_data, fault_list)
    else:
        CO_0, CO_1, CC_0, CC_1=COP_map(circuit_data)
        F_D, D_B,C, max_time_untestable, test_patterns=proposed_podem(circuit_data, fault_list)

    time_elapsed=time.time()-start_time
    mem_usage = memory_usage()-mem_before

    F=len(fault_list)

    coverage=F_D/F
     
    conflict_eff=D_B/C
    print("Summary for benchmark ", bench)
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

    test_patterns_b, coverage_b, time_elapsed_b, mem_usage_b, max_time_untestable_b, conflict_eff_b=run_algorithm(data_circuit, fault_list, "baseline")
    test_patterns, coverage, time_elapsed, mem_usage, max_time_untestable, conflict_eff=run_algorithm(data_circuit, fault_list, "proposed")

    table.add_row([bench, coverage_b,coverage, time_elapsed_b,  time_elapsed, mem_usage_b, mem_usage,
                       max_time_untestable_b, max_time_untestable, conflict_eff_b, conflict_eff])

print(table)