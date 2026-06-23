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
    if parser_name == "sightmap":
        return parse_sightmap(building_id, building_name, source_url, source_type, text)
    if parser_name == "rentcafe_ysi":
        return parse_rentcafe_ysi(building_id, building_name, source_url, source_type, text)
    if parser_name == "knock_doorway":
        return parse_knock_doorway(building_id, building_name, source_url, source_type, text)
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


def clean_display_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    return re.sub(r"\s+", " ", BeautifulSoup(html.unescape(str(value)), "html.parser").get_text(" ", strip=True))


def first_money(*values: Any) -> int | None:
    for value in values:
        money = parse_money_min(value)
        if money is not None:
            return money
    return None


def parse_money_min(value: Any) -> int | None:
    if isinstance(value, (list, tuple)):
        parsed = [parse_money_min(item) for item in value]
        parsed = [item for item in parsed if item is not None]
        return min(parsed) if parsed else None
    return parse_money(value)


def normalize_date_value(value: Any) -> str:
    if value is None or value == "":
        return ""
    text = str(value)
    match = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else text


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def iter_scrapling_captured_xhr(text: str) -> Iterable[tuple[str, str]]:
    marker = re.compile(r"<!-- scrapling captured_xhr: (.*?) -->\n", re.S)
    matches = list(marker.finditer(text))
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        yield match.group(1).strip(), text[match.end() : end].strip()


def iter_scrapling_captured_json(text: str, url_pattern: str | None = None) -> Iterable[tuple[str, Any]]:
    pattern = re.compile(url_pattern, re.I) if url_pattern else None
    for url, body in iter_scrapling_captured_xhr(text):
        if pattern and not pattern.search(url):
            continue
        try:
            yield url, json.loads(body)
        except Exception:
            continue


def extract_js_assignment(text: str, name: str) -> Any | None:
    for match in re.finditer(re.escape(name) + r"\s*=", text):
        extracted = extract_balanced_value(text, match.end())
        if not extracted:
            continue
        raw_json, _ = extracted
        try:
            return json_loads_relaxed(raw_json)
        except Exception:
            continue
    return None


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


def sightmap_floorplan_name(plan: dict[str, Any]) -> str:
    for value in (plan.get("filter_label"), plan.get("name"), plan.get("id")):
        if value is None or value == "":
            continue
        text = str(value)
        if text.startswith("{"):
            try:
                decoded = json.loads(text)
                if decoded.get("name"):
                    return str(decoded["name"])
            except Exception:
                pass
        return text
    return ""


def parse_sightmap(
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    units: list[Unit] = []
    seen = set()
    for url, payload in iter_scrapling_captured_json(text, r"sightmap\.com/.*/api/"):
        if not isinstance(payload, dict):
            continue
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("units"), list):
            continue
        floorplans = {
            str(plan.get("id")): plan
            for plan in data.get("floor_plans") or []
            if isinstance(plan, dict) and plan.get("id") is not None
        }
        for raw_unit in data.get("units") or []:
            if not isinstance(raw_unit, dict):
                continue
            unit_id = str(raw_unit.get("id") or "")
            unit_no = str(raw_unit.get("unit_number") or raw_unit.get("label") or unit_id)
            key = f"{building_id}:sightmap:{unit_id or unit_no}"
            if key in seen:
                continue
            seen.add(key)
            plan = floorplans.get(str(raw_unit.get("floor_plan_id")), {})
            base_rent = first_money(raw_unit.get("price"), raw_unit.get("display_price"))
            total_rent = first_money(
                raw_unit.get("total_price"),
                raw_unit.get("total_display_price"),
                raw_unit.get("display_full_price"),
                raw_unit.get("total_display_full_price"),
                raw_unit.get("price"),
                raw_unit.get("display_price"),
            )
            fee_note = ""
            total_display = clean_display_text(raw_unit.get("total_display_price"))
            if total_display and total_rent and total_rent != base_rent:
                fee_note = f"Source total rent display: {total_display}."
            units.append(
                Unit(
                    unit_key=key,
                    building_id=building_id,
                    building_name=building_name,
                    unit=unit_no,
                    floorplan=sightmap_floorplan_name(plan),
                    beds=parse_float(plan.get("bedroom_count")),
                    baths=parse_float(plan.get("bathroom_count")),
                    sqft=parse_int(raw_unit.get("area")),
                    base_rent=base_rent,
                    estimated_total_rent=total_rent or base_rent,
                    available_date=normalize_date_value(raw_unit.get("available_on")),
                    lease_term=str(raw_unit.get("display_lease_term") or ""),
                    concessions=clean_display_text(raw_unit.get("specials_description")),
                    fees_notes=fee_note,
                    source_url=source_url,
                    source_type=source_type,
                    notes="SightMap captured availability API via Scrapling.",
                    raw={"source": "sightmap", "api_url": url, "record": raw_unit, "floorplan": plan},
                )
            )
    return units


def parse_rentcafe_ysi(
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    raw_floorplans = extract_js_assignment(text, "ysi.floorplansList") or []
    raw_units = extract_js_assignment(text, "ysi.unitsList") or []
    floorplans = {
        str(plan.get("Id")): plan
        for plan in raw_floorplans
        if isinstance(plan, dict) and plan.get("Id") is not None
    }
    units: list[Unit] = []
    seen = set()

    for raw_unit in raw_units:
        if not isinstance(raw_unit, dict) or is_truthy(raw_unit.get("isCommercial")):
            continue
        unit_id = str(raw_unit.get("Id") or "")
        unit_no = str(raw_unit.get("UnitCode") or unit_id)
        key = f"{building_id}:rentcafe:{unit_id or unit_no}"
        if key in seen:
            continue
        seen.add(key)
        plan = floorplans.get(str(raw_unit.get("FloorplanId")), {})
        base_rent = first_money(raw_unit.get("MinRent"), raw_unit.get("Rentmin"))
        concessions = "Specials marked by source." if is_truthy(raw_unit.get("HasSpecials")) else ""
        units.append(
            Unit(
                unit_key=key,
                building_id=building_id,
                building_name=building_name,
                unit=unit_no,
                floorplan=str(raw_unit.get("FloorplanName") or raw_unit.get("FloorplanId") or ""),
                beds=parse_float(raw_unit.get("Beds") or plan.get("Beds")),
                baths=parse_float(raw_unit.get("Baths") or plan.get("Baths")),
                sqft=parse_int(raw_unit.get("SqFt") or plan.get("MinSqFt") or plan.get("MaxSqFt")),
                base_rent=base_rent,
                estimated_total_rent=base_rent,
                available_date=normalize_date_value(raw_unit.get("AvailableDate")),
                concessions=concessions,
                fees_notes="RentCafe/Yardi min rent used.",
                source_url=source_url,
                source_type=source_type,
                notes="RentCafe/Yardi embedded ysi.unitsList availability.",
                raw={"source": "rentcafe_ysi", "record": raw_unit, "floorplan": plan},
            )
        )

    if units:
        return units

    for plan in raw_floorplans:
        if not isinstance(plan, dict) or is_truthy(plan.get("isCommercial")):
            continue
        available_count = parse_int(plan.get("AvailableCount"))
        if not available_count:
            continue
        plan_id = str(plan.get("Id") or "")
        key = f"{building_id}:rentcafe_floorplan:{plan_id}"
        base_rent = first_money(plan.get("MinRent"), plan.get("Rentmin"))
        units.append(
            Unit(
                unit_key=key,
                building_id=building_id,
                building_name=building_name,
                unit=f"floorplan-{plan_id}",
                floorplan=plan_id,
                beds=parse_float(plan.get("Beds")),
                baths=parse_float(plan.get("Baths")),
                sqft=parse_int(plan.get("MinSqFt") or plan.get("MaxSqFt")),
                base_rent=base_rent,
                estimated_total_rent=base_rent,
                available_date=normalize_date_value(plan.get("AvailableDate")),
                concessions="Specials marked by source." if is_truthy(plan.get("HasSpecials")) else "",
                fees_notes="RentCafe/Yardi floorplan-level min rent used.",
                source_url=source_url,
                source_type=source_type,
                status=f"available_count:{available_count}",
                notes="RentCafe/Yardi embedded ysi.floorplansList availability; unit rows were unavailable.",
                raw={"source": "rentcafe_ysi_floorplan", "record": plan},
            )
        )
    return units


def parse_knock_doorway(
    building_id: str,
    building_name: str,
    source_url: str,
    source_type: str,
    text: str,
) -> list[Unit]:
    units: list[Unit] = []
    seen = set()
    payloads: list[tuple[str, Any]] = []
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            payloads.append((source_url, payload))
    except Exception:
        pass
    payloads.extend(iter_scrapling_captured_json(text, r"(doorway-api|knockrentals)"))
    for url, payload in payloads:
        if not isinstance(payload, dict):
            continue
        units_data = payload.get("units_data")
        if not isinstance(units_data, dict) or not isinstance(units_data.get("units"), list):
            continue
        layouts = {
            str(layout.get("id")): layout
            for layout in units_data.get("layouts") or []
            if isinstance(layout, dict) and layout.get("id") is not None
        }
        for raw_unit in units_data.get("units") or []:
            if not isinstance(raw_unit, dict):
                continue
            if not is_truthy(raw_unit.get("available")):
                continue
            if is_truthy(raw_unit.get("hidden")) or is_truthy(raw_unit.get("leased")) or raw_unit.get("deletedAt"):
                continue
            unit_id = str(raw_unit.get("id") or "")
            unit_no = str(raw_unit.get("name") or unit_id)
            key = f"{building_id}:knock:{unit_id or unit_no}"
            if key in seen:
                continue
            seen.add(key)
            layout = layouts.get(str(raw_unit.get("layoutId")), {})
            base_rent = first_money(raw_unit.get("knockPrice"), raw_unit.get("price"), raw_unit.get("displayPrice"))
            units.append(
                Unit(
                    unit_key=key,
                    building_id=building_id,
                    building_name=building_name,
                    unit=unit_no,
                    floorplan=str(raw_unit.get("layoutName") or layout.get("name") or ""),
                    beds=parse_float(raw_unit.get("bedrooms") or layout.get("bedrooms")),
                    baths=parse_float(raw_unit.get("bathrooms") or layout.get("bathrooms")),
                    sqft=parse_int(raw_unit.get("area") or layout.get("area")),
                    base_rent=base_rent,
                    estimated_total_rent=base_rent,
                    available_date=normalize_date_value(raw_unit.get("availableOn")),
                    source_url=source_url,
                    source_type=source_type,
                    status="reserved" if is_truthy(raw_unit.get("reserved")) else "available",
                    notes="Knock Doorway captured units API via Scrapling.",
                    raw={"source": "knock_doorway", "api_url": url, "record": raw_unit, "layout": layout},
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
