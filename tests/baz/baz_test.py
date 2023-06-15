from dotenv import load_dotenv
load_dotenv()

from baz_contract import compile
from baz_eval import evaluate
from algofuzz.FuzzAppClient import FuzzAppClient 
from algofuzz.ContractFuzzer import TotalContractFuzzer


def main():
    approval, clear, contract, schema = compile()
    app_client = FuzzAppClient.from_compiled(approval, clear, contract, schema)
    fuzzer = TotalContractFuzzer(app_client)
    fuzzer.start(evaluate, 10000)

if __name__ == '__main__':
    main()