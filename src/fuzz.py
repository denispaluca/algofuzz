from pathlib import Path
import random
from typing import Callable
from algosdk import (abi)
from hypothesis import given, settings, target
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
    contract_state = ContractState(app_id)
    contract_state.load(owner_acc[1])
    print(f"Fuzzing contract {contract.name} from account {owner_acc[1]}")
    for i in range(runs):
        method, strategy = random.choice(candidates)
        print(f"Run #{i} executing on method {method.name}: ")
        run(method, strategy, owner_acc, app_id, coverage_history, contract_state, evaluate)


def run(method: abi.Method, strategy, account, app_id, coverage_history, contract_state, evaluate: Callable[[str, ContractState], bool]):
    @settings(max_examples=10)
    @given(strategy)
    def execute(arg):
        print(f"Calling with {arg}")
        call_res, coverage = call(method, account, app_id, arg)
        new_lines_covered = coverage_history.update(coverage)
        contract_state.load(account[1])
        eval_res = evaluate(account[1], contract_state)

        # TARGETS
        # Coverage Guided
        # Can also target the length of new lines
        # target(len(new_lines_covered)
        target(coverage_history.count())

        # State Guided
        target(contract_state.get_unique_global_state_count())
        target(contract_state.get_unique_local_state_count())

        assert eval_res

    try:
        execute()
    except AssertionError:
        print("EVALUATION FAILED")
        exit()
    except Exception as e:
        print(e)