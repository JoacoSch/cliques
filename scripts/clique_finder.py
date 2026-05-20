import random


def _greedy_desde_semilla(grafo: dict, s: int, vertices_filtrados: set, aleatorio: bool = False) -> set:
    candidatos = grafo[s] & vertices_filtrados
    if aleatorio:
        candidatos_ord = random.sample(list(candidatos), len(candidatos))
    else:
        scores = {v: len(grafo[s] & grafo[v]) for v in candidatos}
        candidatos_ord = sorted(candidatos, key=lambda v: scores[v], reverse=True)

    clique = {s}
    for v in candidatos_ord:
        if all(v in grafo[u] for u in clique):
            clique.add(v)
    return clique


def _perturbar(grafo: dict, clique: set, vertices_filtrados: set, rondas: int) -> set:
    mejor = set(clique)
    for _ in range(rondas):
        if not mejor:
            break
        v_sacar = random.choice(list(mejor))
        candidatos = set(mejor) - {v_sacar}

        # vecinos comunes de todos los miembros restantes
        vecinos_comunes = set(vertices_filtrados)
        for u in candidatos:
            vecinos_comunes &= grafo[u]
        vecinos_comunes -= candidatos
        vecinos_comunes.discard(v_sacar)

        scores = {v: len(grafo[v] & candidatos) for v in vecinos_comunes}
        for v in sorted(vecinos_comunes, key=lambda v: scores[v], reverse=True):
            if all(v in grafo[u] for u in candidatos):
                candidatos.add(v)

        if len(candidatos) > len(mejor):
            mejor = candidatos
    return mejor


def buscar_cliques(grafo: dict, vertices_filtrados: set, top_k: int = 5,
                   primera: bool = False, todas_semillas: bool = False,
                   rondas_random: int = 0, rondas_perturbacion: int = 5) -> list:
    grados_filtrados = {v: len(grafo[v]) for v in vertices_filtrados}

    semillas = sorted(grados_filtrados, key=lambda v: grados_filtrados[v], reverse=True)
    if not todas_semillas:
        semillas = semillas[:top_k]

    mejor_tamano = 0
    cliques_maximas = []

    for i, s in enumerate(semillas):
        # Greedy determinístico
        clique = _greedy_desde_semilla(grafo, s, vertices_filtrados, aleatorio=False)

        # Rondas con orden aleatorio de candidatos
        for _ in range(rondas_random):
            c = _greedy_desde_semilla(grafo, s, vertices_filtrados, aleatorio=True)
            if len(c) > len(clique):
                clique = c

        # Perturbación desde la mejor clique de esta semilla
        if rondas_perturbacion > 0:
            clique = _perturbar(grafo, clique, vertices_filtrados, rondas_perturbacion)

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

        if primera and mejor_tamano > 0:
            break

    return cliques_maximas
