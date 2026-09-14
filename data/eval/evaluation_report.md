# Reporte Técnico de Evaluación: Modelo de Regresión para Sales Forecasting
**TrackFlow Tech — Unidad de Ingeniería e Inteligencia Artificial**  
**Ticket:** #ML-EVAL-2026-04 · Evaluación Técnica Formal de Modelo Previo a Promoción a Staging  
**Destinatarios:** Andrés Kim (CTO), Thomas Harry (CEO), Ana Whitfield (Head of Warehouse Operations), Carlos Vega (Head of Last Mile & Carriers)  
**Fecha de Evaluación:** Septiembre 2026  
**Entorno y Rama:** `feature/regression-model-eval`  

---

## 1. Resumen Ejecutivo y Respuestas al Ticket Técnico

En respuesta al ticket de auditoría técnica emitido por la dirección tecnológica previo a la promoción del modelo a staging, se ha llevado a cabo una evaluación rigurosa del modelo de regresión (**Random Forest Regressor**, $N_{\text{trees}}=100$, `max_depth=10`, `random_state=42`) entrenado para pronosticar los ingresos mensuales consolidados de TrackFlow (`revenue_eur`). 

A continuación se responden de forma directa y concluyente las tres preguntas del ticket técnico:

| Pregunta del Ticket | Diagnóstico Concluyente | Evidencia Técnica Cuantitativa |
| :--- | :--- | :--- |
| **1. ¿El modelo tiene underfitting, overfitting, o está bien ajustado?** | **Overfitting Moderado-Alto (Alta Varianza)** | En validación temporal cruzada (5 folds), el error de entrenamiento se sitúa en **$17,784.19$ EUR RMSE**, mientras que el error de validación escala a **$77,245.96$ EUR RMSE** (una brecha de generalización persistente de **$+59,461.77$ EUR** / $+334\%$). En el test final de 2 años (2024-2025), el RMSE alcanza **$115,421.34$ EUR** frente a los **$18,453.64$ EUR** observados en los 8 años de entrenamiento. |
| **2. ¿Qué tan estable es su desempeño si cambias la porción de datos de entrenamiento?** | **Inestable y Sensible al Período Temporal** | El desempeño en validación varía drásticamente según la ventana evaluada: el RMSE oscila entre **$39,879.16$ EUR** (Fold 1) y **$119,258.91$ EUR** (Fold 5), con una desviación estándar entre folds de **$\pm 26,433.09$ EUR** en RMSE y **$\pm 24,138.56$ EUR** en MAE. Esto refleja una fuerte vulnerabilidad a cambios de nivel y régimen macroeconómico. |
| **3. ¿Cuál es la acción correctiva específica recomendada?** | **Regularización Estructural de Hiperparámetros y Lags Autoregresivos** | Modificar la configuración de hiperparámetros para restringir la memorización: aumentar `min_samples_leaf` de $1$ a $4$, elevar `min_samples_split` de $2$ a $6$, acotar `max_depth` a $5$, e incorporar variables de rezago temporal explícitas (`lag_12_revenue_eur`, `rolling_mean_3m_revenue_eur`) para que el modelo capture la tendencia subyacente sin sobreajustar ruido estacional. |

---

## 2. Contexto de Negocio y Justificación de Métricas: MAE vs RMSE

### 2.1 Realidad Operativa de TrackFlow (`CONTEXT.md`)
TrackFlow opera como integrador logístico integral de e-commerce en dos mercados clave con almacenes físicos en **Los Ángeles** y **Zaragoza**, gestionando más de 130 empleados y facturando aproximadamente **9 millones de euros anuales** (~750,000 € a 1,300,000 € mensuales).

La dinámica del negocio depende críticamente de la precisión del pronóstico de ingresos y envíos:
1. **Coste de Sobreestimación:**  
   Si el modelo proyecta ventas significativamente por encima de la demanda real, el equipo de operaciones liderado por **Ana Whitfield** sobredimensiona la plantilla de almacén (actualmente ~70 operarios) contratando turnos temporales innecesarios, reserva espacio excesivo de almacenamiento que permanece ocioso y compromete volúmenes mínimos contractuales con transportistas (**UPS**, **FedEx**, **MRW**, **SEUR**), erosionando el estrecho margen operativo del sector logístico.
2. **Coste de Subestimación (Riesgo Crítico de Negocio):**  
   Si el modelo subestima la demanda (especialmente en los picos de Q4 de noviembre y diciembre con Black Friday y fiestas), los almacenes de Los Ángeles y Zaragoza se saturan, se generan cuellos de botella en picking/packing, se incumplen los SLAs de despacho acordados, se colapsa la atención al cliente de **Valentina Cruz** con reclamaciones B2C y se produce insatisfacción severa en las marcas B2B, amenazando directamente las renovaciones de contratos anuales gestionadas por **Miguel Torres**.

### 2.2 Justificación de la Métrica Principal: RMSE frente a MAE

Se evaluaron ambas métricas estándar de regresión:
- **MAE (Mean Absolute Error):**  
  $$\text{MAE} = \frac{1}{n}\sum_{i=1}^n |y_i - \hat{y}_i|$$
  Trata todos los errores con penalización lineal uniforme. Un error de $100,000$ EUR tiene exactamente el doble de peso que uno de $50,000$ EUR. Es intuitivo para proyecciones de flujo de caja mensual estándar.
- **RMSE (Root Mean Squared Error):**  
  $$\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^n (y_i - \hat{y}_i)^2}$$
  Penaliza de forma cuadrática y desproporcionada los desvíos atípicos y de gran magnitud.

> **Dictamen de Negocio:**  
> **El RMSE es la métrica rectora que mejor refleja el costo real de los errores para TrackFlow.**  
> En logística contractual, desviaciones pequeñas o moderadas ($\pm 25,000$ EUR a $\pm 35,000$ EUR) pueden ser absorbidas operacionalmente mediante horas extras y reasignaciones de bahía. Por el contrario, un desvío severo ($\ge 100,000$ EUR) durante los meses pico colapsa la infraestructura física, rompe contratos con clientes corporativos y acarrea penalizaciones económicas y de reputación irreparables. Dado que el daño operativo crece exponencialmente con la magnitud del error, la función de penalización convexa del **RMSE** modela con fidelidad matemática el perfil de riesgo de TrackFlow.

---

## 3. Estrategia de Validación Cruzada Temporal (TimeSeriesSplit)

Para evaluar la capacidad predictiva sin incurrir en **data leakage** (fuga de información futura hacia el pasado), se implementó una partición temporal estricta mediante `TimeSeriesSplit(n_splits=5)` sobre el conjunto de entrenamiento de 8 años (96 meses: 2016 a 2023).

### 3.1 Garantías de Integridad Cronológica
- **Preservación temporal absoluta:** En cada fold $k$, se cumple formalmente que:
  $$\max(\text{TrainIndex}_k) < \min(\text{ValIndex}_k)$$
- **Sin barajado (`shuffle=False`):** Los índices de entrenamiento y validación avanzan en orden estrictamente creciente ($\Delta \text{index} = +1$).
- **Expansión hacia adelante (Forward Chaining):** La ventana de entrenamiento se expande progresivamente sin solapamiento entre particiones de validación sucesivas:
  $$\text{Train}_1 \subset \text{Train}_2 \subset \dots \subset \text{Train}_5$$

### 3.2 Resultados Desglosados por Fold

| Fold | Ventana Entrenamiento (Train) | Meses Train | Ventana Validación (Val) | Meses Val | Train MAE (€) | Val MAE (€) | Train RMSE (€) | Val RMSE (€) | Brecha Generalización RMSE (€) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 2016-01 a 2017-04 | 16 | 2017-05 a 2018-08 | 16 | 18,479.64 | 28,960.17 | 23,831.77 | 39,879.16 | +16,047.39 |
| **2** | 2016-01 a 2018-08 | 32 | 2018-09 a 2019-12 | 16 | 12,461.40 | 71,182.37 | 16,467.03 | 87,188.25 | +70,721.22 |
| **3** | 2016-01 a 2019-12 | 48 | 2020-01 a 2021-04 | 16 | 12,596.08 | 53,013.35 | 16,436.06 | 61,985.75 | +45,549.69 |
| **4** | 2016-01 a 2021-04 | 64 | 2021-05 a 2022-08 | 16 | 12,340.18 | 67,616.63 | 15,233.67 | 77,917.75 | +62,684.08 |
| **5** | 2016-01 a 2022-08 | 80 | 2022-09 a 2023-12 | 16 | 13,579.16 | 102,764.54 | 16,952.44 | 119,258.91 | +102,306.48 |

### 3.3 Métricas Agregadas de Validación Cruzada

De acuerdo con las mejores prácticas estadísticas, se reporta el desempeño consolidado como **media $\pm$ desviación estándar**:

- **Train MAE:** $13,891.29 \pm 2,335.74\text{ EUR}$
- **Val MAE:** $64,707.41 \pm 24,138.56\text{ EUR}$
- **Train RMSE:** $17,784.19 \pm 3,076.44\text{ EUR}$
- **Val RMSE:** $77,245.96 \pm 26,433.09\text{ EUR}$
- **Brecha Promedio de Generalización (RMSE):** $+59,461.77\text{ EUR}$
- **Brecha Promedio de Generalización (MAE):** $+50,816.12\text{ EUR}$

---

## 4. Análisis de la Curva de Aprendizaje

La curva de aprendizaje formal generada con partición temporal se encuentra almacenada en:  
`data/eval/learning_curve.png`

```
+-----------------------------------------------------------------------------------+
|              TrackFlow — Diagnóstico de Curva de Aprendizaje (5 Folds)            |
|                                                                                   |
|    RMSE (k€)                                                                      |
|      130 |                                                 * [Val RMSE: 119.3k€]  |
|      110 |                                                                        |
|       90 |                        * [Val: 87.2k€]         * [Val: 77.9k€]         |
|       70 |                                 * [Val: 62.0k€]                        |
|       50 |        * [Val: 39.9k€]                                                 |
|       30 |                                                                        |
|       15 |   o---------o-------------------o---------------o-------------o        |
|          |  [Train RMSE estable y bajo: 15k€ - 17k€]                              |
|        0 +-----------------------------------------------------------------       |
|             16m       32m                 48m             64m           80m       |
|                              Tamaño de Entrenamiento (Meses)                      |
+-----------------------------------------------------------------------------------+
```

### 4.1 Interpretación del Patrón Visual
1. **Comportamiento de la Curva de Entrenamiento:**  
   El error de entrenamiento desciende rápidamente de $23.8\text{k EUR}$ a $16.4\text{k EUR}$ en el segundo fold y permanece prácticamente plano y asintótico alrededor de los $15\text{k}-17\text{k EUR}$ RMSE a medida que se incorporan más datos históricos (hasta 80 meses).
2. **Comportamiento de la Curva de Validación:**  
   La curva de validación temporal exhibe valores consistentemente elevados ($39.9\text{k}$ a $119.3\text{k EUR}$ RMSE), sin descender hacia la curva de entrenamiento a medida que crece el número de muestras.
3. **Brecha de Generalización Persistente (Generalization Gap):**  
   Existe una separación amplia y continua entre ambas curvas (promedio $+59.5\text{k EUR}$ en RMSE). Lejos de cerrarse con más datos, la brecha se amplía en el Fold 5 ($+102.3\text{k EUR}$), evidenciando que el modelo memoriza patrones pasados pero pierde capacidad de generalización cuando la serie experimenta crecimiento secular.

---

## 5. Diagnóstico Técnico Formal

| Clasificación Diagnóstica | Justificación Técnica y Evidencia Estadística |
| :---: | :--- |
| **OVERFITTING**<br>*(Sobreajuste / Alta Varianza)* | **Confirmado.** El modelo presenta bajo sesgo (error de entrenamiento muy reducido, $\approx 1.5\%$ de la facturación media mensual) pero alta varianza (error de validación $\approx 4$ a $7$ veces superior). La incapacidad de la curva de validación de aproximarse a la de entrenamiento descarta de forma concluyente el *underfitting* (el cual se caracterizaría por un error de entrenamiento alto y cercano al de validación). |

### Causa Raíz Identificada
1. **Profundidad Excesiva y Nula Regularización para Tamaño Muestral:**  
   El modelo actual utiliza `max_depth=10`, `min_samples_split=2` y `min_samples_leaf=1`. En un dataset tabular de serie temporal de apenas 96 observaciones, estos hiperparámetros permiten a los árboles aislar casi individualmente los meses históricos en hojas puras, capturando el ruido mensual en lugar de la señal macro.
2. **Naturaleza Estática de Árboles ante Crecimiento de Tendencia:**  
   Los árboles de decisión de Random Forest realizan particiones ortogonales del espacio de features. Al no poseer features de rezago autoregresivo (`lag_t`), dependen exclusivamente de la variable `time_step` y funciones armónicas de mes. Cuando la ventana de validación se sitúa en un rango temporal futuro nunca antes visto en entrenamiento, los árboles saturan en la media del último nodo hoja conocido, subestimando sistemáticamente los picos crecientes.

---

## 6. Acción Correctiva Concreta y Plan de Mejora

Para solucionar la causa raíz antes de promover el modelo a staging, se propone una intervención específica en dos etapas:

### 6.1 Regularización Estructural de Hiperparámetros (Inmediata)
Reemplazar la configuración laxa actual por restricciones de complejidad que penalicen la memorización de ruido:

```python
# Configuración Propuesta (Regularizada para Mitigar Overfitting)
regularized_model = RandomForestRegressor(
    n_estimators=150,
    max_depth=5,           # Reducido de 10 a 5: previene aislamiento de meses atípicos
    min_samples_leaf=4,    # Aumentado de 1 a 4: garantiza generalización en nodos terminales
    min_samples_split=6,   # Aumentado de 2 a 6: exige soporte mínimo antes de ramificar
    max_features="sqrt",   # Reduce correlación entre árboles
    random_state=42,
    n_jobs=-1
)
```

### 6.2 Enriquecimiento de Features Autoregresivas (Pipeline de Datos)
Incorporar al módulo `src/pipelines/data_prep.py` variables dinámicas que trasladen la información del nivel reciente de facturación a la predicción:
1. `revenue_lag_12_eur`: Facturación del mismo mes del año anterior (captura estacionalidad interanual).
2. `revenue_rolling_mean_3m_eur`: Media móvil de los 3 meses precedentes (captura el régimen de volumen actual sin depender de una extrapolación de tendencia rígida).

---

## 7. Aprobación y Próximos Pasos

- [x] **Validación Cruzada Temporal Implementada:** TimeSeriesSplit de 5 folds sin barajado ni fuga temporal.
- [x] **Métricas Consolidadas:** MAE y RMSE reportadas como media $\pm$ desviación estándar.
- [x] **Curva de Aprendizaje:** Generada y archivada en `data/eval/learning_curve.png`.
- [x] **Diagnóstico Técnico Formal:** Overfitting / Alta Varianza dictaminado con evidencia empírica.
- [x] **Acción Correctiva:** Especificación técnica detallada de regularización.
- [x] **Tests Automatizados:** Pruebas unitarias en `tests/pipelines/test_temporal_cv.py` passing al 100%.

**Recomendación al CTO (Andrés Kim):**  
Rechazar el paso a staging de la versión con `max_depth=10` / `min_samples_leaf=1`. Aplicar la configuración regularizada indicada en la Sección 6 e integrar la ejecución de `test_temporal_cv.py` en el pipeline de CI/CD.
