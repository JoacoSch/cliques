# CLAUDE.md — Heurística para Clique de Mayor Tamaño

## ⚠️ Reglas de desarrollo — LEER ANTES DE ESCRIBIR CÓDIGO

1. **No usar librerías externas de grafos.** Prohibido usar `networkx`, `igraph`, `graph-tool` o cualquier librería que resuelva problemas de grafos. Toda la lógica se implementa desde cero con estructuras nativas de Python (`dict`, `set`, `list`).
2. **No usar algoritmos de clique ya implementados.** No importar ni adaptar implementaciones externas de ningún tipo. La única heurística permitida es la descripta en este documento.
3. **No usar datos externos.** El programa opera exclusivamente sobre los archivos `.dat` del repositorio. Sin requests de red, sin archivos fuera del proyecto, sin datasets externos.
4. **Dependencias permitidas:** únicamente librería estándar de Python: `argparse`, `json`, `os`, `sys`, `collections`, `time`. Nada más.
5. **Python 3.8+**

---

## Formato de los archivos `.dat` — verificado en los 18 archivos del repo

| Característica         | Valor confirmado                          |
|------------------------|-------------------------------------------|
| Separador              | **Tabulación** (`\t`) en todos los archivos |
| Header / comentarios   | **Ninguno** — el archivo empieza directo con aristas |
| Vértices               | **Enteros base 0** (`0..N-1`) en todos los archivos |
| Dirección              | No dirigido — cada línea `u\tv` vale en ambos sentidos |
| Pesos                  | Sin pesos |
| Auto-loops             | No presentes, pero ignorar `u == v` por las dudas |
| Tamaños disponibles    | 15, 200, 500, 700, 750, 800, 900, 1000 vértices |

> **Nota sobre el README del repo:** indica que los vértices empiezan en `1`, pero la inspección de los 18 archivos confirma que todos empiezan en `0`. Usar base `0`.

**Ejemplo real — primeras líneas de `test_15.dat` (15 vértices, 42 aristas):**
```
0	13
2	4
5	8
6	11
9	14
7	8
```

**Ejemplo real — primeras líneas de `graph_200_02.dat` (200 vértices, 3980 aristas):**
```
148	160
29	47
53	115
91	161
```

**Estadísticas de grado por tamaño de grafo (referencia para calibrar filtros):**

| Archivo              | Vértices | Aristas  | Grado mín | Grado máx | Grado prom |
|----------------------|----------|----------|-----------|-----------|------------|
| test_15.dat          | 15       | 42       | —         | —         | —          |
| graph_200_02.dat     | 200      | 3.980    | 28        | 60        | 39.8       |
| graph_1000_04.dat    | 1.000    | 199.800  | 353       | 452       | 399.6      |

Los grafos son **scale-free**: pocos vértices concentran muchas conexiones, la mayoría tiene pocas.

---

## Arquitectura del programa

```
main.py            → entrada CLI, orquesta los pasos y reporta tiempos
loader.py          → lee el .dat y construye el grafo en memoria
filter.py          → ranking y filtrado adaptativo de vértices
clique_finder.py   → búsqueda greedy + vecindad común
output.py          → escribe resultados en .txt y .json
```

---

## Paso 1 — Carga del grafo (`loader.py`)

- Leer el archivo `.dat` línea por línea.
- Parsear cada línea como `u, v = line.strip().split()` y convertir a `int`.
- Ignorar líneas vacías y líneas donde `u == v`.
- Construir un **diccionario de adyacencia** con `set` como valores:
  ```python
  grafo[u].add(v)
  grafo[v].add(u)   # no dirigido: agregar ambas direcciones
  ```
- Devolver:
  - `grafo`: `dict[int, set[int]]`
  - `num_vertices`: cantidad de vértices únicos
  - `num_aristas`: cantidad de líneas válidas leídas

---

## Paso 2 — Ranking y filtrado adaptativo (`filter.py`)

### 2a. Calcular grado de cada vértice
```python
grados[v] = len(grafo[v])
```

### 2b. Ordenar por grado descendente
```python
ranking = sorted(grados.items(), key=lambda x: x[1], reverse=True)
# → [(vertice, grado), ...]
```

### 2c. Filtrado adaptativo por gap en la distribución

El umbral se detecta automáticamente buscando el salto más grande en la distribución de grados:

1. Tomar los valores de grado únicos, ordenados de **mayor a menor**.
2. Considerar solo la **mitad superior** (ignorar el 50% de menor grado) para que el gap no se distorsione por la masa de vértices de bajo grado.
3. Calcular las diferencias (`gaps`) entre grados consecutivos dentro de esa mitad superior.
4. Si el gap máximo es **≥ 20% del rango total de grados del grafo**, considerarlo significativo.
5. El umbral de corte = grado mínimo del grupo por encima de ese gap.
6. Conservar todos los vértices con `grado >= umbral`.

**Parámetro de respaldo `--percentil` (default: 85):**
- Activar si no se detecta gap significativo (gap máximo < 20% del rango total).
- `--percentil 90` conserva el 10% de vértices con mayor grado.
- `--percentil 85` conserva el 15% de vértices con mayor grado.

**Logging obligatorio en consola:**
```
[filtrado] método: gap automático | umbral de grado: 45 | vértices conservados: 38 / 200
[filtrado] método: percentil=85   | umbral de grado: 32 | vértices conservados: 30 / 200
```

---

## Paso 3 — Búsqueda de clique (`clique_finder.py`)

### Estrategia: Greedy multi-arranque + vecindad común

#### Parámetro `--top-k` (default: 5)
Repetir la búsqueda completa desde los `k` vértices de mayor grado del subgrafo filtrado. Conservar la mejor clique encontrada al final.

---

#### Para cada vértice semilla `s` en top-k:

**Fase 1 — Candidatos iniciales**
1. `candidatos = grafo[s] ∩ vertices_filtrados`
   (vecinos de `s` que pasaron el filtro de grado)
2. Reducir `candidatos` a los que son vecinos entre sí:
   ```python
   for v in list(candidatos):
       candidatos &= grafo[v]
   ```
   Resultado: conjunto donde todos se conocen mutuamente con `s`.

**Fase 2 — Construcción incremental por vecindad común**
1. Calcular score de cada candidato: `score(v) = |grafo[s] ∩ grafo[v]|`
2. Ordenar `candidatos` por score descendente.
3. Construir la clique incrementalmente:
   ```
   clique = {s}
   para cada v en candidatos (ordenado por score):
       si v ∈ grafo[u] para todo u ∈ clique:
           clique.add(v)
   ```
   La verificación es incremental: solo chequear el nuevo vértice contra los ya en `clique`.

---

#### Selección del resultado

- **Modo por defecto (sin flags):** ejecutar desde todos los top-k semillas y reportar **todas las cliques que alcancen el tamaño máximo encontrado**.
- **Modo `--primera`:** detener al encontrar la primera clique máxima y no continuar. Para grafos grandes donde el tiempo de ejecución importa.

La elección entre modos se hace **manualmente** pasando o no el flag `--primera`.

---

## Paso 3b — Loop de validación con umbral adaptativo (`main.py`)

Este mecanismo detecta cuando el filtro fue demasiado agresivo y reintenta automáticamente bajando el umbral.

### Acumulación de cliques entre intentos

**Las cliques encontradas nunca se descartan.** Cada intento agrega sus cliques al pool global:

```python
pool_cliques = []   # todas las cliques encontradas en todos los intentos
mejor_tamaño = 0

por cada intento:
    cliques_intento = buscar_cliques(grafo, vertices_filtrados)
    pool_cliques.extend(cliques_intento)
    if max(len(c) for c in cliques_intento) > mejor_tamaño:
        mejor_tamaño = max(len(c) for c in cliques_intento)
```

Al final, el resultado es el subconjunto de `pool_cliques` con `len(c) == mejor_tamaño`, independientemente de en qué intento se encontró.

### Criterio para reintentar — Opción A: comparar con el umbral

Si el mejor tamaño encontrado es sospechosamente pequeño dado el umbral de grado usado, el filtro fue probablemente demasiado agresivo. La heurística: en una clique, todos sus miembros se conectan entre sí, por lo que el grado mínimo de cualquier miembro dentro de la clique es `tamaño - 1`. Si el tamaño encontrado es mucho menor al umbral de grado, algo falló.

```python
if mejor_tamaño < umbral_grado_actual * factor_reintento:
    # el resultado es sospechoso → bajar umbral y reintentar
```

Parámetro `--factor-reintento FLOAT` (default: `0.3`). Ejemplo con default:
- umbral=40, clique encontrada=3 → `3 < 40 * 0.3 = 12` → **reintentar**
- umbral=40, clique encontrada=15 → `15 < 12` es falso → **resultado aceptable**

### Criterio para parar — Opción B: sin mejora entre intentos

Si bajar el umbral no produjo una clique más grande que la ya conocida, seguir bajando no va a ayudar.

```python
if mejor_tamaño_nuevo <= mejor_tamaño_anterior:
    break   # bajar el umbral no mejoró nada, parar
```

### Cuánto bajar el umbral en cada reintento

En cada reintento, bajar el percentil de corte en **10 puntos** (ej: 85 → 75 → 65). Esto amplía gradualmente el conjunto de candidatos sin abrir el grafo completo de golpe.

### Límite de reintentos

Parámetro `--max-reintentos INT` (default: `2`). Evita loops infinitos en grafos donde el resultado genuinamente no mejora.

### Flujo completo

```
intento 1: filtrar con percentil P → buscar cliques → tamaño T1
  ¿T1 < umbral * factor?
    NO  → resultado aceptable, terminar
    SÍ  → reintentar con percentil P-10

intento 2: filtrar con percentil P-10 → buscar cliques → acumular en pool → tamaño T2
  ¿T2 > T1?
    NO  → bajar el umbral no ayudó, terminar con lo acumulado
    SÍ  → ¿llegamos a max-reintentos?
            SÍ → terminar con lo acumulado
            NO → reintentar con percentil P-20

resultado final: todas las cliques del pool con tamaño == max(T1, T2, ...)
```

### Logging obligatorio por intento

```
[intento 1/3] umbral=percentil 85 → grado>=45 | vértices: 38/200 | mejor clique: 3  ← sospechoso
[intento 2/3] umbral=percentil 75 → grado>=38 | vértices: 52/200 | mejor clique: 6  ← mejoró
[resultado]   pool total: 8 cliques | tamaño máximo: 6 | intentos usados: 2
```

---

## Paso 4 — Output (`output.py`)

Guardar dos archivos en `--output-dir` (default: mismo directorio que el `.dat` procesado).

### `resultado_<nombre_grafo>.txt`
```
Grafo: graph_200_02.dat
Vértices totales: 200
Aristas totales: 3980
Vértices tras filtrado: 38  (método: gap automático, umbral de grado=45)
Tiempo de ejecución: 0.42s

Tamaño de la clique máxima encontrada: 6

Clique 1: [12, 45, 67, 89, 102, 134]
Clique 2: [12, 45, 67, 89, 102, 155]
```

### `resultado_<nombre_grafo>.json`
```json
{
  "grafo": "graph_200_02.dat",
  "vertices_totales": 200,
  "aristas_totales": 3980,
  "vertices_filtrados": 38,
  "metodo_filtrado": "gap_automatico",
  "umbral_grado": 45,
  "percentil_usado": null,
  "tiempo_segundos": 0.42,
  "intentos": 2,
  "percentiles_usados": [85, 75],
  "tamano_clique_maxima": 6,
  "modo": "todas",
  "cliques": [
    [12, 45, 67, 89, 102, 134],
    [12, 45, 67, 89, 102, 155]
  ]
}
```

---

## Interfaz de línea de comandos (`main.py`)

```bash
python main.py <archivo.dat> [opciones]

Argumentos posicionales:
  archivo.dat         Ruta al archivo .dat a procesar

Opciones:
  --percentil INT          Percentil de respaldo para el filtrado (default: 85)
  --top-k INT              Cantidad de semillas greedy (default: 5)
  --primera                Detener al encontrar la primera clique máxima.
                           Sin este flag se buscan TODAS las cliques del tamaño máximo.
  --factor-reintento FLOAT Umbral para detectar resultado sospechoso (default: 0.3).
                           Si clique_size < grado_umbral * factor → reintentar
  --max-reintentos INT     Máximo de reintentos bajando el umbral (default: 2)
  --output-dir DIR         Directorio de salida (default: directorio del .dat)
```

**Ejemplos de uso:**
```bash
# Grafo pequeño: buscar todas las cliques máximas
python main.py test_15.dat

# Grafo mediano con percentil manual
python main.py graph_200_02.dat --percentil 90 --top-k 10

# Grafo grande: solo la primera clique
python main.py graph_1000_04.dat --primera --top-k 3
```

---

## Notas de implementación

- Usar **`set` de Python** para todas las operaciones de vecindad. Las intersecciones (`&`) son el núcleo de performance del algoritmo.
- El subgrafo filtrado no necesita reconstruirse: mantener un `set` llamado `vertices_filtrados` y usarlo como máscara sobre el grafo original.
- Imprimir progreso en consola por semilla:
  ```
  [semilla 1/5] vértice=134, grado=52 → clique: tamaño 5
  [semilla 2/5] vértice=89,  grado=48 → clique: tamaño 6  ← nueva mejor
  ```
- Medir y reportar tiempo total al finalizar.
- Al terminar, imprimir en consola un resumen antes de guardar archivos:
  ```
  [resultado] clique máxima: tamaño 6 | cliques encontradas: 2
  [output] guardado en: resultado_graph_200_02.txt / .json
  ```