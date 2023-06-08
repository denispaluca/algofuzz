# AlgoFuzz
AlgoFuzz is a property-based fuzzing tool for Algorand smart contracts. The tool itself is a prototype written in python. Users are expected to modify and run the source code directly to be able to test it.

## Prerequisites
- [Python 3.10 or higher](https://www.python.org/downloads/)
- [AlgoKit](https://developer.algorand.org/docs/get-started/algokit/) and its dependencies

## Usage
1. Start an Algorand local network with AlgoKit  
`algokit localnet start`

2. In the file `property_test.py` write your property tests inside `evaluate` using the `ContractState` to retrieve the global and local state. i.e:  
```py
def evaluate(exec_account_address: str, contract: ContractState) -> bool:    
    return contract.get_global('nr_users') < 10
```

3. Execute the program with arguments:  
`python src/main.py <approval-path> <clear-path> <contract-path> <state-schema>`
    - **approval-path**: Path to approval teal program (e.g. approval.teal)
    - **clear-path**: Path to clear teal program (e.g. clear.teal)
    - **contract-path**: Path to contract abi json file (e.g. contract.json)
    - **state-schema**: 4 integers representing the state schema (e.g. 2 0 0 0)
        1. Global Uints
        2. Global Bytes
        3. Local Uints
        4. Local Bytes