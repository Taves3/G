from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from .datatypes import Type

class ReturnSignal(Exception):
    def __init__(self, value: Type):
        self.value = value