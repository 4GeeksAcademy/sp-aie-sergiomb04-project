"""Unit tests for TrackFlow sales dataset temporal split and leakage prevention."""

import pytest
import pandas as pd
import numpy as np
from src.pipelines.data_prep import (
    load_data,
    clean_data,
    create_features,
    temporal_split,
    prepare_datasets
)
from src.pipelines.evaluate import (
    calculate_mse,
    calculate_psi,
    calculate_gini,
    calculate_k2_score,
    evaluate_forecast
)


@pytest.fixture
def loaded_dataset():
    """Load and prepare cleaned historical dataset."""
    df = load_data("data/raw/trackflow_sales.csv")
    df = clean_data(df)
    df = create_features(df)
    return df


def test_temporal_split_chronological_ordering(loaded_dataset):
    """Test that max date in train is strictly less than min date in test."""
    train_df, test_df = temporal_split(loaded_dataset, train_years=8, test_years=2)
    
    max_train_date = train_df["month"].max()
    min_test_date = test_df["month"].min()
    
    assert max_train_date < min_test_date, (
        f"Temporal leakage detected: max_train_date ({max_train_date}) is not strictly "
        f"before min_test_date ({min_test_date})"
    )
    assert max_train_date == pd.Timestamp("2023-12-01"), f"Expected 2023-12-01, got {max_train_date}"
    assert min_test_date == pd.Timestamp("2024-01-01"), f"Expected 2024-01-01, got {min_test_date}"


def test_temporal_split_exact_lengths(loaded_dataset):
    """Test that split represents exactly 8 years train (96 months) and 2 years test (24 months)."""
    train_df, test_df = temporal_split(loaded_dataset, train_years=8, test_years=2)
    
    assert len(train_df) == 96, f"Expected 96 train rows (8 years * 12 months), got {len(train_df)}"
    assert len(test_df) == 24, f"Expected 24 test rows (2 years * 12 months), got {len(test_df)}"
    assert len(loaded_dataset) == 120, f"Expected 120 total rows (10 years * 12 months), got {len(loaded_dataset)}"


def test_no_shared_indices_or_duplicate_dates(loaded_dataset):
    """Test that there is zero overlap in dates or records between train and test sets."""
    train_df, test_df = temporal_split(loaded_dataset, train_years=8, test_years=2)
    
    train_dates = set(train_df["month"])
    test_dates = set(test_df["month"])
    
    intersection = train_dates.intersection(test_dates)
    assert len(intersection) == 0, f"Found overlapping dates between train and test: {intersection}"


def test_scaler_fitted_only_on_train():
    """Verify that feature scaling fits strictly on training data without test leakage."""
    train_df, test_df, X_train_scaled, X_test_scaled, y_train, y_test, scaler, _ = prepare_datasets()
    
    # Train mean should be close to 0 and std close to 1
    assert np.allclose(X_train_scaled.mean(axis=0), 0.0, atol=1e-5)
    assert np.allclose(X_train_scaled.std(axis=0), 1.0, atol=1e-5)
    
    # Test set scaled using train mean/std (should NOT have exactly mean 0 or std 1 due to drift/growth)
    assert not np.allclose(X_test_scaled.mean(axis=0), 0.0, atol=1e-2)
    assert scaler.n_samples_seen_ == 96


def test_revenue_validity(loaded_dataset):
    """Ensure revenue values are all positive floats with no missing values."""
    assert (loaded_dataset["revenue_eur"] > 0).all(), "Revenue contains non-positive values"
    assert not loaded_dataset["revenue_eur"].isnull().any(), "Revenue contains NaN values"


def test_metrics_evaluation_functions():
    """Test unit calculation of evaluation metrics."""
    np.random.seed(42)
    y_true = np.linspace(1000.0, 1600.0, 24) + np.random.normal(0, 50, 24)
    y_pred = np.linspace(1000.0, 1600.0, 24) + np.random.normal(0, 30, 24)
    y_train = np.linspace(800.0, 1200.0, 96) + np.random.normal(0, 50, 96)
    
    mse_res = calculate_mse(y_true, y_pred)
    assert "mse_eur2" in mse_res and mse_res["mse_eur2"] > 0
    assert "rmse_eur" in mse_res and mse_res["rmse_eur"] > 0
    
    psi_res = calculate_psi(y_train, y_true, num_bins=3)
    assert "psi_score" in psi_res and psi_res["psi_score"] >= 0
    
    gini_res = calculate_gini(y_true, y_pred)
    assert "normalized_gini" in gini_res
    assert -1.0 <= gini_res["normalized_gini"] <= 1.0
    
    residuals = y_true - y_pred
    k2_res = calculate_k2_score(residuals)
    assert "k2_statistic" in k2_res
    assert "p_value" in k2_res

