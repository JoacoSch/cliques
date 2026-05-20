def buscar_cliques(grafo: dict, vertices_filtrados: set, top_k: int = 5, primera: bool = False):
    grados_filtrados = {v: len(grafo[v]) for v in vertices_filtrados}
    semillas = sorted(grados_filtrados, key=lambda v: grados_filtrados[v], reverse=True)[:top_k]

    mejor_tamano = 0
    cliques_maximas = []

    for i, s in enumerate(semillas):
        candidatos = grafo[s] & vertices_filtrados

        scores = {v: len(grafo[s] & grafo[v]) for v in candidatos}
        candidatos_ord = sorted(candidatos, key=lambda v: scores[v], reverse=True)

        clique = {s}
        for v in candidatos_ord:
            if all(v in grafo[u] for u in clique):
                clique.add(v)

        tamano = len(clique)
        indicador = ""

        if tamano > mejor_tamano:
            mejor_tamano = tamano
            cliques_maximas = [sorted(clique)]
            indicador = "  ← nueva mejor"
        elif tamano == mejor_tamano and tamano > 0:
            cliques_maximas.append(sorted(clique))

        print(f"[semilla {i+1}/{len(semillas)}] vértice={s}, grado={grados_filtrados[s]} "
              f"→ clique: tamaño {tamano}{indicador}")

        if primera and tamano >= mejor_tamano and mejor_tamano > 0:
            break

    return cliques_maximas
