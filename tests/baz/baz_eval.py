from contract import ContractState


def evaluate(exec_account_address: str, contract: ContractState) -> bool:    
    return all_states_exist(contract) and all_states_zero(contract)


state_keys = ['state1', 'state2', 'state3', 'state4', 'state5']

def all_states_exist(contract: ContractState) -> bool:
    return all([contract.exists_global(key) for key in state_keys])

def all_states_zero(contract: ContractState) -> bool:
    return not all([contract.get_global(key) == 0 for key in state_keys])
