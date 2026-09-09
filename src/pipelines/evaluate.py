"""Evaluation metrics module for TrackFlow Sales Forecasting.

Calculates key technical and business KPIs:
- MSE (Mean Squared Error in EUR^2 and % of average monthly revenue)
- PSI (Population Stability Index between train and test distributions)
- Normalized Gini Coefficient (discrimination and ordering power in regression)
- K2 Score (D'Agostino-Pearson test for residual normality)
- MAE, RMSE, WAPE, and MAPE for Finance stakeholders.
"""

from typing import Dict, Any, Tuple
import numpy as np
import scipy.stats as stats
from sklearn.metrics import mean_squared_error, mean_absolute_error


def calculate_mse(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate Mean Squared Error and relative error metrics.

    Args:
        y_true: Ground truth target values.
        y_pred: Predicted values.

    Returns:
        Dict with MSE (EUR^2), RMSE (EUR), and RMSE as percentage of mean actual revenue.
    """
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    mean_val = float(np.mean(y_true))
    rmse_pct = float((rmse / mean_val) * 100.0) if mean_val > 0 else 0.0
    
    return {
        "mse_eur2": mse,
        "rmse_eur": rmse,
        "mean_actual_eur": mean_val,
        "rmse_pct_of_mean": rmse_pct
    }


def calculate_psi(
    reference: np.ndarray,
    target: np.ndarray,
    num_bins: int = 5,
    epsilon: float = 1e-4
) -> Dict[str, Any]:
    """Calculate Population Stability Index (PSI) to assess distribution shift.

    Args:
        reference: Baseline distribution (e.g. y_train).
        target: Comparison distribution (e.g. y_test or y_pred).
        num_bins: Number of quantile buckets.
        epsilon: Small constant to avoid log(0) or division by zero.

    Returns:
        Dict with PSI score and business interpretation.
    """
    # Define bin edges using reference quantiles
    quantiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(reference, quantiles)
    bin_edges[0] -= 1e-5
    bin_edges[-1] += 1e-5

    # Calculate frequencies in each bin
    ref_counts, _ = np.histogram(reference, bins=bin_edges)
    tgt_counts, _ = np.histogram(target, bins=bin_edges)

    ref_pct = np.maximum(ref_counts / len(reference), epsilon)
    tgt_pct = np.maximum(tgt_counts / len(target), epsilon)

    # PSI formula: sum((Actual% - Expected%) * ln(Actual% / Expected%))
    psi_per_bin = (tgt_pct - ref_pct) * np.log(tgt_pct / ref_pct)
    total_psi = float(np.sum(psi_per_bin))

    if total_psi < 0.10:
        interpretation = "Estable (Sin cambio significativo en la distribución)"
    elif total_psi <= 0.25:
        interpretation = "Deriva Moderada (Cambio detectable entre train y test)"
    else:
        interpretation = "Deriva Significativa (Esperable por crecimiento acumulado de 10 años)"

    return {
        "psi_score": total_psi,
        "interpretation": interpretation,
        "num_bins": num_bins
    }


def calculate_gini(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate the Normalized Gini Coefficient for regression.

    Measures the ranking capability of the model (ordering high vs low revenue months).

    Args:
        y_true: Actual revenue values.
        y_pred: Predicted values.

    Returns:
        Dict with Raw Gini, Theoretical Maximum Gini, and Normalized Gini.
    """
    def _raw_gini(actual: np.ndarray, prediction: np.ndarray) -> float:
        n = len(actual)
        # Sort actual by prediction descending
        order = np.argsort(-prediction)
        sorted_actual = actual[order]
        
        cumulative_actual = np.cumsum(sorted_actual) / np.sum(actual)
        cumulative_population = np.arange(1, n + 1) / n
        
        # Area under curve using trapezoidal rule
        auc = float(np.trapezoid(cumulative_actual, cumulative_population))
        return 2.0 * auc - 1.0

    gini_pred = _raw_gini(y_true, y_pred)
    gini_max = _raw_gini(y_true, y_true)
    normalized_gini = float(gini_pred / gini_max) if gini_max != 0 else 0.0

    return {
        "raw_gini": gini_pred,
        "max_gini": gini_max,
        "normalized_gini": normalized_gini
    }


def calculate_k2_score(residuals: np.ndarray) -> Dict[str, Any]:
    """Calculate D'Agostino-Pearson K^2 test statistic for residual normality.

    Args:
        residuals: Array of errors (y_true - y_pred).

    Returns:
        Dict with K^2 statistic, p-value, and normality assessment.
    """
    # SciPy normaltest computes K^2 = s^2 + k^2 based on skewness and kurtosis
    stat, p_val = stats.normaltest(residuals)
    stat = float(stat)
    p_val = float(p_val)
    
    is_normal = p_val > 0.05
    interpretation = (
        "Residuos compatibles con distribución normal (p > 0.05, no hay sesgo sistemático)"
        if is_normal
        else "Residuos con leve desviación de normalidad (p <= 0.05)"
    )

    return {
        "k2_statistic": stat,
        "p_value": p_val,
        "is_normal": is_normal,
        "interpretation": interpretation
    }


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray) -> Dict[str, Any]:
    """Run full evaluation suite and return structured metrics dictionary.

    Args:
        y_true: Test set actual revenue.
        y_pred: Test set predicted revenue.
        y_train: Training set actual revenue (for PSI baseline).

    Returns:
        Dict containing all required and complementary metrics.
    """
    residuals = y_true - y_pred
    
    mse_metrics = calculate_mse(y_true, y_pred)
    psi_metrics = calculate_psi(reference=y_train, target=y_true)
    gini_metrics = calculate_gini(y_true, y_pred)
    k2_metrics = calculate_k2_score(residuals)
    
    mae = float(mean_absolute_error(y_true, y_pred))
    mape = float(np.mean(np.abs(residuals / y_true)) * 100.0)
    wape = float(np.sum(np.abs(residuals)) / np.sum(y_true) * 100.0)

    return {
        "mse": mse_metrics,
        "psi": psi_metrics,
        "gini": gini_metrics,
        "k2_score": k2_metrics,
        "finance_friendly": {
            "mae_eur": mae,
            "mape_pct": mape,
            "wape_pct": wape,
            "total_actual_revenue_test_eur": float(np.sum(y_true)),
            "total_predicted_revenue_test_eur": float(np.sum(y_pred)),
            "net_revenue_variance_pct": float(((np.sum(y_pred) - np.sum(y_true)) / np.sum(y_true)) * 100.0)
        }
    }
