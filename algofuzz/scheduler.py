import pickle
import random
import hashlib
import json
from typing import Set, Union, Sequence, Dict, List


class Seed:
    """Represent an input with additional attributes"""

    def __init__(self, data) -> None:
        """Initialize from seed data"""
        self.data = data

        self.path_id: str = None
        self.state_id: str = None
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


def get_state_id(state: dict) -> str:
    pickled = json.dumps(state, sort_keys=True).encode()
    return hashlib.md5(pickled).hexdigest()

class PowerSchedule:
    def __init__(self, exponent: int = 5, state_coef = 0.5) -> None:
        self.path_frequency: Dict = {}
        self.state_frequency: Dict = {}
        self.exponent = exponent
        self.state_coef = state_coef
        self.cov_coef = 1 - state_coef

    def assignEnergy(self, population: Sequence[Seed]) -> None:
        for seed in population:
            state_freq = self.state_frequency[seed.state_id]
            path_freq = self.path_frequency[seed.path_id]

            weighted_freqs = self.state_coef * state_freq + self.cov_coef * path_freq
            seed.energy = 1 / (weighted_freqs ** self.exponent)

    def normalizedEnergy(self, population: Sequence[Seed]) -> List[float]:
        energy = list(map(lambda seed: seed.energy, population))
        sum_energy = sum(energy)  
        assert sum_energy != 0
        norm_energy = list(map(lambda nrg: nrg / sum_energy, energy))
        return norm_energy

    def choose(self, population: Sequence[Seed]) -> Seed:
        self.assignEnergy(population)
        norm_energy = self.normalizedEnergy(population)
        seed: Seed = random.choices(population, weights=norm_energy)[0]
        return seed
    
    def addState(self, state: dict) -> tuple[bool, str]:
        state_id = get_state_id(state)
        if state_id not in self.state_frequency:
            self.state_frequency[state_id] = 1
            return True, state_id
        
        self.state_frequency[state_id] += 1
        return False, state_id
    
    def addPath(self, path: Set[int]) -> tuple[bool, str]:
        path_id = getPathID(path)
        if path_id not in self.path_frequency:
            self.path_frequency[path_id] = 1
            return True, path_id
        
        self.path_frequency[path_id] += 1
        return False, path_id