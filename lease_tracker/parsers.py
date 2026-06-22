from __future__ import annotations

import html
import json
import re
from datetime import date
from typing import Any, Iterable

from bs4 import BeautifulSoup

from .models import Unit


def parse_units(
    parser_name: str,
    *,
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    if parser_name == "spaces":
        return parse_spaces(building_id, building_name, source_url, source_type, text)
    if parser_name == "amli_next":
        return parse_amli_next(building_id, building_name, source_url, source_type, text)
    if parser_name == "jsonld_floorplans":
        return parse_jsonld_floorplans(building_id, building_name, source_url, source_type, text)
    if parser_name == "reed_html":
        return parse_reed_html(building_id, building_name, source_url, source_type, text)
    return []


def parse_money(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    text = str(value)
    match = re.search(r"\$?\s*([0-9][0-9,]*(?:\.\d+)?)", text)
    if not match:
        return None
    return int(round(float(match.group(1).replace(",", ""))))


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    match = re.search(r"([0-9][0-9,]*)", str(value))
    return int(match.group(1).replace(",", "")) if match else None


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(value))
    return float(match.group(1)) if match else None


def extract_balanced_value(text: str, start: int) -> tuple[str, int] | None:
    while start < len(text) and text[start] not in "[{":
        start += 1
    if start >= len(text):
        return None
    opener = text[start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    quote = ""
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_string = False
            continue
        if ch in {"'", '"'}:
            in_string = True
            quote = ch
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start : i + 1], i + 1
    return None


def json_loads_relaxed(raw: str) -> Any:
    return json.loads(raw)


def token_number(css: Iterable[str], suffix: str) -> float | None:
    for item in css:
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)" + re.escape(suffix), item)
        if match:
            return float(match.group(1))
    return None


def parse_spaces(
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    units: list[Unit] = []
    for match in re.finditer(r"const\s+spacesUnitJSON\s*=", text):
        extracted = extract_balanced_value(text, match.end())
        if not extracted:
            continue
        raw_json, _ = extracted
        try:
            records = json_loads_relaxed(raw_json)
        except Exception:
            continue
        for record in records:
            css = record.get("css") or []
            beds = token_number(css, "bed")
            baths = token_number(css, "bath")
            floor_ids = [item.removeprefix("floor_") for item in css if item.startswith("floor_")]
            lease_terms = record.get("lease_terms") or []
            candidate_terms = [
                term for term in lease_terms if parse_int(term.get("lease_term")) in {10, 11, 12, 13, 14, 15}
            ] or lease_terms
            best_term = None
            best_price = None
            for term in candidate_terms:
                price = parse_money(term.get("price"))
                if price is not None and (best_price is None or price < best_price):
                    best_price = price
                    best_term = str(term.get("lease_term", ""))
            unit_id = str(record.get("id") or "")
            floorplan = f"floor_{floor_ids[0]}" if floor_ids else ""
            notes = "Spaces/RealPage embedded availability. Rent uses lowest exposed 10-15 month term."
            available = str(record.get("available_on") or "")
            units.append(
                Unit(
                    unit_key=f"{building_id}:spaces:{unit_id}",
                    building_id=building_id,
                    building_name=building_name,
                    unit=unit_id,
                    floorplan=floorplan,
                    beds=beds,
                    baths=baths,
                    base_rent=best_price,
                    estimated_total_rent=best_price,
                    available_date=available,
                    lease_term=best_term or "",
                    fees_notes="Source labels prices as total monthly leasing price when available.",
                    source_url=source_url,
                    source_type=source_type,
                    notes=notes,
                    raw={"source": "spaces", "record": record},
                )
            )
    return units


def walk_json(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_json(item)


def parse_amli_next(
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    soup = BeautifulSoup(text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    payloads: list[Any] = []
    if script and script.string:
        try:
            payloads.append(json.loads(script.string))
        except Exception:
            pass
    if not payloads:
        match = re.search(r'"floorplanName"\s*:', text)
        if not match:
            return []
        # The AMLI page currently exposes usable data in __NEXT_DATA__; if that changes,
        # fail closed rather than scraping arbitrary script fragments.
        return []

    units: list[Unit] = []
    seen = set()
    for payload in payloads:
        for obj in walk_json(payload):
            if not isinstance(obj, dict):
                continue
            if "floorplanName" not in obj or not isinstance(obj.get("units"), list):
                continue
            floorplan = str(obj.get("floorplanName") or "")
            beds = parse_float(obj.get("bedroomMax"))
            baths = parse_float(obj.get("bathroomMax"))
            for raw_unit in obj.get("units") or []:
                if not isinstance(raw_unit, dict):
                    continue
                unit_no = str(raw_unit.get("unitNumber") or raw_unit.get("unitId") or "")
                key = f"{building_id}:amli:{unit_no or raw_unit.get('unitId')}"
                if key in seen:
                    continue
                seen.add(key)
                base_rent = parse_money(raw_unit.get("baseRent") or raw_unit.get("rent"))
                total_rent = parse_money(raw_unit.get("totalRent")) or base_rent
                mandatory = parse_money(raw_unit.get("mandatoryFees"))
                fee_note = f"Mandatory monthly fees exposed: ${mandatory}" if mandatory else ""
                units.append(
                    Unit(
                        unit_key=key,
                        building_id=building_id,
                        building_name=building_name,
                        unit=unit_no,
                        floorplan=floorplan,
                        beds=beds,
                        baths=baths,
                        sqft=parse_int(raw_unit.get("squareFeet") or obj.get("sqftMin")),
                        base_rent=base_rent,
                        estimated_total_rent=total_rent,
                        available_date=str(
                            raw_unit.get("rpAvailableDate")
                            or raw_unit.get("realPageAvailabilityDate")
                            or ""
                        )[:10],
                        fees_notes=fee_note,
                        source_url=source_url,
                        source_type=source_type,
                        notes="AMLI embedded Next data; total rent used when exposed.",
                        raw={"source": "amli_next", "floorplan": floorplan, "record": raw_unit},
                    )
                )
    return units


def all_jsonld_objects(text: str) -> list[Any]:
    soup = BeautifulSoup(text, "html.parser")
    out: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        raw = html.unescape(raw).strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def iter_floorplans_from_jsonld(payload: Any) -> Iterable[dict[str, Any]]:
    for obj in walk_json(payload):
        if not isinstance(obj, dict):
            continue
        types = obj.get("@type")
        if isinstance(types, list):
            is_floorplan = "FloorPlan" in types
        else:
            is_floorplan = types == "FloorPlan"
        if is_floorplan:
            yield obj


def parse_jsonld_floorplans(
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    units: list[Unit] = []
    seen = set()
    for payload in all_jsonld_objects(text):
        for plan in iter_floorplans_from_jsonld(payload):
            name = str(plan.get("name") or plan.get("@id") or "floorplan")
            beds = parse_float(plan.get("numberOfBedrooms") or plan.get("numberOfRooms"))
            baths = parse_float(plan.get("numberOfBathroomsTotal") or plan.get("numberOfFullBathrooms"))
            floor_size = plan.get("floorSize") or {}
            if isinstance(floor_size, dict):
                sqft_value = floor_size.get("value") or floor_size.get("minValue") or floor_size.get("maxValue")
            else:
                sqft_value = floor_size
            sqft = parse_int(sqft_value)
            offers = plan.get("offers")
            if isinstance(offers, list):
                offer_items = offers
            elif isinstance(offers, dict):
                offer_items = [offers]
            else:
                offer_items = [{}]
            available_count = parse_int(plan.get("numberOfAvailableAccommodationUnits"))
            if available_count == 0 and not offers:
                continue
            for idx, offer in enumerate(offer_items):
                price = parse_money(offer.get("price") if isinstance(offer, dict) else None)
                availability = str(offer.get("availability") if isinstance(offer, dict) else "")
                if availability and "OutOfStock" in availability:
                    continue
                if not price and (available_count is None or available_count <= 0):
                    continue
                key = f"{building_id}:jsonld:{name}:{idx}:{price or available_count or 'available'}"
                if key in seen:
                    continue
                seen.add(key)
                status = "available"
                if available_count is not None:
                    status = f"available_count:{available_count}"
                units.append(
                    Unit(
                        unit_key=key,
                        building_id=building_id,
                        building_name=building_name,
                        unit=f"floorplan-{name}",
                        floorplan=name,
                        beds=beds,
                        baths=baths,
                        sqft=sqft,
                        base_rent=price,
                        estimated_total_rent=price,
                        source_url=(offer.get("url") if isinstance(offer, dict) else None) or plan.get("url") or source_url,
                        source_type=source_type,
                        status=status,
                        notes="JSON-LD floorplan-level availability; may not expose unit number/date.",
                        raw={"source": "jsonld_floorplans", "record": plan},
                    )
                )
    return units


def infer_year_for_month_day(month_name: str, day_text: str) -> str:
    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    today = date.today()
    month = months.get(month_name[:3].lower())
    day = parse_int(day_text)
    if not month or not day:
        return f"{month_name} {day_text}".strip()
    year = today.year
    candidate = date(year, month, day)
    if candidate < today:
        candidate = date(year + 1, month, day)
    return candidate.isoformat()


def parse_reed_html(
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    soup = BeautifulSoup(text, "html.parser")
    units: list[Unit] = []
    for modal in soup.select(".availability-mdl"):
        floorplan = modal.get("data-type") or ""
        header_text = modal.get_text(" ", strip=True)
        bed_match = re.search(r"(\d+(?:\.\d+)?)\s*Bed", header_text, re.I)
        bath_match = re.search(r"(\d+(?:\.\d+)?)\s*Bath", header_text, re.I)
        beds = parse_float(bed_match.group(1)) if bed_match else None
        baths = parse_float(bath_match.group(1)) if bath_match else None
        for row in modal.select("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if len(cells) < 6 or cells[0].lower() == "unit":
                continue
            unit_no = cells[0]
            rent = parse_money(cells[1])
            sqft = parse_int(cells[2])
            available_raw = cells[5].replace("Available", "").strip()
            date_match = re.search(r"([A-Za-z]{3,})\s+(\d{1,2})", available_raw)
            available = (
                infer_year_for_month_day(date_match.group(1), date_match.group(2))
                if date_match
                else available_raw
            )
            if not unit_no or not rent:
                continue
            units.append(
                Unit(
                    unit_key=f"{building_id}:reed:{unit_no}",
                    building_id=building_id,
                    building_name=building_name,
                    unit=unit_no,
                    floorplan=floorplan,
                    beds=beds,
                    baths=baths,
                    sqft=sqft,
                    base_rent=rent,
                    estimated_total_rent=rent,
                    available_date=available,
                    source_url=source_url,
                    source_type=source_type,
                    notes="The Reed HTML availability table.",
                    raw={"source": "reed_html", "cells": cells},
                )
            )
    return units
