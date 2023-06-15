from dotenv import load_dotenv
load_dotenv()


from fwn_contract import compile
from fwn_eval import evaluate

from algofuzz.FuzzAppClient import FuzzAppClient 
from algofuzz.ContractFuzzer import ContractFuzzer, TotalContractFuzzer


def main():
    fuzzer = ContractFuzzer(FuzzAppClient.from_compiled(*compile()))
    fuzzer.start(evaluate, 10000)

if __name__ == '__main__':
    main()