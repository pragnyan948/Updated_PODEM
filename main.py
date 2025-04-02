import time
from collections import defaultdict
import pdb
import os
import re
from prettytable import PrettyTable
import psutil

def memory_usage():
    # Get current process memory usage in bytes
    process = psutil.Process(os.getpid())  # Current process
    return process.memory_info().rss / 1024 / 1024  # Convert to MB
def count_input_usage(bench_file):
    usage_count = defaultdict(int)

    with open(bench_file, 'r') as file:
        for line in file:
            line = line.strip()
            if '=' in line:  # This line defines a gate
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

    # Print the extracted numbers
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
        print("Max Fanout of the Benchmark b"+str_count+":", max_count)
        if max_count>40:
            bench_set.add(count_bench)
    print("Filtered Benchamrks: ", bench_set)
    pdb.set_trace()

# TO DO: NETLIST READ
def netlist_read():
    return circuit_data

#TO DO:Obtain List Faults
def obtain_list_faults(parent_folder, bench_set):
    return fault_list

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
        F_D, D_B,C, max_time_untestable=basic_podem(basic_circuit, fault_list)
    else:
        F_D, D_B,C, max_time_untestable=proposed_podem(basic_circuit, fault_list)

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
    return coverage, time_elapsed, mem_usage, max_time_untestable, conflict_eff


parent_folder="./Benchmark/I99T/i99t/"
bench_set=filter_benchmark(parent_folder)
#fault_list:2d array of length of bench set 
fault_list=obtain_list_faults(parent_folder, bench_set)
table = PrettyTable()

table.field_names = ["Circuit", "Coverage (Baseline)", "Coverage (Proposed)", "Time Elapsed (Baseline)", "Time Elapsed (Proposed)",
                     "Memory Usage (Baseline)", "Memory Usage (Proposed)", "Max Time Untestable (Baseline)",  "Max Time Untestable (Proposed)", 
                     "Conflict Eff (Baseline)", "Conflict Eff (Proposed)"]


for bench_idx, bench in enumerate(bench_set):
    data_circuit=netlist_read(bench, parent_folder)

    coverage_b, time_elapsed_b, mem_usage_b, max_time_untestable_b, conflict_eff_b=run_algorithm(data_circuit, fault_list[bench_idx], "baseline")
    coverage, time_elapsed, mem_usage, max_time_untestable, conflict_eff=run_algorithm(data_circuit, fault_list[bench_idx], "proposed")

    table.add_row([bench, coverage_b,coverage, time_elapsed_b,  time_elapsed, mem_usage_b, mem_usage,
                       max_time_untestable_b, max_time_untestable, conflict_eff_b, conflict_eff])

print(table)