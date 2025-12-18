from pathlib import Path

from solver import solve_csv


def main() -> int:
    base = Path(__file__).resolve().parent
    input_path = base / "Test_100_Puzzles.csv"
    output_path = base / "results.csv"

    solve_csv(input_path, output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
