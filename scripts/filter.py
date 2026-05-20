def filtrar_vertices(grafo: dict, percentil: int = 75, umbral_gap: float = 0.5):
    grados = {v: len(vecinos) for v, vecinos in grafo.items()}
    num_vertices = len(grados)

    grado_max = max(grados.values())
    grado_min = min(grados.values())
    rango = grado_max - grado_min

    grados_unicos = sorted(set(grados.values()), reverse=True)

    metodo = None
    umbral = None

    if rango > 0 and len(grados_unicos) >= 2:
        # histograma: cuántos vértices tienen cada grado
        hist = {}
        for g in grados.values():
            hist[g] = hist.get(g, 0) + 1

        mejor_score = -1
        mejor_corte = None
        mejor_gap_valor = 0.0
        mejor_gap_freq = 0.0

        # señales mínimas para que un corte sea "no trivial"
        MIN_GAP_VALOR = 0.10   # al menos 10% del rango de grados
        MIN_GAP_FREQ  = 1.5    # el siguiente nivel agrega al menos 50% más que lo acumulado

        acumulado = hist.get(grados_unicos[0], 0)
        for i in range(len(grados_unicos) - 1):
            g_actual = grados_unicos[i]
            g_siguiente = grados_unicos[i + 1]
            siguiente_count = hist.get(g_siguiente, 0)

            gap_valor = (g_actual - g_siguiente) / rango
            gap_freq = siguiente_count / (acumulado + 1)
            score = gap_valor + gap_freq

            # ambas señales deben ser no-triviales para considerar este corte
            if gap_valor >= MIN_GAP_VALOR and gap_freq >= MIN_GAP_FREQ and score > mejor_score:
                mejor_score = score
                mejor_corte = g_siguiente
                mejor_gap_valor = gap_valor
                mejor_gap_freq = gap_freq

            acumulado += siguiente_count

        if mejor_score >= umbral_gap:
            umbral = mejor_corte
            metodo = (f"gap combinado (score={mejor_score:.2f}, "
                      f"valor={mejor_gap_valor:.2f}, freq={mejor_gap_freq:.2f})")

    if metodo is None:
        idx = int(percentil / 100 * num_vertices)
        idx = min(idx, num_vertices - 1)
        umbral = sorted(grados.values(), reverse=True)[idx]
        metodo = f"fallback {percentil}%"

    vertices_filtrados = {v for v, g in grados.items() if g >= umbral}

    print(f"[filtrado] método: {metodo} | umbral de grado: {umbral} | "
          f"vértices conservados: {len(vertices_filtrados)} / {num_vertices}")

    return vertices_filtrados, metodo, umbral


def filtrar_kcore(grafo: dict, vertices_filtrados: set, k: int):
    candidatos = set(vertices_filtrados)
    while True:
        a_remover = {v for v in candidatos if len(grafo[v] & candidatos) < k}
        if not a_remover:
            break
        candidatos -= a_remover

    print(f"[filtrado] método: k-core (k={k}) | "
          f"vértices conservados: {len(candidatos)} / {len(vertices_filtrados)}")

    return candidatos
