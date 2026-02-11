"""Fault injection system for simulator."""

from .fault_injector import FaultInjector
from .fault_types import (
    BearingWearFault,
    CloggingFault,
    ValveStuckFault,
    SensorDriftFault,
    SensorStuckFault,
    NoiseBurstFault,
)

__all__ = [
    "FaultInjector",
    "BearingWearFault",
    "CloggingFault",
    "ValveStuckFault",
    "SensorDriftFault",
    "SensorStuckFault",
    "NoiseBurstFault",
]
