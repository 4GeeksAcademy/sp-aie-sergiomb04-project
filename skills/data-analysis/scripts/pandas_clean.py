"""
Safe snippet for basic pandas cleaning. Copy and adapt for your dataset.
Run: python pandas_clean.py  (ensure pandas is installed)
"""
import sys

import pandas as pd

# Load (adjust path and kwargs as needed)
try:
    df = pd.read_csv("data.csv")  # or read_json, read_excel
except FileNotFoundError:
    print("Error: Archivo 'data.csv' no encontrado.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error al cargar CSV: {e}", file=sys.stderr)
    sys.exit(1)
print("df_shape", df.shape)
print("df_dtypes", df.dtypes)

# Drop fully null columns
df = df.dropna(axis=1, how="all")
print("df_shape_after_drop_all_null_cols", df.shape)

# Fill or drop nulls in key columns (customise columns)
# df = df.dropna(subset=["required_col"])
# df["optional_col"] = df["optional_col"].fillna(0)

# Normalise column names (optional)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
print("df_columns", list(df.columns))

# Deduplicate (optional)
before = len(df)
df = df.drop_duplicates()
print("rows_dropped_duplicates", before - len(df))

# Sample output
print("df_head", df.head())
