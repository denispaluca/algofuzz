from src.ContractFuzzer import ContractState


def evaluate(exec_account_address: str, contract: ContractState) -> bool:    
    return state_is_zero(contract)


def state_is_zero(contract: ContractState) -> bool:
    key = 'state'
    if not contract.exists_global(key):
        return False
    
    state = contract.get_global(key)
    cond = state == 0
    return cond
