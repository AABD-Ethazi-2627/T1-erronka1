# Comparación de variables de entrada

Se compararon cuatro variantes de Random Forest sobre `data/ai4i2020_train.csv`,
con tres particiones estratificadas, semilla 42, 100 árboles, `class_weight=balanced`
y el umbral de la API (`probabilidad > 0,5`). Las métricas son para la clase fallo;
la matriz de confusión suma las predicciones de las tres particiones de validación.

| Indicadores físicos | `machine_type` | Recall | Precisión | F1 | TN | FP | FN | TP |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| No | No | 0,472 | 0,901 | 0,620 | 7715 | 14 | 143 | 128 |
| No | Sí | 0,395 | 0,899 | 0,549 | 7717 | 12 | 164 | 107 |
| Sí | No | 0,705 | 0,918 | 0,797 | 7712 | 17 | 80 | 191 |
| Sí | Sí | 0,723 | 0,966 | 0,827 | 7722 | 7 | 75 | 196 |

En esta comparación conviene conservar las variables físicas y el tipo de máquina.
No se ha sustituido el modelo desplegado. Esta validación usa el dataset de entrenamiento
y no constituye una evaluación externa; seleccionar variantes con estos resultados y
volver a evaluarlas sobre los mismos datos puede producir una estimación optimista.
Hay que confirmar cualquier cambio con un conjunto de prueba independiente.

Reproducción desde la raíz del proyecto con las dependencias de `scoring`:

```sh
PYTHONPATH=scoring python scoring/evaluate_features.py
```
