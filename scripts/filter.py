def filtrar_por_grado(grafo: dict, percentil: int = 75) -> set:
    grados = {v: len(vecinos) for v, vecinos in grafo.items()}
    num_vertices = len(grados)
    idx = int(percentil / 100 * num_vertices)
    idx = min(idx, num_vertices - 1)
    umbral = sorted(grados.values(), reverse=True)[idx]
    resultado = {v for v, g in grados.items() if g >= umbral}
    print(f"[filtro-grado] umbral={umbral} | conservados: {len(resultado)}/{num_vertices}")
    return resultado


def _gap_combinado(valores: list, conteos: dict, umbral_gap: float):
    """Busca el mejor punto de corte combinando gap de valor y gap de frecuencia."""
    if len(valores) < 2:
        return None, -1

    v_max = valores[0]
    v_min = valores[-1]
    rango = v_max - v_min
    if rango == 0:
        return None, -1

    MIN_GAP_VALOR = 0.10
    MIN_GAP_FREQ  = 1.5

    mejor_score = -1
    mejor_corte = None
    acumulado = conteos.get(valores[0], 0)

    for i in range(len(valores) - 1):
        v_actual   = valores[i]
        v_siguiente = valores[i + 1]
        siguiente_count = conteos.get(v_siguiente, 0)

        gap_valor = (v_actual - v_siguiente) / rango
        gap_freq  = siguiente_count / (acumulado + 1)
        score     = gap_valor + gap_freq

        if gap_valor >= MIN_GAP_VALOR and gap_freq >= MIN_GAP_FREQ and score > mejor_score:
            mejor_score = score
            mejor_corte = v_siguiente

        acumulado += siguiente_count

    if mejor_score >= umbral_gap:
        return mejor_corte, mejor_score
    return None, mejor_score


def filtrar_por_triangulos(grafo: dict, subconjunto: set, umbral_gap: float = 0.5):
    # Calcular triángulos solo dentro del subconjunto
    triangulos = {}
    for v in subconjunto:
        vecinos_sub = grafo[v] & subconjunto
        t = sum(len(grafo[u] & vecinos_sub) for u in vecinos_sub) // 2
        triangulos[v] = t

    valores_unicos = sorted(set(triangulos.values()), reverse=True)
    conteos = {}
    for t in triangulos.values():
        conteos[t] = conteos.get(t, 0) + 1

    corte, score = _gap_combinado(valores_unicos, conteos, umbral_gap)

    if corte is not None:
        resultado = {v for v, t in triangulos.items() if t >= corte}
        print(f"[filtro-triangulos] gap (score={score:.2f}) | umbral_tri={corte} | "
              f"conservados: {len(resultado)}/{len(subconjunto)}")
    else:
        resultado = set(subconjunto)
        print(f"[filtro-triangulos] sin gap significativo | conservados: {len(resultado)}/{len(subconjunto)}")

    return resultado, triangulos


def filtrar_kcore(grafo: dict, vertices_filtrados: set, k: int) -> set:
    candidatos = set(vertices_filtrados)
    while True:
        a_remover = {v for v in candidatos if len(grafo[v] & candidatos) < k}
        if not a_remover:
            break
        candidatos -= a_remover
    print(f"[filtro-kcore] k={k} | conservados: {len(candidatos)}/{len(vertices_filtrados)}")
    return candidatos
