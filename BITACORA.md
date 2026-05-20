# Bitácora de desarrollo — Heurística de Clique Máxima

---

## v1 — Implementación inicial
**Fecha:** 2026-05-20

### Cambios
- Creación de los 5 módulos: `loader.py`, `filter.py`, `clique_finder.py`, `output.py`, `main.py`
- Pipeline: filtrado por percentil → búsqueda greedy multi-arranque → output `.txt` + `.json`
- Filtrado: por defecto `percentil=85` (conservar top 15% por grado)
- Búsqueda: greedy desde top-k semillas, ordenando candidatos por vecindad común con la semilla
- Loop de reintentos: si resultado sospechoso (`tamaño < umbral * factor`), bajar percentil 10 pts y reintentar

### Fix importante
La Fase 1 del algoritmo original (`candidatos &= grafo[v]` iterativo) vaciaba el conjunto de candidatos porque `v ∉ grafo[v]`. Se eliminó esa pre-reducción; la Fase 2 construye la clique correctamente.

### Resultados (con `--primera`)
| Grafo | Clique |
|---|---|
| test.15 | 3 |
| graph.200.02 | 5 |
| graph.1000.04 | 8 |

---

## v2 — Enfoque menos agresivo + k-core adaptativo
**Fecha:** 2026-05-20

### Motivación
El filtro inicial (percentil=85, top 15%) era demasiado agresivo. Se observó que con más vértices candidatos se encontraban cliques más grandes.

### Cambios
- Default `--percentil` cambiado de 85 → 75 (conservar top 75%)
- Semántica invertida: `percentil=75` ahora significa "conservar el 75%", no "percentil 75 de corte"
- Gap detection: ahora busca sobre la distribución **completa** de grados (antes: solo mitad superior)
- Fallback: si no hay gap significativo → conservar top 75% (antes: top 15%)
- **Reintentos inteligentes**: reemplazar "bajar percentil 10 pts" por `filtrar_kcore(k=mejor_tamaño)`
  - Justificación: si la mejor clique es de tamaño k, todo vértice candidato necesita ≥ k vecinos en el conjunto
- Nueva función `filtrar_kcore(grafo, vertices_filtrados, k)`

### Resultados (con `--primera`)
| Grafo | v1 | v2 | Δ |
|---|---|---|---|
| graph.200.02 | 5 | 6 | +1 |
| graph.1000.04 | 8 | 8 | = |
| graph.1000.05 | — | 11 | — |

---

## v3 — Gap combinado (valor + frecuencia)
**Fecha:** 2026-05-20

### Motivación
El gap solo por diferencia de valores de grado no detecta el caso "5 vértices con grado 4-6 vs 20 con grado 3" cuando la diferencia numérica es pequeña. Se necesita una segunda señal: cuántos vértices *nuevos* agregaría el siguiente nivel respecto a los ya acumulados.

### Cambios
- Nuevo score por punto de corte: `score = gap_valor + gap_frecuencia`
  - `gap_valor = (g_actual - g_siguiente) / rango` ∈ [0,1]
  - `gap_frecuencia = siguiente_count / (acumulado + 1)`
- Ambas señales deben ser no-triviales: `gap_valor ≥ 0.10` AND `gap_frecuencia ≥ 1.5`
- Nuevo parámetro `--umbral-gap FLOAT` (default: 0.5) para el score mínimo
- Output por carpeta con **timestamp** para no pisar resultados anteriores: `resultados/<grafo>/<timestamp>/`

### Observación
En los grafos del repo (distribución de grado uniforme), el gap combinado casi nunca activa — todos usan fallback 75%. El gap solo activó en `test.15`.

### Resultados — todos los grafos (con `--primera`)
| Grafo | Vértices | Clique | Tiempo |
|---|---|---|---|
| test.15 | 15 | 3 | 0.00s |
| graph.200.02 | 200 | 4* | 0.00s |
| graph.200.03 | 200 | 6 | 0.00s |
| graph.200.04 | 200 | 6 | 0.00s |
| graph.200.05 | 200 | 9 | 0.00s |
| graph.500.03 | 500 | 6 | 0.01s |
| graph.500.04 | 500 | 8 | 0.02s |
| graph.700.03 | 700 | 5 | 0.02s |
| graph.750.03 | 750 | 6 | 0.03s |
| graph.800.02 | 800 | 5 | 0.03s |
| graph.800.03 | 800 | 5 | 0.03s |
| graph.800.04 | 800 | 9 | 0.05s |
| graph.800.05 | 800 | 9 | 0.07s |
| graph.900.04 | 900 | 8 | 0.07s |
| graph.900.05 | 900 | 10 | 0.09s |
| graph.900.06 | 900 | 15 | 0.11s |
| graph.1000.04 | 1000 | 8 | 0.09s |
| graph.1000.05 | 1000 | 11 | 0.11s |

*graph.200.02 bajó de 6 a 4 porque se usó `--primera` (para con semilla 1 que encuentra 4; sin `--primera` encuentra 6).

---

## v4 — Filtro en dos etapas (grado → triángulos) + búsqueda exhaustiva
**Fecha:** 2026-05-20

### Motivación
- El grado es una señal débil: un vértice con 50 vecinos sin conexiones entre sí nunca formará una clique grande
- El **conteo de triángulos** mide directamente cuán densa es la vecindad → mejor predictor de potencial de clique
- Calcular triángulos sobre todos los vértices es caro en grafos densos → filtrar primero por grado (barato) y luego por triángulos (sobre el subconjunto ya reducido)
- La búsqueda con top-k=5 semillas dejaba mucho potencial sin explorar

### Cambios en el filtrado
- **Etapa 1** `filtrar_por_grado(grafo, percentil=75)`: corte rápido O(N), elimina el peor 25%
- **Etapa 2** `filtrar_por_triangulos(grafo, subconjunto, umbral_gap)`: calcula triángulos solo en el subconjunto reducido, aplica gap combinado sobre su distribución
- `filtrar_kcore` se aplica progresivamente después de cada mejora en la búsqueda

### Cambios en la búsqueda (`clique_finder.py`)
- **`--todas-semillas`**: usar todos los vértices filtrados como semilla (no solo top-k)
- **`--rondas-random INT`** (default: 0): por cada semilla, repetir la búsqueda greedy R veces con orden aleatorio de candidatos
- **`--rondas-perturbacion INT`** (default: 5): desde la mejor clique de cada semilla, realizar rondas de perturbación (sacar un vértice, intentar agregar otros)

### Resultados comparativos (búsqueda exhaustiva vs. rápida)

| Grafo | Rápido (`--primera`) | Exhaustivo (`--todas-semillas --rondas-random 3 --rondas-perturbacion 10`) |
|---|---|---|
| graph.200.02 | 6 | 6 |
| graph.1000.05 | 11 | **13** |

**Conclusión:** La búsqueda exhaustiva mejora significativamente en grafos grandes. El tiempo escala (5.54s para 1000v exhaustivo vs 0.11s rápido), pero sigue siendo manejable.

---

## v4 — Resultados completos con búsqueda exhaustiva
**Fecha:** 2026-05-20
**Flags:** `--todas-semillas --rondas-random 3 --rondas-perturbacion 10`

| Grafo | Vértices | Clique v3 (rápido) | Clique v4 (exhaustivo) | Δ | Tiempo |
|---|---|---|---|---|---|
| test.15 | 15 | 3 | **4** | +1 | 0.00s |
| graph.200.02 | 200 | 4* | **6** | +2 | 0.02s |
| graph.200.03 | 200 | 6 | **7** | +1 | 0.03s |
| graph.200.04 | 200 | 6 | **9** | +3 | 0.05s |
| graph.200.05 | 200 | 9 | **11** | +2 | 0.07s |
| graph.500.03 | 500 | 6 | **8** | +2 | 0.28s |
| graph.500.04 | 500 | 8 | **9** | +1 | 0.37s |
| graph.700.03 | 700 | 5 | **8** | +3 | 0.61s |
| graph.750.03 | 750 | 6 | **8** | +2 | 0.61s |
| graph.800.02 | 800 | 5 | **7** | +2 | 0.55s |
| graph.800.03 | 800 | 5 | **7** | +2 | 0.66s |
| graph.800.04 | 800 | 9 | **11** | +2 | 1.93s |
| graph.800.05 | 800 | 9 | **14** | +5 | 2.95s |
| graph.900.04 | 900 | 8 | **11** | +3 | 2.63s |
| graph.900.05 | 900 | 10 | **13** | +3 | 4.35s |
| graph.900.06 | 900 | 15 | **17** | +2 | 6.52s |
| graph.1000.04 | 1000 | 8 | **11** | +3 | 3.50s |
| graph.1000.05 | 1000 | 11 | **13** | +2 | 5.56s |

*v3 usaba `--primera`; v4 usa búsqueda exhaustiva completa.

**Mejora promedio:** +2.3 vértices por clique. Todos los grafos mejoraron. Tiempo máximo: 6.52s (graph.900.06).

---

## v5 — Top-k relativo al conjunto filtrado
**Fecha:** 2026-05-20

### Motivación
Con top-k fijo (ej. 5), el porcentaje de semillas probadas varía enormemente: 42% en grafos pequeños, 0.7% en grafos de 1000v. No tiene sentido. Se reemplaza `--top-k INT` por `--top-k-pct FLOAT` (default: 10%), que escala automáticamente con el tamaño del conjunto filtrado.

### Cambio
- `--top-k INT` → `--top-k-pct FLOAT` (default: 10.0)
- `top_k = max(1, int(top_k_pct / 100 * len(vertices_filtrados)))`
- `--todas-semillas` sigue disponible para usar el 100%

### Resultados comparativos (con `--rondas-random 3 --rondas-perturbacion 10`)

| Grafo | top-k=5 (abs) | 10% relativo | todas-semillas | Observación |
|---|---|---|---|---|
| graph.200.02 | 6 / 0.01s | 15 seeds → **6** / 0.01s | 6 / 0.02s | igual |
| graph.800.05 | 12 / 1.14s | 60 seeds → **12** / 1.30s | 13 / 2.99s | 2.3x más rápido, −1 |
| graph.1000.04 | 10 / 1.34s | 75 seeds → **11** / 1.57s | 11 / 3.50s | misma calidad, 2.2x más rápido |
| graph.900.06 | 16 / 2.38s | 70 seeds → **16** / 2.77s | 17 / 6.52s | 2.4x más rápido, −1 |

**Conclusión:** El 10% relativo logra la misma calidad que todas-semillas en la mayoría de los casos, al costo de la mitad del tiempo. Mucho más eficiente que un número fijo.
