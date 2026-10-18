from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    name: str
    qty: int
    price: float

    @property
    def value(self) -> float:
        return self.qty * self.price
