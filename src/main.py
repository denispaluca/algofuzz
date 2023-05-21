import argparse
from pathlib import Path
from typing import Any
from contract import deploy
from fuzz import fuzz, fuzz2
from property_test import evaluate

def main(*args: Any, **kwds: Any) -> Any:
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

    args = parser.parse_args()

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
    
    app_id, owner_acc = deploy(approval_path, clear_path, args.schema)
    fuzz2(contract_path, owner_acc, app_id, evaluate)

    


if __name__ == '__main__':
    main()