import pandas as pd
import io
import re
from .header_detection import detect_header_row
from openpyxl.utils import get_column_letter

# ======================================================
# SAFE SINGLE SHEET CLEAN
# ======================================================
def clean_single_sheet_from_raw(df_raw: pd.DataFrame, header_idx: int) -> pd.DataFrame:
    header_row = df_raw.iloc[header_idx]
    data = df_raw.iloc[header_idx + 1 :].copy()

    if data.empty:
        return pd.DataFrame()

    # Remove fully empty columns early
    data = data.dropna(axis=1, how="all")

    # Track original row order
    data["__row_id__"] = range(len(data))

    # Normalize header length
    header = header_row.iloc[: data.shape[1]].fillna("").astype(str).tolist()
    if len(header) < data.shape[1]:
        header += [f"column_{i}" for i in range(len(header), data.shape[1])]

    data.columns = header

    # Clean column names
    fixed_cols = []
    for i, c in enumerate(data.columns):
        c = str(c).strip()
        fixed_cols.append(
            c if c and not c.lower().startswith("unnamed")
            else f"column_{i}"
        )
    data.columns = fixed_cols

    # Drop empty rows
    data = data.dropna(how="all")

    # Drop empty columns again (safety)
    data = data.dropna(axis=1, how="all")

    return data


# ======================================================
# COLUMN STANDARDIZATION
# ======================================================
def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    def snake(s):
        s = re.sub(r"[^\w\s]", "", str(s).lower())
        return re.sub(r"\s+", "_", s).strip("_") or "column"

    seen = {}
    cols = []

    for c in df.columns:
        base = snake(c)
        seen[base] = seen.get(base, 0)
        cols.append(base if seen[base] == 0 else f"{base}_{seen[base]}")
        seen[base] += 1

    df.columns = cols
    return df


# ======================================================
# DROP UNNAMED NUMERIC COLUMNS (🔥 KEY FIX)
# ======================================================
def drop_unnamed_numeric_columns(df: pd.DataFrame, threshold: float = 0.8) -> pd.DataFrame:
    cols_to_drop = []

    for col in df.columns:
        if col.startswith("column_"):
            non_null = df[col].dropna()
            if non_null.empty:
                cols_to_drop.append(col)
                continue

            numeric_ratio = pd.to_numeric(non_null, errors="coerce").notna().mean()
            if numeric_ratio >= threshold:
                cols_to_drop.append(col)

    return df.drop(columns=cols_to_drop)


# ======================================================
# SUMMARY ROW REMOVAL
# ======================================================
def remove_summary_rows(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    keys = [k.lower() for k in keywords]

    def is_summary(row):
        return any(
            any(k in str(v).lower() for k in keys)
            for v in row if pd.notna(v)
        )

    return df.loc[~df.apply(is_summary, axis=1)]


# ======================================================
# SMART DEDUPLICATION
# ======================================================
def smart_deduplicate(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    subset = [c for c in (subset or []) if c in df.columns]
    if not subset:
        return df.drop_duplicates()

    df["_score"] = df.notna().sum(axis=1)
    df = df.sort_values("_score", ascending=False)
    df = df.drop_duplicates(subset=subset, keep="first")
    return df.drop(columns="_score")


# ======================================================
# MAIN PIPELINE
# ======================================================
def smart_clean_sheets_from_bytes(
    file_bytes: bytes,
    apply_standardize: bool,
    remove_summary: bool,
    summary_keywords: list[str],
    remove_dupes: bool,
    dup_subset_map,
    drop_missing: bool,
) -> dict:
    try:
        raw_sheets = pd.read_excel(
            io.BytesIO(file_bytes),
            sheet_name=None,
            header=None,
            engine="openpyxl",
        )
    except Exception:
        raise ValueError(
            "This Excel file is corrupted or exported incorrectly.\n\n"
            "Fix: Open it in Excel → Save As → Excel Workbook (.xlsx)"
        )

    cleaned = {}

    for sheet, df_raw in raw_sheets.items():
        if df_raw.empty:
            cleaned[sheet] = pd.DataFrame()
            continue

        header_idx = detect_header_row(df_raw)
        df = clean_single_sheet_from_raw(df_raw, header_idx)

        if apply_standardize:
            df = standardize_column_names(df)

        if remove_summary:
            df = remove_summary_rows(df, summary_keywords)

        if remove_dupes:
            df = smart_deduplicate(df, ["employeeid"])

        # 🔥 DROP unnamed numeric junk columns
        df = drop_unnamed_numeric_columns(df)

        if drop_missing:
            df = df.dropna()

        # Restore original row order
        if "__row_id__" in df.columns:
            df = df.sort_values("__row_id__").drop(columns="__row_id__")

        cleaned[sheet] = df.reset_index(drop=True)

    return cleaned


# ======================================================
# EXCEL OUTPUT
# ======================================================
def make_excel_bytes_from_sheets(sheets: dict) -> io.BytesIO:
    out = io.BytesIO()

    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=name[:31])
            ws = writer.book[name[:31]]
            ws.freeze_panes = "A2"
            for col in ws.columns:
                ws.column_dimensions[get_column_letter(col[0].column)].width = 15

    out.seek(0)
    return out
