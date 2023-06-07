from baz_contract import compile
from baz_eval import evaluate
from src.ContractFuzzer import TotalContractFuzzer


def main():
    fuzzer = TotalContractFuzzer(*compile())
    fuzzer.start(evaluate, 10000)

if __name__ == '__main__':
    main()