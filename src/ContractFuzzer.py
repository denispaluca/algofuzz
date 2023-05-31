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


class MethodFuzzer:
    def __init__(self, method: abi.Method):
        self.method = method
        self.mutator = MethodMutator(method)
        self.seeds = [self.mutator.seed()]
        self.seed_index = 0
        self.population = []
        self.inputs = []
        self.schedule = PowerSchedule()
        
    def create_candidate(self):
        """Returns an input generated by fuzzing a seed in the population"""
        seed = self.schedule.choose(self.population)

        # Stacking: Apply multiple mutations to generate the candidate
        candidate = seed.data
        trials = min(len(candidate), 1 << random.randint(1, 5))
        for i in range(trials):
            candidate = self.mutator.mutate(candidate)
        return candidate
    
    def update(self, coverage: set[int], new_lines_covered: set[int]) -> None:
        self.schedule.addPath(coverage)

        if len(new_lines_covered) > 0:
            seed = Seed(self.inp)
            seed.coverage = coverage
            self.population.append(seed)

    def fuzz(self):
        if self.seed_index < len(self.seeds):
            # Still seeding
            self.inp = self.seeds[self.seed_index]
            self.seed_index += 1
        else:
            # Mutating
            self.inp = self.create_candidate()

        self.inputs.append(self.inp)
        return self.inp

class ContractFuzzer:
    def __init__(self, approval_path: Path, clear_path: Path, abi_path: Path, schema: tuple[int,int,int,int]):
        self.approval_path = approval_path
        self.clear_path = clear_path
        self.schema = schema
        self.abi = abi.Contract.from_json(abi_path.open().read())

        self.method_fuzzers = {method.name: MethodFuzzer(method) for method in self.abi.methods}
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
    
    def _fuzz_method(self, method: abi.Method):
        method_fuzzer = self.method_fuzzers[method.name]
        input = method_fuzzer.fuzz()
        print(f"Calling {method.name} with {input}")

        res, cov = call(method, self.owner_acc, self.app_id, input)
        new_lines_covered = self.coverage.update(cov)
        method_fuzzer.update(cov, new_lines_covered)
            
    def _fuzz(self, eval: Callable[[str, ContractState], bool], runs: int = 1000):
        for _ in range(runs):
            method = random.choice(self.abi.methods)
            self._fuzz_method(method)
            self.contract_state.load(self.owner_acc[1])
            res = eval(self.owner_acc[1], self.contract_state)

            assert res, "Evaluation failed"

    

    


        
    
    
    