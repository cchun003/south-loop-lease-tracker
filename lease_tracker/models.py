from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Unit:
    unit_key: str
    building_id: str
    building_name: str
    unit: str = ""
    floorplan: str = ""
    beds: float | None = None
    baths: float | None = None
    sqft: int | None = None
    base_rent: int | None = None
    estimated_total_rent: int | None = None
    available_date: str = ""
    lease_term: str = ""
    concessions: str = ""
    fees_notes: str = ""
    parking_available: str = "unconfirmed"
    parking_monthly: str = ""
    source_url: str = ""
    source_type: str = ""
    status: str = "available"
    notes: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def rent_for_threshold(self) -> int | None:
        return self.estimated_total_rent if self.estimated_total_rent is not None else self.base_rent

    def is_target_layout(self) -> bool:
        return self.beds == 2 and self.baths is not None and self.baths >= 2


@dataclass
class SourceResult:
    building_id: str
    building_name: str
    source_name: str
    source_type: str
    url: str
    parser: str
    status: str
    units: list[Unit] = field(default_factory=list)
    error: str = ""

