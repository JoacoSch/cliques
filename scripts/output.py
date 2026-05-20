import json
import os


def guardar_resultados(ruta_dat, num_vertices, num_aristas, vertices_filtrados,
                       metodo_filtrado, umbral_grado, cliques, tiempo,
                       output_dir, modo, intentos, percentiles_usados):
    nombre_grafo = os.path.basename(ruta_dat)
    base = os.path.splitext(nombre_grafo)[0]
    tamano_max = len(cliques[0]) if cliques else 0

    ruta_txt = os.path.join(output_dir, f"resultado_{base}.txt")
    ruta_json = os.path.join(output_dir, f"resultado_{base}.json")

    with open(ruta_txt, "w") as f:
        f.write(f"Grafo: {nombre_grafo}\n")
        f.write(f"Vértices totales: {num_vertices}\n")
        f.write(f"Aristas totales: {num_aristas}\n")
        f.write(f"Vértices tras filtrado: {len(vertices_filtrados)}  "
                f"(método: {metodo_filtrado}, umbral de grado={umbral_grado})\n")
        f.write(f"Tiempo de ejecución: {tiempo:.2f}s\n")
        f.write(f"\nTamaño de la clique máxima encontrada: {tamano_max}\n\n")
        for idx, clique in enumerate(cliques, 1):
            f.write(f"Clique {idx}: {clique}\n")

    percentil_usado = percentiles_usados[0] if percentiles_usados else None
    es_gap = metodo_filtrado == "gap automático"

    datos = {
        "grafo": nombre_grafo,
        "vertices_totales": num_vertices,
        "aristas_totales": num_aristas,
        "vertices_filtrados": len(vertices_filtrados),
        "metodo_filtrado": "gap_automatico" if es_gap else "percentil",
        "umbral_grado": umbral_grado,
        "percentil_usado": None if es_gap else percentil_usado,
        "tiempo_segundos": round(tiempo, 3),
        "intentos": intentos,
        "percentiles_usados": percentiles_usados,
        "tamano_clique_maxima": tamano_max,
        "modo": modo,
        "cliques": cliques,
    }

    with open(ruta_json, "w") as f:
        json.dump(datos, f, indent=2)

    print(f"[output] guardado en: {ruta_txt} / {ruta_json}")
    return ruta_txt, ruta_json
