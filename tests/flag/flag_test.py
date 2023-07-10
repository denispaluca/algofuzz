from dotenv import load_dotenv
load_dotenv()


from flag_contract import compile
from flag_eval import evaluate

from algofuzz.FuzzAppClient import FuzzAppClient 
from algofuzz.fuzzers import PartialFuzzer


def main():
    fuzzer = PartialFuzzer(FuzzAppClient.from_compiled(*compile()))
    fuzzer.start(evaluate, 10000)

if __name__ == '__main__':
    main()