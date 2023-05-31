import hashlib
from pathlib import Path
import pickle
import random
import time
from typing import Callable, Set, Union, Sequence, Dict, List
from algosdk import (abi)
from CoverageHistory import CoverageHistory

from contract import ContractState, call, deploy
from mutate import MethodMutator

class Seed:
    """Represent an input with additional attributes"""

    def __init__(self, data) -> None:
        """Initialize from seed data"""
        self.data = data

        # These will be needed for advanced power schedules
        self.coverage: Set[int] = set()
        self.distance: Union[int, float] = -1
        self.energy = 0.0

    def __str__(self):
        """Returns data as string representation of the seed"""
        return self.data.__str__()

    __repr__ = __str__



def getPathID(coverage: set[int]) -> str:
    """Returns a unique hash for the covered statements"""
    pickled = pickle.dumps(sorted(coverage))
    return hashlib.md5(pickled).hexdigest()

class PowerSchedule:
    """Define how fuzzing time should be distributed across the population."""

    def __init__(self, exponent: int = 5) -> None:
        """Constructor"""
        self.path_frequency: Dict = {}
        self.exponent = exponent

    def assignEnergy(self, population: Sequence[Seed]) -> None:
        """Assigns each seed the same energy"""
        for seed in population:
            path_id = getPathID(seed.coverage)
            if path_id not in self.path_frequency:
                self.path_frequency[path_id] = 1
            
            seed.energy = 1 / (self.path_frequency[path_id] ** self.exponent)

    def normalizedEnergy(self, population: Sequence[Seed]) -> List[float]:
        """Normalize energy"""
        energy = list(map(lambda seed: seed.energy, population))
        sum_energy = sum(energy)  # Add up all values in energy
        assert sum_energy != 0
        norm_energy = list(map(lambda nrg: nrg / sum_energy, energy))
        return norm_energy

    def choose(self, population: Sequence[Seed]) -> Seed:
        """Choose weighted by normalized energy."""
        self.assignEnergy(population)
        norm_energy = self.normalizedEnergy(population)
        seed: Seed = random.choices(population, weights=norm_energy)[0]
        return seed
    
    def addPath(self, cov: set[int]) -> None:
        """Add a new path to the schedule"""
        path_id = getPathID(cov)
        if path_id not in self.path_frequency:
            self.path_frequency[path_id] = 1
        self.path_frequency[path_id] += 1

class ContractFuzzer:
    def __init__(self, approval_path: Path, clear_path: Path, abi_path: Path, schema: tuple[int,int,int,int]):
        self.approval_path = approval_path
        self.clear_path = clear_path
        self.schema = schema
        self.abi = abi.Contract.from_json(abi_path.open().read())

        self.population: dict[str, list[Seed]] = {}
        self.mutators: dict[str, MethodMutator] = {}
        self.schedulers: dict[str, PowerSchedule] = {}
        for method in self.abi.methods:
            mutator = MethodMutator(method)
            self.mutators[method.name] = mutator
            self.population[method.name] = [Seed(mutator.seed())]
            self.schedulers[method.name] = PowerSchedule()
        
        self.coverage = CoverageHistory()
        self.app_id = None
        self.owner_acc = None

    def start(self, eval: Callable[[str, ContractState], bool], runs: int = 100):
        self.app_id, self.owner_acc = deploy(self.approval_path, self.clear_path, self.schema)
        self.contract_state = ContractState(self.app_id)
        self.contract_state.load(self.owner_acc[1])

        print(f"Fuzzing contract {self.abi.name} (id: {self.app_id}) from account {self.owner_acc[1]}")

        try:
            self._fuzz(eval, runs)
        except AssertionError:
            print("EVALUATION FAILED")
            exit()

    def _call(self, method: abi.Method, args):
        res, cov = call(method, self.owner_acc, self.app_id, args)
        new_lines_covered = self.coverage.update(cov)
        self.contract_state.load(self.owner_acc[1])

        covSet = set(cov)
        self.schedulers[method.name].addPath(covSet)
        if len(new_lines_covered) > 0:
            seed = Seed(args)
            seed.coverage = covSet
            self.population[method.name].append(seed)

        return res, new_lines_covered
    
    def _fuzz_method(self, method: abi.Method):
        seed = self.schedulers[method.name].choose(self.population[method.name])
        mutated = self.mutators[method.name].mutate(seed.data)
        print(f"Calling {method.name} with {mutated}")

        res, new_lines_covered = self._call(method, mutated)

    
    def _fuzz(self, eval: Callable[[str, ContractState], bool], runs: int = 1000):
        for _ in range(runs):
            method = random.choice(self.abi.methods)
            self._fuzz_method(method)
            res = eval(self.owner_acc[1], self.contract_state)

            assert res, "Evaluation failed"

    

    


        
    
    
    