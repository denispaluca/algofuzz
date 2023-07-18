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

        self.coverage: Set[int] = set()
        self.transition: tuple[dict,dict] = None
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


def get_transition_id(transition: tuple[dict, dict]) -> str:
    pickled = json.dumps(transition, sort_keys=True).encode()
    return hashlib.md5(pickled).hexdigest()

class PowerSchedule:
    def __init__(self, exponent: int = 5, trans_coef = 0.5) -> None:
        self.path_frequency: Dict = {}
        self.transition_frequency: Dict = {}
        self.exponent = exponent
        self.trans_coef = trans_coef

    def assignEnergy(self, population: Sequence[Seed]) -> None:
        for seed in population:
            transition_id, path_id = None, None
            if seed.transition is not None:
                transition_id = get_transition_id(seed.transition)
                if transition_id not in self.transition_frequency:
                    self.transition_frequency[transition_id] = 1

            if seed.coverage is not None:
                path_id = getPathID(seed.coverage)
                if path_id not in self.path_frequency:
                    self.path_frequency[path_id] = 1
            
            

            trans_freq = self.transition_frequency.get(transition_id, 0)
            path_freq = self.path_frequency.get(path_id, 0)
            weighted_freqs = self.trans_coef * trans_freq + (1 - self.trans_coef) * path_freq
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
    
    def addTransition(self, transition: tuple[dict, dict] | None) -> bool:
        if transition is None:
            return False
        
        transition_id = get_transition_id(transition)
        if transition_id not in self.transition_frequency:
            self.transition_frequency[transition_id] = 1
            return True
        
        self.transition_frequency[transition_id] += 1
        return False
    
    def addPath(self, path: Set[int] | None) -> bool:
        if path is None:
            return False
        
        path_id = getPathID(path)
        if path_id not in self.path_frequency:
            self.path_frequency[path_id] = 1
            return True
        
        self.path_frequency[path_id] += 1
        return False