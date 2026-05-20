def filtrar_vertices(grafo: dict, percentil: int = 85):
    grados = {v: len(vecinos) for v, vecinos in grafo.items()}
    num_vertices = len(grados)

    grado_max = max(grados.values())
    grado_min = min(grados.values())
    rango = grado_max - grado_min

    grados_unicos = sorted(set(grados.values()), reverse=True)
    mitad = max(1, len(grados_unicos) // 2)
    mitad_superior = grados_unicos[:mitad]

    metodo = None
    umbral = None

    if rango > 0 and len(mitad_superior) >= 2:
        gaps = [(mitad_superior[i] - mitad_superior[i + 1], mitad_superior[i + 1])
                for i in range(len(mitad_superior) - 1)]
        max_gap, grado_tras_gap = max(gaps, key=lambda x: x[0])

        if max_gap >= 0.20 * rango:
            umbral = grado_tras_gap
            metodo = "gap automático"

    if metodo is None:
        idx = int((1 - percentil / 100) * num_vertices)
        idx = max(0, min(idx, num_vertices - 1))
        umbral_grado = sorted(grados.values(), reverse=True)[idx]
        umbral = umbral_grado
        metodo = f"percentil={percentil}"

    vertices_filtrados = {v for v, g in grados.items() if g >= umbral}

    print(f"[filtrado] método: {metodo} | umbral de grado: {umbral} | "
          f"vértices conservados: {len(vertices_filtrados)} / {num_vertices}")

    return vertices_filtrados, metodo, umbral
