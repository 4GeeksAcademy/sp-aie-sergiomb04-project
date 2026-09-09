"""Data preparation and temporal split module for TrackFlow Sales Forecasting.

Prevents data leakage by adhering to strict chronological train/test separation
and fitting feature transformers exclusively on the training partition.
"""

from typing import Tuple, List, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


def load_data(filepath: str = "data/raw/trackflow_sales.csv") -> pd.DataFrame:
    """Load sales historical dataset and sort chronologically.

    Args:
        filepath: Path to the raw CSV file.

    Returns:
        pd.DataFrame: Cleaned and sorted DataFrame filtered for consolidated market.
    """
    df = pd.read_csv(filepath)
    df["month"] = pd.to_datetime(df["month"])
    
    # Filter for consolidated revenue
    if "market" in df.columns:
        df = df[df["market"] == "consolidated"].copy()
        
    df = df.sort_values("month").reset_index(drop=True)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values, ensure positive revenue, and validate date continuity.

    Args:
        df: Input DataFrame.

    Returns:
        pd.DataFrame: Validated DataFrame.
    """
    df_clean = df.copy()
    
    # Validate non-negative revenue
    if (df_clean["revenue_eur"] <= 0).any():
        raise ValueError("Detected non-positive values in revenue_eur")
        
    # Check for missing values in core columns
    core_cols = ["month", "revenue_eur", "shipments_processed"]
    if df_clean[core_cols].isnull().any().any():
        df_clean = df_clean.dropna(subset=core_cols).reset_index(drop=True)
        
    return df_clean


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer temporal and seasonal features for time-series regression.

    Features generated:
    - time_step: Monotonically increasing index capturing long-term growth trend.
    - month_num: Month of the year (1-12).
    - quarter: Quarter of the year (1-4).
    - sin_month, cos_month: Cyclical representation of seasonality.
    - is_nov_dec: Binary indicator for peak Q4 e-commerce holiday season (+25-35%).
    - is_feb: Binary indicator for post-holiday slowdown (-10-15%).

    Args:
        df: Input DataFrame with 'month' datetime column.

    Returns:
        pd.DataFrame: DataFrame enriched with feature columns.
    """
    df_feat = df.copy()
    
    # Base chronological index
    df_feat["time_step"] = np.arange(len(df_feat))
    
    # Date parts
    df_feat["year"] = df_feat["month"].dt.year
    df_feat["month_num"] = df_feat["month"].dt.month
    df_feat["quarter"] = df_feat["month"].dt.quarter
    
    # Cyclical seasonal transformation
    df_feat["sin_month"] = np.sin(2 * np.pi * df_feat["month_num"] / 12.0)
    df_feat["cos_month"] = np.cos(2 * np.pi * df_feat["month_num"] / 12.0)
    
    # Business-specific calendar markers
    df_feat["is_nov_dec"] = df_feat["month_num"].isin([11, 12]).astype(int)
    df_feat["is_feb"] = (df_feat["month_num"] == 2).astype(int)
    
    return df_feat


def temporal_split(
    df: pd.DataFrame,
    train_years: int = 8,
    test_years: int = 2
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Perform a strict chronological split (first N years train, last M years test).

    Args:
        df: DataFrame sorted chronologically.
        train_years: Number of initial years for training (default: 8 -> 96 months).
        test_years: Number of final years for testing (default: 2 -> 24 months).

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (train_df, test_df) with no index overlap.
    """
    total_months = len(df)
    train_months = train_years * 12
    test_months = test_years * 12
    
    if total_months < (train_months + test_months):
        raise ValueError(
            f"Dataset has {total_months} months, but {train_months + test_months} are required "
            f"for {train_years} train years and {test_years} test years."
        )
        
    train_df = df.iloc[:train_months].copy().reset_index(drop=True)
    test_df = df.iloc[train_months:train_months + test_months].copy().reset_index(drop=True)
    
    # Strict temporal sanity check
    if train_df["month"].max() >= test_df["month"].min():
        raise ValueError("Data leakage detected: train_max_date >= test_min_date")
        
    return train_df, test_df


def prepare_datasets(
    filepath: str = "data/raw/trackflow_sales.csv",
    feature_cols: Optional[List[str]] = None,
    target_col: str = "revenue_eur"
) -> Tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler, List[str]]:
    """Complete data prep pipeline returning train/test splits and fitted scaler.

    Args:
        filepath: Path to dataset.
        feature_cols: List of features to use. If None, uses default feature set.
        target_col: Target variable name.

    Returns:
        train_df, test_df, X_train_scaled, X_test_scaled, y_train, y_test, scaler, feature_cols
    """
    if feature_cols is None:
        feature_cols = [
            "time_step",
            "month_num",
            "quarter",
            "sin_month",
            "cos_month",
            "is_nov_dec",
            "is_feb"
        ]
        
    raw_df = load_data(filepath)
    cleaned_df = clean_data(raw_df)
    featured_df = create_features(cleaned_df)
    
    train_df, test_df = temporal_split(featured_df, train_years=8, test_years=2)
    
    X_train_raw = train_df[feature_cols].values
    X_test_raw = test_df[feature_cols].values
    
    y_train = train_df[target_col].values
    y_test = test_df[target_col].values
    
    # Fit scaler strictly on training data
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_raw)
    X_test_scaled = scaler.transform(X_test_raw)
    
    return train_df, test_df, X_train_scaled, X_test_scaled, y_train, y_test, scaler, feature_cols
