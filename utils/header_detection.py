# utils/header_detection.py
import pandas as pd
import re

def is_header_like_cell(value) -> bool:
    """
    Returns True if cell looks like a column name, not data.
    """
    if pd.isna(value):
        return False

    s = str(value).strip()
    if s == "":
        return False

    # Reject pure numbers (data)
    if re.fullmatch(r"[0-9,.%]+", s):
        return False

    # Reject ID-like values (EMP-001, ID123, etc.)
    if re.search(r"\b(id|code|emp)[-_]?\d+", s.lower()):
        return False

    # Accept words, mixed words+numbers (Salary2023)
    return True


def detect_header_row(df_raw: pd.DataFrame) -> int:
    """
    Detect the most likely header row in a raw Excel sheet.
    """

    best_row = 0
    best_score = float("-inf")

    max_rows_to_check = min(len(df_raw), 20)  # headers are near top

    for i in range(max_rows_to_check):
        row = df_raw.iloc[i]

        non_empty = row.notna().sum()
        if non_empty == 0:
            continue

        header_like = sum(is_header_like_cell(v) for v in row)
        unique_vals = len(set(str(v).strip().lower() for v in row if pd.notna(v)))

        # Penalize rows that look like data
        numeric_cells = sum(
            str(v).replace(".", "").replace(",", "").isdigit()
            for v in row if pd.notna(v)
        )

        id_like_cells = sum(
            bool(re.search(r"\d", str(v))) and bool(re.search(r"[a-zA-Z]", str(v)))
            for v in row if pd.notna(v)
        )

        # Prefer top rows
        position_bonus = max(0, 10 - i)

        score = (
            (3 * header_like)
            + unique_vals
            - (2 * numeric_cells)
            - id_like_cells
            + position_bonus
        )

        if score > best_score:
            best_score = score
            best_row = i

    return best_row
