from fwn_contract import compile
from fwn_eval import evaluate
from src.ContractFuzzer import ContractFuzzer, TotalContractFuzzer


def main():
    fuzzer = ContractFuzzer(*compile())
    fuzzer.start(evaluate, 10000)

if __name__ == '__main__':
    main()