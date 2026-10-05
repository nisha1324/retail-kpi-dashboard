"""Turn the raw two-sheet workbook into one clean transactions table.

Rules (each one is logged with the number of rows it removes):
1. The two sheets overlap on 2010-12-01..09 (identical rows), so sheet 1 is
   cut at 2010-12-01 and sheet 2 is kept whole.
2. Exact duplicate rows are dropped.
3. Only product lines are kept: StockCode starts with 5 digits. This removes
   postage, fees, bank charges, manual adjustments and test codes.
4. Lines with Price <= 0 are dropped (free samples / write-offs, no revenue).
Cancellations (Invoice starting with "C") are kept as negative returns so
revenue can be shown both gross and net of returns.

Output: data/processed/transactions.parquet and results/prep_log.md
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "online_retail_II.xlsx"
OUT_DIR = ROOT / "data" / "processed"
OVERLAP_START = pd.Timestamp("2010-12-01")


def clean(sheet1: pd.DataFrame, sheet2: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    log: list[tuple[str, int]] = []
    s1 = sheet1[sheet1["InvoiceDate"] < OVERLAP_START]
    log.append(("Sheet overlap (2010-12-01..09 in both sheets)", len(sheet1) - len(s1)))
    df = pd.concat([s1, sheet2], ignore_index=True)

    before = len(df)
    df = df.drop_duplicates()
    log.append(("Exact duplicate rows", before - len(df)))

    before = len(df)
    df = df[df["StockCode"].astype(str).str.match(r"^\d{5}")]
    log.append(("Non-product stock codes (postage, fees, adjustments)", before - len(df)))

    before = len(df)
    df = df[df["Price"] > 0]
    log.append(("Price <= 0", before - len(df)))

    df = df.rename(columns={"Customer ID": "CustomerID"}).copy()
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    df["Description"] = df["Description"].astype("string")
    df["CustomerID"] = df["CustomerID"].astype("Int64")
    df["IsReturn"] = df["Invoice"].str.startswith("C")
    df["Revenue"] = (df["Quantity"] * df["Price"]).round(2)
    return df.reset_index(drop=True), log


def main() -> None:
    sheets = pd.read_excel(RAW, sheet_name=None)
    s1, s2 = sheets.values()
    raw_rows = len(s1) + len(s2)
    df, log = clean(s1, s2)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "results").mkdir(exist_ok=True)
    df.to_parquet(OUT_DIR / "transactions.parquet", index=False)

    lines = ["# Data prep log", "", f"Raw rows (both sheets): {raw_rows:,}", "",
             "| Rule | Rows removed |", "|---|---:|"]
    lines += [f"| {rule} | {n:,} |" for rule, n in log]
    lines += ["", f"Clean rows: {len(df):,} "
              f"({df['InvoiceDate'].min():%Y-%m-%d} to {df['InvoiceDate'].max():%Y-%m-%d})",
              f"Return lines kept as negatives: {int(df['IsReturn'].sum()):,}"]
    (ROOT / "results" / "prep_log.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
