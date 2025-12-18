import re
from typing import Callable, List, Optional, Protocol, Sequence, Tuple


class CandidateLike(Protocol):
    names_by_house: Tuple[str, ...]
    colors_by_house: Tuple[str, ...]
    pets_by_house: Tuple[str, ...]


Constraint = Callable[[CandidateLike], bool]


def norm_text(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    if s.endswith("."):
        s = s[:-1]
    return s


def parse_list_line(line: str, key: str) -> Optional[List[str]]:
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\.?$", line.strip(), flags=re.IGNORECASE)
    if not m:
        return None
    return [x.strip().lower() for x in m.group(1).split(",") if x.strip()]


def extract_clues(puzzle_text: str) -> List[str]:
    in_clues = False
    clues: List[str] = []
    for raw_line in puzzle_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("clues:"):
            in_clues = True
            continue
        if not in_clues:
            continue
        m = re.match(r"^\d+\.\s*(.+)$", line)
        if not m:
            continue
        clues.append(norm_text(m.group(1)))
    return clues


def extract_names_from_clues(clues: Sequence[str]) -> List[str]:
    names: List[str] = []
    for clue in clues:
        m = re.match(r"^(?P<name>[A-Z][a-z]+)\b", clue)
        if m:
            n = m.group("name")
            if n not in ("The", "House") and n not in names:
                names.append(n)
    return names


def build_constraints(clues: Sequence[str], colors: Sequence[str], pets: Sequence[str]) -> Tuple[List[Constraint], List[str]]:
    colors_set = set(colors)
    pets_set = set(pets)

    constraints: List[Constraint] = []
    unknown: List[str] = []

    def add(fn: Constraint) -> None:
        constraints.append(fn)

    for raw in clues:
        c = raw

        m = re.match(r"^(?P<name>[A-Z][a-z]+) lives in house (?P<house>\d+)$", c)
        if m:
            name = m.group("name")
            house = int(m.group("house"))

            def _fn(candidate: CandidateLike, name=name, house=house) -> bool:
                return candidate.names_by_house[house - 1] == name

            add(_fn)
            continue

        m = re.match(r"^(?P<name>[A-Z][a-z]+) lives in the (?P<color>[a-z]+) house$", c)
        if m:
            name = m.group("name")
            color = m.group("color").lower()
            if color not in colors_set:
                unknown.append(raw)
                continue

            def _fn(candidate: CandidateLike, name=name, color=color) -> bool:
                return candidate.names_by_house[candidate.colors_by_house.index(color)] == name

            add(_fn)
            continue

        m = re.match(r"^House (?P<house>\d+) is painted (?P<color>[a-z]+)$", c)
        if m:
            house = int(m.group("house"))
            color = m.group("color").lower()
            if color not in colors_set:
                unknown.append(raw)
                continue

            def _fn(candidate: CandidateLike, house=house, color=color) -> bool:
                return candidate.colors_by_house[house - 1] == color

            add(_fn)
            continue

        m = re.match(r"^The (?P<left>[a-z]+) house is immediately to the left of the (?P<right>[a-z]+) house$", c)
        if m:
            left = m.group("left").lower()
            right = m.group("right").lower()
            if left not in colors_set or right not in colors_set:
                unknown.append(raw)
                continue

            def _fn(candidate: CandidateLike, left=left, right=right) -> bool:
                return candidate.colors_by_house.index(left) + 1 == candidate.colors_by_house.index(right)

            add(_fn)
            continue

        m = re.match(r"^The (?P<color>[a-z]+) house contains the (?P<pet>[a-z]+)$", c)
        if m:
            color = m.group("color").lower()
            pet = m.group("pet").lower()
            if color not in colors_set or pet not in pets_set:
                unknown.append(raw)
                continue

            def _fn(candidate: CandidateLike, color=color, pet=pet) -> bool:
                idx = candidate.colors_by_house.index(color)
                return candidate.pets_by_house[idx] == pet

            add(_fn)
            continue

        m = re.match(r"^The person in house (?P<house>\d+) owns the (?P<pet>[a-z]+)$", c)
        if m:
            house = int(m.group("house"))
            pet = m.group("pet").lower()
            if pet not in pets_set:
                unknown.append(raw)
                continue

            def _fn(candidate: CandidateLike, house=house, pet=pet) -> bool:
                return candidate.pets_by_house[house - 1] == pet

            add(_fn)
            continue

        m = re.match(r"^(?P<name>[A-Z][a-z]+) owns the (?P<pet>[a-z]+)$", c)
        if m:
            name = m.group("name")
            pet = m.group("pet").lower()
            if pet not in pets_set:
                unknown.append(raw)
                continue

            def _fn(candidate: CandidateLike, name=name, pet=pet) -> bool:
                idx = candidate.names_by_house.index(name)
                return candidate.pets_by_house[idx] == pet

            add(_fn)
            continue

        m = re.match(r"^(?P<name>[A-Z][a-z]+) does not live in the (?P<color>[a-z]+) house$", c)
        if m:
            name = m.group("name")
            color = m.group("color").lower()
            if color not in colors_set:
                unknown.append(raw)
                continue

            def _fn(candidate: CandidateLike, name=name, color=color) -> bool:
                return candidate.names_by_house.index(name) != candidate.colors_by_house.index(color)

            add(_fn)
            continue

        unknown.append(raw)

    return constraints, unknown
