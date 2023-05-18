from pathlib import Path
import random
from typing import Callable
from algosdk import (abi)
from hypothesis import given, settings
from strategies import get_method_strategy
from contract import call, ContractState
from CoverageHistory import CoverageHistory

def fuzz(contract_path: Path, owner_acc, app_id, evaluate, runs=100):
    contract = abi.Contract.from_json(contract_path.open().read())
    candidates = [
        (method, get_method_strategy(method))
        for method in contract.methods
    ]
    coverage_history = CoverageHistory()
    contract_state = ContractState()
    contract_state.load(owner_acc[1])
    print(f"Fuzzing contract {contract.name} from account {owner_acc[1]}")
    for i in range(runs):
        method, strategy = random.choice(candidates)
        print(f"Run #{i} executing on method {method.name}: ")
        run(method, strategy, owner_acc, app_id, coverage_history, evaluate)

def run(method: abi.Method, strategy, account, app_id, coverage_history, contract_state, evaluate: Callable[[str, int], bool]):
    @settings(max_examples=10)
    @given(strategy)
    def execute(arg):
        print(f"Calling with {arg}")
        call_res, coverage = call(method, account, app_id, arg)
        new_lines_covered = coverage_history.update(coverage)
        contract_state.load(account[1])
        eval_res = evaluate(account[1], app_id)
        assert eval_res

    try:
        execute()
    except AssertionError:
        print("EVALUATION FAILED")
        exit()
    except Exception as e:
        print(e)