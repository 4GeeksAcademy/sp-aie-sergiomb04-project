"""Unit tests for TrackFlow temporal cross-validation and chronological integrity.

Validates that:
- TimeSeriesSplit preserves strict chronological ordering in all folds.
- No indices are shuffled or leaked between train and validation partitions.
- Folds advance forward in time without future-to-past contamination.
- Evaluation metrics report mean ± standard deviation.
"""

import os
from pathlib import Path
import pytest
import numpy as np
from sklearn.model_selection import TimeSeriesSplit

from src.pipelines.data_prep import prepare_datasets
from src.pipelines.temporal_evaluation import (
    validate_temporal_split_indices,
    run_temporal_cross_validation,
    evaluate_full_train_and_test
)


@pytest.fixture
def training_data():
    """Load training features and labels from historical sales dataset."""
    train_df, _, X_train, _, y_train, _, _, _ = prepare_datasets()
    return X_train, y_train, train_df["month"]


def test_temporal_cv_chronological_ordering_intra_fold(training_data):
    """Verify that in every fold, max(train_idx) < min(val_idx) and no shuffling occurs."""
    X_train, y_train, _ = training_data
    tscv = TimeSeriesSplit(n_splits=5)
    splits = list(tscv.split(X_train))
    
    assert len(splits) == 5, f"Expected 5 folds, got {len(splits)}"
    
    for fold_idx, (tr_idx, val_idx) in enumerate(splits, start=1):
        # 1. Intra-fold chronological boundary
        max_train = int(np.max(tr_idx))
        min_val = int(np.min(val_idx))
        assert max_train < min_val, (
            f"Fold {fold_idx}: Train max index ({max_train}) must be strictly less than "
            f"validation min index ({min_val})"
        )
        
        # 2. No shuffling within train or validation
        assert np.all(np.diff(tr_idx) > 0), f"Fold {fold_idx}: Train indices are not monotonically increasing"
        assert np.all(np.diff(val_idx) > 0), f"Fold {fold_idx}: Validation indices are not monotonically increasing"
        
        # 3. Disjoint partitions within fold
        overlap = set(tr_idx).intersection(set(val_idx))
        assert len(overlap) == 0, f"Fold {fold_idx}: Found overlapping indices between train and val: {overlap}"


def test_temporal_cv_chronological_ordering_inter_folds(training_data):
    """Verify that no index of a subsequent fold appears before an index of a prior fold."""
    X_train, _, _ = training_data
    tscv = TimeSeriesSplit(n_splits=5)
    splits = list(tscv.split(X_train))
    
    for i in range(1, len(splits)):
        prev_tr, prev_val = splits[i - 1]
        curr_tr, curr_val = splits[i]
        
        # Validation window strictly advances forward in time
        assert np.min(curr_val) > np.min(prev_val), (
            f"Fold {i+1} min validation index ({np.min(curr_val)}) must be strictly greater "
            f"than Fold {i} min validation index ({np.min(prev_val)})"
        )
        assert np.max(curr_val) > np.max(prev_val), (
            f"Fold {i+1} max validation index ({np.max(curr_val)}) must be strictly greater "
            f"than Fold {i} max validation index ({np.max(prev_val)})"
        )
        
        # Validation partition of fold i must never overlap prior validation partition
        val_intersection = set(prev_val).intersection(set(curr_val))
        assert len(val_intersection) == 0, (
            f"Validation sets between fold {i} and {i+1} must be disjoint, got overlap: {val_intersection}"
        )
        
        # Train window expands chronologically: prior train is a strict subset of current train
        assert set(prev_tr).issubset(set(curr_tr)), (
            f"Prior train set in fold {i} must be a subset of current train set in fold {i+1}"
        )
        assert len(curr_tr) > len(prev_tr), "Training size must increase chronologically across folds"


def test_validate_temporal_split_indices_detects_violations():
    """Defensive test: ensure validation function catches temporal leakage and shuffling."""
    # Case 1: Leakage (train max >= val min)
    leaked_splits = [
        (np.array([0, 1, 2, 5]), np.array([3, 4]))
    ]
    with pytest.raises(ValueError, match="Data leakage detected"):
        validate_temporal_split_indices(leaked_splits)
        
    # Case 2: Shuffled train indices
    shuffled_splits = [
        (np.array([2, 1, 0]), np.array([3, 4]))
    ]
    with pytest.raises(ValueError, match="train indices are not strictly increasing"):
        validate_temporal_split_indices(shuffled_splits)
        
    # Case 3: Validation going backwards across folds
    regressive_splits = [
        (np.array([0, 1]), np.array([2, 3])),
        (np.array([0, 1, 2]), np.array([1, 4]))  # min val is 1 <= prev min val 2
    ]
    with pytest.raises(ValueError):
        validate_temporal_split_indices(regressive_splits)


def test_temporal_cv_mean_std_metrics_reporting(training_data):
    """Verify that temporal cross validation calculates and reports mean ± standard deviation."""
    X_train, y_train, dates = training_data
    summary = run_temporal_cross_validation(X_train, y_train, dates=dates, n_splits=5, random_state=42)
    
    assert summary["n_splits"] == 5
    assert len(summary["folds"]) == 5
    
    for metric_name in ["train_mae", "val_mae", "train_rmse", "val_rmse"]:
        assert metric_name in summary
        metric_dict = summary[metric_name]
        assert "mean" in metric_dict
        assert "std" in metric_dict
        assert "formatted" in metric_dict
        assert metric_dict["mean"] > 0
        assert metric_dict["std"] >= 0
        assert "±" in metric_dict["formatted"]
        assert "EUR" in metric_dict["formatted"]
        
    # Check that generalization gap exists and indicates higher validation error than train error
    assert summary["mean_generalization_gap_rmse_eur"] > 0, "Expected validation RMSE > train RMSE (overfitting gap)"
    assert summary["mean_generalization_gap_mae_eur"] > 0, "Expected validation MAE > train MAE (overfitting gap)"


def test_full_train_and_test_evaluation():
    """Verify full 8-year train vs 2-year test evaluation metrics."""
    metrics = evaluate_full_train_and_test(random_state=42)
    
    assert metrics["train_8y"]["samples"] == 96
    assert metrics["test_2y"]["samples"] == 24
    assert metrics["train_8y"]["mae_eur"] > 0
    assert metrics["train_8y"]["rmse_eur"] > 0
    assert metrics["test_2y"]["mae_eur"] > 0
    assert metrics["test_2y"]["rmse_eur"] > 0
    
    # Overfitting signature: test error is substantially higher than training error
    assert metrics["test_2y"]["rmse_eur"] > metrics["train_8y"]["rmse_eur"]


def test_evaluation_artifacts_exist():
    """Verify that required evaluation report and learning curve image exist."""
    img_path = Path("data/eval/learning_curve.png")
    assert img_path.exists(), f"Missing learning curve image at {img_path}"
    assert img_path.stat().st_size > 1000, "Learning curve image is unexpectedly small or empty"
