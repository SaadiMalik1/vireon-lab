"""
Training-Time Data Poisoning Simulator.

Simulates adversarial data poisoning attacks against BCI decoders during
the training phase. This module supports Label Flipping (untargeted/targeted)
and Clean-Label Backdoor insertion (trigger injection without label change).
"""

import numpy as np
import random
from typing import List, Tuple, Optional

class DataPoisoner:
    """Base class for data poisoning techniques."""
    def poison(self, x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError()


class LabelFlippingPoisoner(DataPoisoner):
    """
    Flips the labels of a percentage of the training data.
    If target_class is specified, it flips labels TO that target class.
    If target_class is None, it randomly flips labels to any other class.
    """
    def __init__(self, poison_ratio: float = 0.1, target_class: Optional[int] = None, num_classes: int = 2):
        self.poison_ratio = poison_ratio
        self.target_class = target_class
        self.num_classes = num_classes

    def poison(self, x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if x.size == 0:
            return x, y
            
        n_samples = len(y)
        n_poison = int(n_samples * self.poison_ratio)
        
        # Select random indices to poison
        indices = np.random.choice(n_samples, n_poison, replace=False)
        
        y_poisoned = y.copy()
        
        for idx in indices:
            if self.target_class is not None:
                y_poisoned[idx] = self.target_class
            else:
                # Random flip
                candidates = [c for c in range(self.num_classes) if c != y[idx]]
                if candidates:
                    y_poisoned[idx] = random.choice(candidates)
                    
        return x, y_poisoned


class CleanLabelBackdoorPoisoner(DataPoisoner):
    """
    Inserts a high-frequency trigger into a percentage of the training data
    belonging to a specific target class. The label is not changed, causing
    the model to associate the trigger with the target class.
    """
    def __init__(self, poison_ratio: float = 0.1, target_class: int = 1, 
                 trigger_freq_hz: float = 60.0, trigger_amplitude: float = 100.0,
                 sample_rate: int = 250):
        self.poison_ratio = poison_ratio
        self.target_class = target_class
        self.trigger_freq_hz = trigger_freq_hz
        self.trigger_amplitude = trigger_amplitude
        self.sample_rate = sample_rate

    def poison(self, x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if x.size == 0:
            return x, y
            
        x_poisoned = x.copy()
        
        # Find indices of the target class
        target_indices = np.where(y == self.target_class)[0]
        if len(target_indices) == 0:
            return x_poisoned, y
            
        n_poison = int(len(target_indices) * self.poison_ratio)
        if n_poison == 0:
            return x_poisoned, y
            
        # Select target samples to insert backdoor
        indices = np.random.choice(target_indices, n_poison, replace=False)
        
        n_channels = x.shape[1]
        n_points = x.shape[2]
        
        t = np.arange(n_points) / float(self.sample_rate)
        trigger_signal = self.trigger_amplitude * np.sin(2 * np.pi * self.trigger_freq_hz * t)
        
        for idx in indices:
            # Add trigger to all channels (or could be specific channels)
            for ch in range(n_channels):
                x_poisoned[idx, ch, :] += trigger_signal
                
        return x_poisoned, y
