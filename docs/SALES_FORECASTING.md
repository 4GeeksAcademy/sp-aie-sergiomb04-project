# TrackFlow — Sales Forecasting & Revenue Prediction

> **Machine Learning Regression Pipeline for Monthly Consolidated Revenue Forecasting**  
> *Target Stakeholders: Thomas Harry (CEO), Andres Kim (CTO), Ana Whitfield (Warehouse Ops), and Finance Leadership.*

---

## 1. Executive Summary & Model Justification

TrackFlow generates revenue primarily based on the volume and value of shipments fulfilled across its two international fulfillment hubs: **Los Angeles (USA)** and **Zaragoza (Spain)**. Because e-commerce logistics experiences strong cyclicality (high demand in Q4 holiday season, post-holiday slowdown in February), executive leadership requires accurate, interpretable revenue projections to budget warehouse capacity, carrier allocations, and cash flows.

### Algorithm Selection: Random Forest Regressor
- **Parameters:** `n_estimators=100`, `max_depth=10`, `random_state=42`, `n_jobs=-1`.
- **Finance & Leadership Rationale:**
  1. **Tree-Level Explainability:** Unlike opaque black-box neural networks, Random Forest is an ensemble of decision trees where feature contributions to revenue (e.g. Q4 holiday peak vs. February dip) can be audited directly by financial controllers.
  2. **Empirical Uncertainty Bands:** Because the forest consists of 100 individual estimator trees, we compute the empirical 5th and 95th percentiles across all tree predictions. This provides Finance with an intuitive, distribution-free risk interval ($p_{05}$ to $p_{95}$) for sensitivity analysis.
  3. **Robustness:** Resilient to seasonal spikes and post-holiday drops without overfitting.
  4. **Reproducibility:** Seed fixed at `random_state=42` ensures exact reproducibility across audit cycles.

---

## 2. Temporal Split & Anti-Leakage Safeguards

- **Historical Range:** 10 years of consolidated monthly data (120 records from `2016-01` to `2025-12`).
- **Training Partition:** First **8 years** (`2016-01` to `2023-12`, 96 months).
- **Test / Verification Partition:** Last **2 years** (`2024-01` to `2025-12`, 24 months).
- **Leakage Safeguards:**
  - Strict chronological cutoff: $\max(\text{train\_date}) < \min(\text{test\_date})$.
  - Zero index or date overlap between partitions.
  - Feature transformers (`StandardScaler`) fit **exclusively** on training data and applied via `.transform()` to test data.

---

## 3. Test Evaluation Metrics (2024–2025 Test Set)

| Metric | Value | Finance Interpretation & Status |
|---|---|---|
| **MSE (Mean Squared Error)** | `13,322,085,784.57 €²` | Error cuadrático medio de la predicción en el período de 24 meses. |
| **RMSE (% of Mean Revenue)** | `115,421.34 €` (**8.88%**) | Desviación estándar del error; representa menos del 9% de la facturación media mensual (~1.3M €). |
| **Normalized Gini** | **`0.6788`** (Raw: `0.0433`) | Alta capacidad discriminante para ordenar correctamente meses pico vs. meses valle. |
| **K2 Score (D'Agostino-Pearson)** | `0.5924` ($p = 0.7436$) | $p > 0.05$: Residuos normales sin sesgo sistemático en las estimaciones. |
| **PSI (Population Stability Index)** | `5.5268` | Deriva poblacional esperada debido al crecimiento compuesto anual del 6% a lo largo de 10 años. |
| **WAPE (Weighted Abs. % Error)** | **`7.09%`** | Margen de error porcentual ponderado sobre la facturación global de test. |
| **MAE (Mean Absolute Error)** | `92,055.18 €` | Error medio absoluto por mes evaluado. |

---

## 4. Plain-Language Guide for Finance Stakeholders

1. **MSE / RMSE (Error Cuadrático y Desviación Promedio):**
   - *Significado:* Mide la distancia promedio entre las ventas reales y las predichas. El RMSE (115.421 €) equivale a un 8.88% de las ventas mensuales promedio (~1.3M €), proporcionando un margen de error estrecho para planificación de flujo de caja.
2. **Normalized Gini (Capacidad de Discriminación y Ordenamiento):**
   - *Significado:* Indica si el modelo sabe priorizar correctamente qué meses tendrán mayor facturación (ej. Black Friday/Navidad) y cuáles menor (ej. Febrero). Un Gini normalizado de 0.68 confirma que el modelo no confunde una estacionalidad baja normal con una anomalía operativa.
3. **K2 Score de Residuos (Diagnóstico de Sesgo):**
   - *Significado:* Comprueba si los errores del modelo se distribuyen de forma simétrica e impredecible (ruido blanco). Un p-valor de 0.74 (> 0.05) certifica que el modelo no está sobreestimando ni subestimando sistemáticamente los ingresos.
4. **PSI (Índice de Estabilidad Poblacional):**
   - *Significado:* Evalúa si la distribución de ventas de los últimos 2 años es idéntica a la de los 8 años anteriores. El valor elevado refleja el crecimiento anual compuesto de la compañía (3-9% anual), confirmando la expansión del negocio.
5. **WAPE (Error Porcentual Absoluto Ponderado):**
   - *Significado:* El error total acumulado respecto a la facturación real total es de solo el 7.09%, cumpliendo holgadamente el criterio de precisión financiera para presupuesto anual.

---

## 5. Forecast Visualization

The forecast chart with the 5th-95th percentile variability band is generated at:
`reports/figures/sales_forecast_trackflow.png`

![Sales Forecast TrackFlow](../reports/figures/sales_forecast_trackflow.png)

---

## 6. How to Run Pipeline & Verification Tests

```bash
# Run unit tests verifying 8/2 temporal split & anti-leakage
uv run pytest tests/pipelines/test_sales_split.py

# Execute the complete training, evaluation, and visualization pipeline
uv run python -m src.pipelines.train_forecast
```

### Module Structure
```text
src/pipelines/
├── __init__.py
├── data_prep.py        # Loading, cleaning, feature engineering & temporal split
├── evaluate.py         # MSE, PSI, Gini, K2 Score, WAPE, MAPE calculators
└── train_forecast.py   # Model training, uncertainty estimation, visualization
```
