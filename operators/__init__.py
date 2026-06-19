# -*- coding: utf-8 -*-
# Multi-Agent System Operators
# Built on top of AFlow's Operator base class.
# These operators define higher-level multi-agent topologies
# with pre-configured LLM and prompt dependencies injected at construction.

from operators.base import MASOperator
from operators.sequential import Sequential
from operators.star import Star
from operators.shared_memory import SharedMemory
from operators.debate import Debate
from operators.star_with_coordinator import StarWithCoordinator
from operators.debate_with_moderator import DebateWithModerator

__all__ = [
    "MASOperator",
    "Sequential",
    "Star",
    "SharedMemory",
    "Debate",
    "StarWithCoordinator",
    "DebateWithModerator",
]
