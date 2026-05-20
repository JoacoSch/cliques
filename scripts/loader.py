from collections import defaultdict


def cargar_grafo(ruta: str):
    grafo = defaultdict(set)
    num_aristas = 0

    with open(ruta, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            partes = line.split()
            if len(partes) < 2:
                continue
            u, v = int(partes[0]), int(partes[1])
            if u == v:
                continue
            grafo[u].add(v)
            grafo[v].add(u)
            num_aristas += 1

    num_vertices = len(grafo)
    return dict(grafo), num_vertices, num_aristas
