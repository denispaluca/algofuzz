from dotenv import load_dotenv
load_dotenv()

import AlgoTether
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import ContractFuzzer, Driver, PartialFuzzer, TotalFuzzer
from algofuzz.dumper import DataDumper

fuzzers: list[type[ContractFuzzer]] = [PartialFuzzer, TotalFuzzer]

def main():
    evaluate_contract(AlgoTether, 10, 4)

def evaluate_contract(contract, timeout_seconds, reps):
    compiled = contract.compile()
    for chosen_fuzzer in fuzzers:
        for j in range(3):
            driver = Driver(j)
            for i in range(3):
                client = FuzzAppClient.from_compiled(*compiled)
                fuzzer = chosen_fuzzer(client)
                dumper = DataDumper(f"{AlgoTether.__name__}_{fuzzer.__class__.__name__}_{driver}_{i}.csv", 1, False)
                fuzzer.start(
                    timeout_seconds=10, 
                    driver=driver, 
                    dumper=dumper,
                    # suppress_output=True
                )

                dumper.file.close()



    


if __name__ == '__main__':
    main()