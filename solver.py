import csv
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from parser import build_constraints, extract_clues, extract_names_from_clues, parse_list_line


@dataclass(frozen=True)
class Candidate:
    size: int
    names_by_house: Tuple[str, ...]
    colors_by_house: Tuple[str, ...]
    pets_by_house: Tuple[str, ...]

    def to_grid_json(self) -> Dict[str, object]:
        return {
            "header": ["House", "Name", "Color", "Pet"],
            "rows": [
                [str(i), self.names_by_house[i - 1], self.colors_by_house[i - 1], self.pets_by_house[i - 1]]
                for i in range(1, self.size + 1)
            ],
        }


Constraint = Callable[[Candidate], bool]


def generate_candidates(size: int, names: Sequence[str], colors: Sequence[str], pets: Sequence[str]) -> List[Candidate]:
    return [
        Candidate(size=size, names_by_house=tuple(nm), colors_by_house=tuple(cl), pets_by_house=tuple(pt))
        for nm in permutations(names, size)
        for cl in permutations(colors, size)
        for pt in permutations(pets, size)
    ]


def _bit_count(x: int) -> int:
    return x.bit_count()


def _lsb_index(x: int) -> int:
    #x should always be non_zero
    return (x & -x).bit_length() - 1


def solve_min_steps(candidates: List[Candidate]) -> Tuple[Optional[Candidate], Optional[int]]:
    if not candidates:
        return None, None

    n = len(candidates)
    full_mask = (1 << n) - 1

    #var keys: kind, house_index
    kinds = ("Name", "Color", "Pet")
    size = candidates[0].size

    values_by_kind: Dict[str, List[str]] = {
        "Name": sorted({v for c in candidates for v in c.names_by_house}),
        "Color": sorted({v for c in candidates for v in c.colors_by_house}),
        "Pet": sorted({v for c in candidates for v in c.pets_by_house}),
    }

    var_value_mask: Dict[Tuple[str, int, str], int] = {}
    for kind in kinds:
        for house in range(1, size + 1):
            for value in values_by_kind[kind]:
                var_value_mask[(kind, house, value)] = 0

    for idx, cand in enumerate(candidates):
        bit = 1 << idx
        for house in range(1, size + 1):
            var_value_mask[("Name", house, cand.names_by_house[house - 1])] |= bit
            var_value_mask[("Color", house, cand.colors_by_house[house - 1])] |= bit
            var_value_mask[("Pet", house, cand.pets_by_house[house - 1])] |= bit

    vars_all: List[Tuple[str, int]] = [(k, h) for k in kinds for h in range(1, size + 1)]

    def domain_values(mask: int, var: Tuple[str, int]) -> List[str]:
        kind, house = var
        vals: List[str] = []
        for value in values_by_kind[kind]:
            if mask & var_value_mask[(kind, house, value)]:
                vals.append(value)
        return vals

    @lru_cache(maxsize=None)
    def search(mask: int) -> Tuple[int, int]:
        # returns will be min_steps and candidate_index
        if mask == 0:
            return 10**9, -1
        if mask & (mask - 1) == 0:
            return 0, _lsb_index(mask)

        #pick up the variable with the smallest domain that is less than 1
        best_var: Optional[Tuple[str, int]] = None
        best_dom: Optional[List[str]] = None
        best_size = 10**9
        for var in vars_all:
            dom = domain_values(mask, var)
            if len(dom) <= 1:
                continue
            if len(dom) < best_size:
                best_size = len(dom)
                best_var = var
                best_dom = dom
                if best_size == 2:
                    break

        if best_var is None or best_dom is None:
            #Multiple candidates but there isnt multi-valued variable- this thing should not happen
            return 10**9, -1

        kind, house = best_var
        best_steps = 10**9
        best_idx = -1
        # Try values in the sorted order
        for value in best_dom:
            child_mask = mask & var_value_mask[(kind, house, value)]
            steps_child, idx_child = search(child_mask)
            if idx_child == -1:
                continue
            total = 1 + steps_child
            if total < best_steps:
                best_steps = total
                best_idx = idx_child
                if best_steps == 1:
                    # cant do better than 1 from Multi_solution state
                    pass

        return best_steps, best_idx

    steps, idx = search(full_mask)
    if idx == -1 or steps >= 10**9:
        return None, None
    return candidates[idx], steps


def solve_puzzle_text(puzzle_text: str, size_raw: str) -> Dict[str, object]:
    m = re.match(r"^(\d+)\*(\d+)$", size_raw.strip())
    if not m or m.group(1) != m.group(2):
        return {"status": "error", "error": f"Unsupported size: {size_raw}"}

    size = int(m.group(1))
    if size != 3:
        return {"status": "error", "error": f"Only 3*3 supported right now; got {size_raw}"}

    colors: Optional[List[str]] = None
    pets: Optional[List[str]] = None
    for line in puzzle_text.splitlines():
        if colors is None:
            colors = parse_list_line(line, "Colors")
        if pets is None:
            pets = parse_list_line(line, "Pets")

    if not colors or not pets:
        return {"status": "error", "error": "Missing Colors/Pets lists"}

    clues = extract_clues(puzzle_text)
    names = extract_names_from_clues(clues)
    issues: List[str] = []

    if len(names) < size:
        for i in range(size - len(names)):
            names.append(f"Unknown{i + 1}")
        issues.append("incomplete_people")
    elif len(names) > size:
        issues.append("too_many_people")
        names = names[:size]

    constraints, unknown_clues = build_constraints(clues, colors, pets)
    if unknown_clues:
        issues.append(f"unparsed_clues:{len(unknown_clues)}")

    all_candidates = generate_candidates(size=size, names=names, colors=colors, pets=pets)

    # Forward checking and constraint propagation... 
    forward_check_steps = 0
    feasible = all_candidates
    for con in constraints:
        before = len(feasible)
        feasible = [c for c in feasible if con(c)]
        after = len(feasible)
        if after < before:
            forward_check_steps += 1

    solution, decision_steps = solve_min_steps(feasible)
    if solution is None:
        return {"status": "unsatisfiable", "issues": issues, "grid_solution": None, "steps": None}

    steps = forward_check_steps + (decision_steps if decision_steps is not None else 0)

    return {
        "status": "ok",
        "issues": issues,
        "grid_solution": solution.to_grid_json(),
        "steps": steps,
        "forward_check_steps": forward_check_steps,
        "decision_steps": decision_steps,
        "num_solutions": len(feasible),
    }


def solve_csv(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows_in = list(reader)

    out_rows: List[Dict[str, str]] = []
    for row in rows_in:
        puzzle_id = (row.get("use thisid") or "").strip()
        size_raw = (row.get("size") or "").strip()
        puzzle_text = row.get("puzzle") or ""

        result = solve_puzzle_text(puzzle_text, size_raw)
        if result.get("status") != "ok":
            out_rows.append(
                {
                    "id": puzzle_id,
                    "grid_solution": "",
                    "steps": "",
                }
            )
            continue

        out_rows.append(
            {
                "id": puzzle_id,
                "grid_solution": json.dumps(result["grid_solution"], ensure_ascii=False),
                "steps": str(result["steps"]),
            }
        )

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "grid_solution", "steps"])
        writer.writeheader()
        writer.writerows(out_rows)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    solve_csv(base / "Test_100_Puzzles.csv", base / "results.csv")
