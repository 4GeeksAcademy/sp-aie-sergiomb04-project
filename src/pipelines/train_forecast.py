"""Training and forecasting pipeline for TrackFlow Sales Forecasting.

Model Selection & Justification for Finance & Executive Leadership:
------------------------------------------------------------------
1. Interpretability & Tree Explainability:
   Random Forest Regressor builds an ensemble of deterministic decision trees that
   Finance can audit. Feature importances quantify the exact drivers of revenue
   (seasonality, calendar effects, long-term trends).

2. Native Uncertainty & Variability Bands:
   Unlike single point-forecast models, the 100 estimator trees provide an empirical
   probability distribution for each monthly prediction. The 5th and 95th percentiles
   form an intuitive, distribution-free risk interval (p05 to p95) for budget planning.

3. Robustness & Overfitting Resistance:
   Bootstrap aggregation (bagging) mitigates variance and resists noise in monthly
   ecommerce fluctuations (e.g., Black Friday surge vs. February dip).

4. Reproducibility:
   Fixed `random_state=42` guarantees exact determinism across training runs and audit cycles.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sklearn.ensemble import RandomForestRegressor

from src.pipelines.data_prep import prepare_datasets, load_data, clean_data, create_features, temporal_split
from src.pipelines.evaluate import evaluate_forecast


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_estimators: int = 100,
    random_state: int = 42
) -> RandomForestRegressor:
    """Train Random Forest Regressor with fixed random seed.

    Args:
        X_train: Scaled training feature matrix.
        y_train: Training target array.
        n_estimators: Number of trees in the forest.
        random_state: Seed for reproducibility.

    Returns:
        Fitted RandomForestRegressor.
    """
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=10,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    return model


def predict_with_uncertainty(
    model: RandomForestRegressor,
    X: np.ndarray,
    lower_percentile: float = 5.0,
    upper_percentile: float = 95.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate point predictions along with empirical uncertainty intervals.

    Args:
        model: Trained RandomForestRegressor.
        X: Feature matrix.
        lower_percentile: Lower bound percentile (e.g. 5.0 for 5th percentile).
        upper_percentile: Upper bound percentile (e.g. 95.0 for 95th percentile).

    Returns:
        Tuple of (y_pred_mean, y_pred_lower, y_pred_upper).
    """
    # Collect predictions from each individual decision tree
    tree_predictions = np.array([tree.predict(X) for tree in model.estimators_])
    
    y_pred_mean = model.predict(X)
    y_pred_lower = np.percentile(tree_predictions, lower_percentile, axis=0)
    y_pred_upper = np.percentile(tree_predictions, upper_percentile, axis=0)
    
    return y_pred_mean, y_pred_lower, y_pred_upper


def plot_forecast_with_bands(
    test_dates: pd.Series,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_lower: np.ndarray,
    y_upper: np.ndarray,
    output_path: str = "reports/figures/sales_forecast_trackflow.png"
) -> None:
    """Generate high-resolution executive forecast chart with uncertainty band.

    Args:
        test_dates: Date series for test period.
        y_true: Ground truth revenue.
        y_pred: Predicted revenue.
        y_lower: Lower bound of variability band.
        y_upper: Upper bound of variability band.
        output_path: Output image filepath.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    
    dates = pd.to_datetime(test_dates).values
    
    # Plot ground truth
    ax.plot(
        dates,
        y_true / 1000.0,
        marker="o",
        color="#1E293B",
        linewidth=2.2,
        label="Ventas Reales (Ground Truth)",
        zorder=4
    )
    
    # Plot point forecast
    ax.plot(
        dates,
        y_pred / 1000.0,
        marker="s",
        color="#2563EB",
        linewidth=2.0,
        linestyle="--",
        label="Predicción Modelo (Random Forest)",
        zorder=5
    )
    
    # Plot uncertainty band (5th to 95th percentile)
    ax.fill_between(
        dates,
        y_lower / 1000.0,
        y_upper / 1000.0,
        color="#93C5FD",
        alpha=0.45,
        label="Banda de Incertidumbre (Percentil 5-95)",
        zorder=3
    )
    
    # Formatting
    ax.set_title(
        "TrackFlow — Predicción de Ventas y Rango de Variabilidad (Test 2024-2025)",
        fontsize=14,
        fontweight="bold",
        pad=15
    )
    ax.set_xlabel("Período Mensual", fontsize=11, fontweight="semibold", labelpad=10)
    ax.set_ylabel("Ingresos Consolidados (Miles de EUR)", fontsize=11, fontweight="semibold", labelpad=10)
    
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.xticks(rotation=35, ha="right", fontsize=9)
    plt.yticks(fontsize=9)
    
    ax.grid(True, linestyle=":", alpha=0.6, color="#94A3B8")
    ax.legend(loc="upper left", frameon=True, framealpha=0.9, facecolor="#F8FAFC", edgecolor="#CBD5E1")
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[INFO] Visualization saved successfully at: {output_path}")


def run_pipeline() -> Dict[str, Any]:
    """Execute complete training, evaluation, visualization and reporting workflow."""
    print("=" * 70)
    print(">>> TRACKFLOW SALES FORECASTING PIPELINE (RANDOM FOREST REGRESSOR) <<<")
    print("=" * 70)
    
    # 1. Prepare Data
    train_df, test_df, X_train, X_test, y_train, y_test, scaler, feature_cols = prepare_datasets()
    print(f"[1/5] Data prepared: Train shape = {X_train.shape} (8 years), Test shape = {X_test.shape} (2 years)")
    print(f"      Features used: {feature_cols}")
    
    # 2. Train Model
    print("[2/5] Training Random Forest Regressor (n_estimators=100, random_state=42)...")
    model = train_model(X_train, y_train, n_estimators=100, random_state=42)
    
    # 3. Predict & Extract Uncertainty Bands
    print("[3/5] Generating predictions and empirical uncertainty intervals (5th-95th percentile)...")
    y_pred, y_lower, y_upper = predict_with_uncertainty(model, X_test)
    
    # 4. Evaluate Metrics
    print("[4/5] Evaluating test metrics (MSE, PSI, Gini, K2 Score)...")
    metrics = evaluate_forecast(y_true=y_test, y_pred=y_pred, y_train=y_train)
    
    # Print Console Summary
    print("-" * 70)
    print(f"  * MSE (EUR^2):           {metrics['mse']['mse_eur2']:,.2f}")
    print(f"  * RMSE (EUR):            {metrics['mse']['rmse_eur']:,.2f} ({metrics['mse']['rmse_pct_of_mean']:.2f}% de la media)")
    print(f"  * PSI Score:             {metrics['psi']['psi_score']:.4f} -> {metrics['psi']['interpretation']}")
    print(f"  * Normalized Gini:       {metrics['gini']['normalized_gini']:.4f} (Raw: {metrics['gini']['raw_gini']:.4f})")
    print(f"  * K2 Score (Residuos):   {metrics['k2_score']['k2_statistic']:.4f} (p-value: {metrics['k2_score']['p_value']:.4f}) -> {metrics['k2_score']['interpretation']}")
    print(f"  * MAE (EUR):             {metrics['finance_friendly']['mae_eur']:,.2f}")
    print(f"  * WAPE:                  {metrics['finance_friendly']['wape_pct']:.2f}%")
    print(f"  * MAPE:                  {metrics['finance_friendly']['mape_pct']:.2f}%")
    print("-" * 70)
    
    # Save Metrics JSON
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = reports_dir / "metrics_report.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Metrics report saved to: {metrics_file}")
    
    # 5. Generate and Save Plot
    print("[5/5] Generating sales forecast visualization with variability bands...")
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    figure_path = str(figures_dir / "sales_forecast_trackflow.png")
    plot_forecast_with_bands(
        test_dates=test_df["month"],
        y_true=y_test,
        y_pred=y_pred,
        y_lower=y_lower,
        y_upper=y_upper,
        output_path=figure_path
    )
    
    print("=" * 70)
    print(">>> PIPELINE COMPLETED SUCCESSFULLY <<<")
    print("=" * 70)
    return metrics


if __name__ == "__main__":
    run_pipeline()
