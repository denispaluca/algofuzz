# AlgoFuzz
![AlgoFuzz-logo](https://github.com/denispaluca/algofuzz/assets/25372894/96fe9a88-02a9-4303-b83f-a955d1dd47a0)

AlgoFuzz is a property-based fuzzing tool for Algorand smart contracts. The tool itself is a prototype written in python. Users are expected to modify and run the source code directly to be able to test it.

## Prerequisites
- [Python 3.10 or higher](https://www.python.org/downloads/)

- [AlgoKit](https://developer.algorand.org/docs/get-started/algokit/) and its dependencies
- [Python Poetry](https://python-poetry.org/)

## Usage
1. Start an Algorand local network with AlgoKit  
`algokit localnet start`

1. Adjust the environment variables in the `.env` file for your localnet if they differ. 

1. Install all dependencies with poetry
`poetry install`

1. In the file `property_test.py` write your property tests inside `evaluate` using the `ContractState` to retrieve the global and local state. i.e:  
    ```py
    def evaluate(exec_account_address: str, contract: ContractState) -> bool:    
        return contract.get_global('nr_users') < 10
    ```

1. Execute the program with arguments:  
`poetry run start -h`
