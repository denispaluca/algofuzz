from pathlib import Path
import random
from typing import Callable
from algosdk import (abi)
from hypothesis import given, settings, target, strategies as st
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
        target(contract_state.count_unique_global_states())
        target(contract_state.count_unique_local_states())

        assert eval_res

    try:
        execute()
    except AssertionError:
        print("EVALUATION FAILED")
        exit()
    except Exception as e:
        print(e)


def fuzz2(contract_path: Path, owner_acc, app_id, evaluate, runs=100):
    contract = abi.Contract.from_json(contract_path.open().read())
    candidates = [
        (method, get_method_strategy(method))
        for method in contract.methods
    ]
    coverage_history = CoverageHistory()
    contract_state = ContractState(app_id)
    contract_state.load(owner_acc[1])
    print(f"Fuzzing contract {contract.name} from account {owner_acc[1]}")

    @settings(max_examples=runs, print_blob=True)
    @given(st.integers(0, len(candidates)))
    def execute(i: int):
        method, strategy = candidates[i]
        print(f"Run #{i} executing on method {method.name}: ")

        @settings(max_examples=10)
        @given(strategy)
        def execute_run(arg):
            print(f"Calling with {arg}")
            call_res, coverage = call(method, owner_acc, app_id, arg)
            new_lines_covered = coverage_history.update(coverage)
            contract_state.load(owner_acc[1])
            eval_res = evaluate(owner_acc[1], contract_state)
            target(coverage_history.count())
            target(contract_state.count_unique_global_states())
            target(contract_state.count_unique_local_states())

            assert eval_res

        execute_run()

        # TARGETS
        # Coverage Guided
        # Can also target the length of new lines
        # target(len(new_lines_covered)
        target(coverage_history.count())

        # State Guided
        target(contract_state.count_unique_global_states())
        target(contract_state.count_unique_local_states())

    try:
        execute()
    except AssertionError:
        print("EVALUATION FAILED")
        exit()
    except Exception as e:
        print(e)