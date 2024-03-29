from curses import wrapper
from dotenv import load_dotenv
load_dotenv()


from fwn_contract import compile
from fwn_eval import evaluate

from algofuzz.FuzzAppClient import FuzzAppClient 
from algofuzz.fuzzers import TotalFuzzer, PartialFuzzer, Driver


def main(*args, **kwds):
    fuzzer = TotalFuzzer(FuzzAppClient.from_compiled(*compile()))
    fuzzer.start(evaluate, 10000)

if __name__ == '__main__':
    main()