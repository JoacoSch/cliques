# Heurística para Clique de Mayor Tamaño

Implementación desde cero en Python de una heurística multi-etapa para encontrar la clique máxima en grafos aleatorios de hasta 1000 vértices.

---

## El problema

Una **clique** en un grafo no dirigido es un subconjunto de vértices donde todos los pares están conectados entre sí. Encontrar la clique de mayor tamaño (Maximum Clique Problem) es NP-hard: no se conoce algoritmo eficiente exacto para grafos grandes. Los algoritmos exactos como Bron-Kerbosch pueden tardar horas en grafos densos de 900+ vértices.

Este proyecto implementa una **heurística greedy con búsqueda local** que llega a 1-2 vértices del óptimo teórico en segundos.

---

## Diseño del algoritmo

### Intuición central

Un vértice con muchas conexiones no es necesariamente útil: si sus vecinos no se conectan entre sí, nunca formarán una clique grande. La señal correcta es la **densidad local** — cuántas aristas hay dentro de la vecindad de un vértice. Esto se mide con el **conteo de triángulos**.

### Pipeline en cuatro etapas

#### Etapa 1 — Filtro por grado (barato, O(N))
Eliminar el 25% de vértices con menor grado. El grado global es una aproximación gruesa pero barata: vértices con poquísimas conexiones difícilmente pertenecen a la clique máxima. Se conserva el top 75% (configurable con `--percentil`).

#### Etapa 2 — Filtro por triángulos (sobre el subconjunto reducido)
Para cada vértice `v` del subconjunto, contar los triángulos en su vecindad:
```
triangulos(v) = |{ (u,w) : u,w ∈ vecinos(v) ∩ subconjunto, u–w ∈ E }|
```
Se busca un **gap combinado** en la distribución de triángulos: un punto de corte donde simultáneamente haya un salto grande en valor (`gap_valor ≥ 10% del rango`) y un salto grande en cantidad de vértices nuevos que se incorporarían (`gap_frecuencia ≥ 1.5×`). Si no hay gap significativo, se mantienen todos los vértices del subconjunto sin corte adicional.

Esta etapa es cara (O(D²) por vértice) pero se ejecuta sobre el conjunto ya reducido en la etapa 1.

#### Etapa 3 — Búsqueda greedy multi-arranque
Desde cada semilla `s` (top `--top-k-pct`% del conjunto filtrado por grado):
1. `candidatos = vecinos(s) ∩ conjunto_filtrado`
2. Ordenar candidatos por `score(v) = |vecinos(s) ∩ vecinos(v)|` (vecindad común con la semilla)
3. Construir la clique incrementalmente: agregar `v` si es vecino de todos los miembros actuales

Opcionalmente, por cada semilla también se ejecutan rondas con **orden aleatorio** de candidatos (`--rondas-random`), acumulando en el pool si mejoran.

Luego, **perturbación local** desde la mejor clique de cada semilla (`--rondas-perturbacion`):
- Sacar un vértice al azar
- Calcular vecinos comunes de los restantes
- Intentar agregar otros vértices al conjunto expandido
- Si mejora, actualizar

#### Etapa 4 — k-core progresivo
Si la búsqueda encontró una clique de tamaño `k`, todo vértice candidato necesita al menos `k` vecinos dentro del conjunto para poder pertenecer a una clique de ese tamaño. Se aplica **k-core**: eliminar iterativamente vértices con menos de `k` vecinos en el conjunto, hasta estabilización. Si el conjunto se reduce, se relanza la búsqueda (hasta `--max-reintentos`).

### Diseño del top-k relativo

El porcentaje de semillas usadas es relativo al conjunto filtrado (`--top-k-pct`, default 10%). Esto evita la asimetría de un número fijo: con top-k=5 se cubría el 42% del conjunto en grafos pequeños pero solo el 0.7% en grafos de 1000 vértices. El 10% relativo logra la misma calidad que `--todas-semillas` en la mayoría de los casos a la mitad del tiempo.

---

## Arquitectura

```
scripts/
├── main.py          → CLI, orquesta el pipeline y reporta tiempos
├── loader.py        → lee el .dat, construye grafo como dict[int, set[int]]
├── filter.py        → filtrado por grado, triángulos, k-core
├── clique_finder.py → búsqueda greedy + perturbación
└── output.py        → escribe .txt y .json en resultados/<grafo>/<timestamp>/

data/
└── *.dat            → 18 grafos: test.15, graph.{200,500,700,750,800,900,1000}.{02-06}

resultados/          → output por grafo, separado por timestamp
BITACORA.md          → changelog completo con resultados por versión
```

### Formato de los archivos `.dat`

- Una arista por línea, separada por tabulación: `u\tv`
- Vértices numerados desde 0
- Sin cabecera, sin pesos, sin auto-loops

---

## Uso

```bash
cd /ruta/al/proyecto
source .venv/bin/activate
python scripts/main.py data/<archivo.dat> [opciones]
```

### Flags

| Flag | Default | Descripción |
|---|---|---|
| `--percentil INT` | 75 | Conservar top X% por grado en etapa 1 |
| `--umbral-gap FLOAT` | 0.5 | Score mínimo para activar el gap de triángulos |
| `--top-k-pct FLOAT` | 10.0 | % del conjunto filtrado a usar como semillas |
| `--todas-semillas` | — | Usar todos los vértices como semilla |
| `--primera` | — | Detener al encontrar la primera clique máxima |
| `--rondas-random INT` | 0 | Rondas con orden aleatorio de candidatos por semilla |
| `--rondas-perturbacion INT` | 5 | Rondas de perturbación desde la mejor clique |
| `--max-reintentos INT` | 2 | Reintentos con k-core tras cada mejora |
| `--output-dir DIR` | auto | Directorio de salida (default: `resultados/<grafo>/<timestamp>/`) |

### Ejemplos

```bash
# Grafo pequeño, búsqueda rápida
python scripts/main.py data/test.15.dat --primera

# Búsqueda equilibrada (default)
python scripts/main.py data/graph.800.05.dat

# Búsqueda exhaustiva: todas las semillas + randomización + más perturbación
python scripts/main.py data/graph.1000.05.dat --todas-semillas --rondas-random 3 --rondas-perturbacion 10

# Correr todos los grafos
for f in data/*.dat; do python scripts/main.py "$f"; done
```

---

## Resultados

Comparación contra la cota teórica `k_teo`: el mayor `k` tal que el número esperado de cliques de tamaño `k` en G(n,p) es ≥ 1.

| Grafo | n | p | k_teo | Encontrado | Δ | Tiempo |
|---|---|---|---|---|---|---|
| test.15 | 15 | 0.40 | 4 | 4 | 0 | 0.00s |
| graph.200.02 | 200 | 0.20 | 6 | 6 | 0 | 0.02s |
| graph.200.03 | 200 | 0.30 | 7 | 7 | 0 | 0.03s |
| graph.200.04 | 200 | 0.40 | 9 | 9 | 0 | 0.05s |
| graph.200.05 | 200 | 0.50 | 11 | 11 | 0 | 0.07s |
| graph.500.03 | 500 | 0.30 | 8 | 8 | 0 | 0.28s |
| graph.500.04 | 500 | 0.35 | 9 | 9 | 0 | 0.37s |
| graph.700.03 | 700 | 0.26 | 8 | 8 | 0 | 0.61s |
| graph.750.03 | 750 | 0.24 | 8 | 8 | 0 | 0.61s |
| graph.800.02 | 800 | 0.20 | 7 | 7 | 0 | 0.55s |
| graph.800.03 | 800 | 0.23 | 8 | 7 | -1 | 0.66s |
| graph.800.04 | 800 | 0.40 | 11 | 11 | 0 | 1.93s |
| graph.800.05 | 800 | 0.50 | 14 | 14 | 0 | 2.95s |
| graph.900.04 | 900 | 0.40 | 12 | 11 | -1 | 2.63s |
| graph.900.05 | 900 | 0.50 | 15 | 13 | -2 | 4.35s |
| graph.900.06 | 900 | 0.60 | 19 | 17 | -2 | 6.52s |
| graph.1000.04 | 1000 | 0.40 | 12 | 11 | -1 | 3.50s |
| graph.1000.05 | 1000 | 0.50 | 15 | 13 | -2 | 5.56s |

- **67% de los grafos (12/18):** clique óptima teórica encontrada exactamente
- **22% (4/18):** 1 vértice abajo del óptimo
- **11% (2/18):** 2 vértices abajo — grafos más grandes y densos donde la clique óptima es estadísticamente rara (E[X_k] ≈ 3–10)

Los casos con Δ=-2 son grafos donde la clique máxima existe en pocas copias esperadas y requiere recorrido exhaustivo del espacio de búsqueda para garantizarse. Algoritmos exactos como Bron-Kerbosch con podas avanzadas encuentran el óptimo pero pueden tardar horas en grafos densos de 1000 vértices. Esta heurística llega a 1-2 vértices del óptimo en segundos.

---

## Restricciones de implementación

- Sin librerías externas de grafos (`networkx`, `igraph`, etc.)
- Solo biblioteca estándar de Python: `argparse`, `json`, `os`, `sys`, `collections`, `time`, `random`
- Python 3.8+
