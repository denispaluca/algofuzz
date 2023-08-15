import os
from dotenv import load_dotenv
load_dotenv()
import json

import AlgoTether
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import ContractFuzzer, Driver, PartialFuzzer, TotalFuzzer

fuzzers: list[type[ContractFuzzer]] = [PartialFuzzer, TotalFuzzer]

def main():
    evaluate_contract(AlgoTether, 2*60, 5)

def evaluate_contract(contract, timeout_seconds, reps):
    config_info = {}
    compiled = contract.compile()
    for chosen_fuzzer in fuzzers:
        for coef in range(1,10):
            real_coef = coef/10
            driver = Driver.COMBINED
            info = f"{chosen_fuzzer.__name__}_coef_{real_coef}"
            config_info[info] = []
            print(f"{info}: ", end=' ', flush=True)
            for i in range(reps):
                client = FuzzAppClient.from_compiled(*compiled)
                fuzzer = chosen_fuzzer(client)
                fuzzer.start(
                    timeout_seconds=timeout_seconds, 
                    driver=driver, 
                    suppress_output=True,
                    schedule_coef=real_coef
                )

                config_info[info].append({
                    "call_count": fuzzer.call_count,
                    "rejected_calls": fuzzer.rejected_calls,
                    "percentage_rejected": fuzzer.rejected_calls/fuzzer.call_count,
                    "lines_covered": len(fuzzer.covered_lines),
                    "percent_covered": len(fuzzer.covered_lines)/fuzzer.lines_count,
                    "unique_paths": fuzzer.cov_paths,
                    "unique_transitions": fuzzer.transitions_count
                })

                print("#", end='', flush=True)
            print()
    print()

    averages = {}
    max_for_metric = {}
    min_for_metric = {}
    for key in config_info:
        averages[key] = {}
        for metric in config_info[key][0]:
            averages[key][metric] = sum([config_info[key][i][metric] for i in range(reps)])/reps

            if metric not in max_for_metric:
                max_for_metric[metric] = (key, averages[key][metric])
                
            if metric not in min_for_metric:
                min_for_metric[metric] = (key, averages[key][metric])

            if averages[key][metric] > max_for_metric[metric][1]:
                max_for_metric[metric] = (key, averages[key][metric])

            if averages[key][metric] < min_for_metric[metric][1]:
                min_for_metric[metric] = (key, averages[key][metric])
    

    file = open("benchmarks/coef/averages.json", "w+")
    file.write(json.dumps(averages, indent=2))
    file.close()

    file = open("benchmarks/coef/max_for_metric.json", "w+")
    file.write(json.dumps(max_for_metric, indent=2))
    file.close()

    file = open("benchmarks/coef/min_for_metric.json", "w+")
    file.write(json.dumps(min_for_metric, indent=2))
    file.close()




    


if __name__ == '__main__':
    main()