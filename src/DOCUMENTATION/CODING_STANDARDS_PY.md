# Python Coding Standards & Guidelines

## Overview
This document outlines the coding standards and best practices for all Python scripts in this project. These guidelines mirror the structure of `CODING_STANDARDS_R.md` and ensure consistency across the codebase.

---

## 1. File Organization

### Script Structure
- **Module docstring**: Every `.py` file starts with a triple-quoted docstring describing its purpose, inputs, and outputs
- **Imports**: Grouped in order — stdlib, third-party, local — separated by blank lines
- **Constants**: Defined at module level in `UPPER_SNAKE_CASE` immediately after imports
- **Functions**: Defined before `main()`
- **Entrypoint**: Use `if __name__ == "__main__": main()` to keep scripts importable

**Example:**
```python
"""
Short description of what this script does.

Output columns:
    col_a, col_b, col_c
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

# ── Constants ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "input.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "output.parquet"


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Transform description."""
    ...


def main():
    df = pd.read_csv(DATA_PATH)
    result = transform(df)
    result.to_parquet(OUTPUT_PATH, index=False)


if __name__ == "__main__":
    main()
```

---

## 2. Naming Conventions

### Variables and Functions
- **Style**: `snake_case`
- **Descriptive**: Names should clearly indicate content/purpose
- **Abbreviations**: Acceptable for well-known terms (`df`, `gdf`, `ot`, `pbp`)

### Constants
- **Style**: `UPPER_SNAKE_CASE`
- **Examples**: `REGULATION_SECONDS`, `SNAPSHOT_INTERVAL`, `OUTPUT_PATH`

### Classes (if used)
- **Style**: `PascalCase`

---

## 3. Required Packages & Dependencies

### Core Stack
| Package | Purpose |
|---|---|
| `pandas` | DataFrames, I/O, merges |
| `numpy` | Numeric operations, vectorized math |
| `pathlib` | Cross-platform file paths |
| `pyarrow` | Parquet read/write backend |

### Additional Packages
| Package | Purpose |
|---|---|
| `sportsdataverse` | NBA play-by-play data loading |

### Environment
- All dependencies tracked in `requirements.txt`
- Virtual environment: `nba-cc-env/`
- Activate before running: `source nba-cc-env/bin/activate`

---

## 4. Data I/O

### Reading Data
- Use `usecols` when loading CSVs to limit memory usage
- Prefer `pd.read_parquet()` for intermediate/output datasets
- Use `pathlib.Path` for all file paths (not string concatenation)

```python
df = pd.read_csv(path, usecols=["col_a", "col_b"])
df = pd.read_parquet(path)
```

### Writing Data
- **Prefer Parquet** (`.parquet`) over CSV for intermediate and output data
  - Smaller file size
  - Faster reads
  - Preserves dtypes exactly
- Use `index=False` when writing
- Create output directories with `mkdir(parents=True, exist_ok=True)`

```python
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(OUTPUT_PATH, index=False)
```

### When to Use CSV
- When the file needs to be human-readable or opened in Excel
- When the file is the primary source-of-truth data download

---

## 5. Data Manipulation

### Preferred Patterns
- **Vectorized operations** over loops wherever possible (`np.where`, pandas vectorized methods)
- **`groupby` + `transform`** for per-group derived columns
- **`merge_asof`** for time-aligned joins
- **Method chaining** for short pipelines; named intermediate variables for complex multi-step logic

### Example: Vectorized Conditional
```python
# Prefer this
df["label"] = np.where(df["value"] > threshold, "high", "low")

# Over this
df["label"] = df["value"].apply(lambda x: "high" if x > threshold else "low")
```

### Forward Fill / Missing Values
- Use `.ffill()` for time-series forward fill
- Chain `.fillna(default)` for remaining NaN at boundaries
- Be explicit about fill logic — always comment the reasoning

```python
df["score"] = df["score"].ffill().fillna(0).astype(int)
```

---

## 6. Type Awareness

### Common Pitfalls
- **NaN makes int → float**: Pandas columns with any NaN become float64. After filling NaN, cast back to int if appropriate
- **merge_asof requires matching dtypes**: Ensure join keys have the same dtype on both sides
- **Decimals in "integer" columns**: Clock values can have fractional seconds — use float, don't assume int

### Type Annotations
- Use type hints on function signatures for clarity
- Not required on every local variable, but encouraged for function parameters and return types

```python
def compute_elapsed(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

---

## 7. Comments & Documentation

### Docstrings
- Every function gets a docstring explaining what it does
- Include parameter descriptions for non-obvious functions
- Document output columns for data-producing functions

### Inline Comments
- Explain **why**, not what (the code shows what)
- Comment non-obvious domain logic (e.g., "OT periods are 300 seconds")
- Use section dividers for visual separation of logical blocks

```python
# ── Paths ────────────────────────────────────────────────────────────────────
# ── Config ───────────────────────────────────────────────────────────────────
```

---

## 8. Progress & Logging

### For Scripts with `main()`
- Print progress messages for long-running steps
- Include row counts and game counts so output is verifiable
- Print a sample of the output at the end

```python
print("Loading play-by-play data...")
df = load_pbp()
print(f"  {len(df):,} plays across {df['game_id'].nunique():,} games")
```

---

## 9. Code Quality Checklist

Before finalizing a script:
- [ ] Module docstring describes purpose, inputs, outputs
- [ ] All imports at top, grouped correctly
- [ ] Constants in `UPPER_SNAKE_CASE`
- [ ] Functions have type hints and docstrings
- [ ] `snake_case` naming throughout
- [ ] No unused imports or dead code
- [ ] `usecols` used for CSV reads when not all columns are needed
- [ ] NaN handling is explicit and commented
- [ ] dtype mismatches checked (especially around merges)
- [ ] Output uses Parquet with `index=False`
- [ ] Script is importable (`if __name__ == "__main__"` guard)
- [ ] Progress messages for long-running operations

---

## 10. Workflow Process

### Typical Data Pipeline Script:
1. **Define paths and constants** at module level
2. **Load** — Read only needed columns
3. **Derive** — Compute new columns (vectorized)
4. **Transform** — Reshape, merge, aggregate
5. **Clean** — Handle NaN, enforce dtypes
6. **Export** — Write to Parquet
7. **Verify** — Print shape, sample rows, summary stats

---

## 11. Notes for AI Agents

When working with this codebase:
- Preserve `snake_case` naming and `UPPER_SNAKE_CASE` constants
- Always use `pathlib.Path` for file paths, anchored to `PROJECT_ROOT`
- Use vectorized pandas/numpy over `.apply()` or Python loops
- Load only required columns with `usecols`
- Be careful with dtypes — check for NaN-induced float promotion and merge key mismatches
- Write Parquet by default, CSV only when human readability is needed
- Include progress prints in `main()` functions
- Verify assumptions about data (e.g., OT encoding) empirically before coding around them
- Document iteration history and design decisions when the path to the solution was non-obvious
