from dotenv import load_dotenv
load_dotenv()

import argparse
from pathlib import Path
from typing import Any
from algofuzz.property_test import evaluate
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import Driver, PartialFuzzer, TotalFuzzer, ContractFuzzer


def main(*args: Any, **kwds: Any) -> Any:
    contract_args, fuzzer_args = parse_args()
    app_client = FuzzAppClient.from_compiled(*contract_args)
    fuzzer_type, driver, driver_coef, breakout_coef, suppress_output, assertion_mode, runs, timeout = fuzzer_args
    fuzzer = fuzzer_type(app_client)

    fuzzer.start(
        eval = evaluate if not assertion_mode else None,
        driver = driver,
        breakout_coef = breakout_coef,
        suppress_output = suppress_output,
        runs = runs,
        timeout_seconds = timeout,
        schedule_coef = driver_coef
    )

    

ContractArgs = tuple[str, str, str, tuple[int, int, int, int]]


fuzzer_map: dict[str, type[ContractFuzzer]] = {
    'total': TotalFuzzer,
    'partial': PartialFuzzer
}

driver_map = {
    'coverage': Driver.COVERAGE,
    'state': Driver.STATE,
    'combined': Driver.COMBINED
}

def parse_args():
    parser = argparse.ArgumentParser(description='Fuzzer for Algorand smart contracts')
    parser.add_argument(
        'approval', 
        type=str,
        help='Approval program of the contract in TEAL'
    )
    parser.add_argument(
        'clear', 
        type=str,
        help='Clear program of the contract in TEAL'
    )
    parser.add_argument(
        'contract', 
        type=str,
        help='Contract json ABI'
    )
    parser.add_argument(
        'schema',
        type=int,
        nargs=4,
        help='State schema of the contracts (Global Ints, Global Bytes, Local Ints, Local Bytes)'
    )
    parser.add_argument(
        '--fuzzer',
        default='total',
        choices=fuzzer_map.keys(),
        help='Fuzzer to use'
    )
    parser.add_argument(
        '--driver',
        default='combined',
        choices=driver_map.keys(),
        help='Fuzzing driver to use'
    )
    parser.add_argument(
        '--driver_coef',
        type=restricted_float,
        default=0.5,
        help='Weight of the state driver in the combined driver'
    )
    parser.add_argument(
        '--breakout_coef',
        type=restricted_float,
        default=0.1,
        help='Probability of breakout (choosing a candidate from seeds instead of population)'
    )
    parser.add_argument(
        '--suppress_output',
        type=bool,
        default=False,
        help='Supress output of the fuzzer'
    )
    parser.add_argument(
        '-a',
        '--assertion',
        type=bool,
        default=False,
        const=True,
        nargs='?',
        help="Run the fuzzer in assertion mode"
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=1000,
        help="Number of calls to execute before stopping the fuzzer"
    )
    parser.add_argument(
        '--timeout',
        type=int,
        help="Number of seconds to run the fuzzer (overrides --runs)"
    )

    args = parser.parse_args()

    return parse_contract(args), parse_fuzzer(args)

def parse_contract(args) -> ContractArgs:
    approval_path = Path(args.approval)
    clear_path = Path(args.clear)
    contract_path = Path(args.contract)

    if not approval_path.is_file():
        print("Path to approval program is wrong")
        raise SystemExit(1)
    
    if not clear_path.is_file():
        print("Path to clear program is wrong")
        raise SystemExit(1)
    
    if not contract_path.is_file():
        print("Path to contract ABI is wrong")
        raise SystemExit(1)
    
    with open(approval_path) as f:
        approval = f.read()
    
    with open(clear_path) as f:
        clear = f.read()

    with open(contract_path) as f:
        contract = f.read()
    
    return approval, clear, contract, args.schema

def parse_fuzzer(args):
    fuzzer = fuzzer_map[args.fuzzer]
    driver = driver_map[args.driver]

    return fuzzer, driver, args.driver_coef, args.breakout_coef, args.suppress_output, args.assertion, args.runs, args.timeout

    
def restricted_float(x):
    try:
        x = float(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%r not a floating-point literal" % (x,))

    if x <= 0.0 or x >= 1.0:
        raise argparse.ArgumentTypeError("%r not in range [0.0, 1.0]"%(x,))
    return x


if __name__ == '__main__':
    main()
    # try:
    #     wrapper(main)
    # except KeyboardInterrupt:
    #     print("Exiting...")