import os
from dotenv import load_dotenv
load_dotenv()

import AlgoTether
import ExchangeToken
from importlib.machinery import SourceFileLoader
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import ContractFuzzer, Driver, PartialFuzzer, TotalFuzzer
from algofuzz.dumper import DataDumper

fuzzers: list[type[ContractFuzzer]] = [PartialFuzzer, TotalFuzzer]

def main():
    modules = get_verismart_modules()
    half_hour = 30 * 60
    evaluate_contract(AlgoTether, half_hour, 6)
    evaluate_contract(ExchangeToken, half_hour, 6)

    mins_10 = 10 * 60
    for module in modules:
        evaluate_contract(module, mins_10, 6)

def get_verismart_modules():
    dir = os.path.dirname(AlgoTether.__file__)
    verismart = os.path.join(dir, 'algorand_veriSmart')
    onlyfiles = [(f.replace('.py', ''), file) for f in os.listdir(verismart) if os.path.isfile(file := os.path.join(verismart, f))]
    onlyfiles.sort(key=lambda x: x[0])
    modules = [SourceFileLoader(f, file).load_module() for f, file in onlyfiles]
    return modules

def evaluate_contract(contract, timeout_seconds, reps):
    compiled = contract.compile()
    for chosen_fuzzer in fuzzers:
        for j in range(3):
            driver = Driver(j)
            for i in range(reps):
                client = FuzzAppClient.from_compiled(*compiled)
                fuzzer = chosen_fuzzer(client)
                dumper = DataDumper(f"benchmarks/{contract.__name__}_{fuzzer.__class__.__name__}_{driver}_{i}.csv", 1, False)
                fuzzer.start(
                    timeout_seconds=timeout_seconds, 
                    driver=driver, 
                    dumper=dumper,
                    # suppress_output=True
                )

                dumper.file.close()



    


if __name__ == '__main__':
    main()