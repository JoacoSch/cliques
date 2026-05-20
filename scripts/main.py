import argparse
import os
import sys
import time
from datetime import datetime

from loader import cargar_grafo
from filter import filtrar_por_grado, filtrar_por_triangulos, filtrar_kcore
from clique_finder import buscar_cliques
from output import guardar_resultados


def main():
    parser = argparse.ArgumentParser(description="Heurística para clique de mayor tamaño")
    parser.add_argument("archivo", help="Ruta al archivo .dat a procesar")
    parser.add_argument("--percentil", type=int, default=75,
                        help="Porcentaje de vértices a conservar en el filtro por grado (default: 75)")
    parser.add_argument("--umbral-gap", type=float, default=0.5,
                        help="Score mínimo para aplicar el gap combinado en triángulos (default: 0.5)")
    parser.add_argument("--top-k-pct", type=float, default=10.0,
                        help="Porcentaje del conjunto filtrado a usar como semillas (default: 10.0)")
    parser.add_argument("--todas-semillas", action="store_true",
                        help="Usar todos los vértices filtrados como semilla (ignora --top-k-pct)")
    parser.add_argument("--primera", action="store_true",
                        help="Detener al encontrar la primera clique máxima")
    parser.add_argument("--rondas-random", type=int, default=0,
                        help="Rondas con orden aleatorio de candidatos por semilla (default: 0)")
    parser.add_argument("--rondas-perturbacion", type=int, default=5,
                        help="Rondas de perturbación desde la mejor clique por semilla (default: 5)")
    parser.add_argument("--max-reintentos", type=int, default=2,
                        help="Máximo de reintentos con k-core tras mejora (default: 2)")
    parser.add_argument("--output-dir", default=None,
                        help="Directorio de salida (default: resultados/<nombre_grafo>/<timestamp>)")
    args = parser.parse_args()

    ruta = args.archivo
    if not os.path.isfile(ruta):
        print(f"Error: no se encontró el archivo '{ruta}'", file=sys.stderr)
        sys.exit(1)

    nombre_base = os.path.splitext(os.path.basename(ruta))[0]
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or os.path.join(raiz, "resultados", nombre_base, timestamp)
    os.makedirs(output_dir, exist_ok=True)

    t_inicio = time.time()

    print(f"[carga] leyendo {ruta} ...")
    grafo, num_vertices, num_aristas = cargar_grafo(ruta)
    print(f"[carga] vértices: {num_vertices} | aristas: {num_aristas}")

    # Etapa 1: filtro por grado (barato)
    print("\n[filtrado etapa 1 — grado]")
    por_grado = filtrar_por_grado(grafo, args.percentil)

    # Etapa 2: filtro por triángulos (sobre el subconjunto reducido)
    print("[filtrado etapa 2 — triángulos]")
    vertices_filtrados, triangulos = filtrar_por_triangulos(grafo, por_grado, args.umbral_gap)

    pool_cliques = []
    mejor_tamano = 0
    metodos_usados = ["grado+triangulos"]
    intentos_realizados = 0

    for intento in range(1, args.max_reintentos + 2):
        print(f"\n--- búsqueda {intento} | vértices: {len(vertices_filtrados)}/{num_vertices} ---")
        intentos_realizados = intento

        if not vertices_filtrados:
            print("[aviso] conjunto filtrado vacío, deteniendo.")
            break

        top_k = max(1, int(args.top_k_pct / 100 * len(vertices_filtrados)))
        print(f"[semillas] {top_k} ({args.top_k_pct:.0f}% de {len(vertices_filtrados)})"
              if not args.todas_semillas else f"[semillas] todas ({len(vertices_filtrados)})")

        cliques_intento = buscar_cliques(
            grafo, vertices_filtrados,
            top_k=top_k,
            primera=args.primera,
            todas_semillas=args.todas_semillas,
            rondas_random=args.rondas_random,
            rondas_perturbacion=args.rondas_perturbacion,
        )

        tamano_intento = max((len(c) for c in cliques_intento), default=0)
        pool_cliques.extend(cliques_intento)

        mejoro = tamano_intento > mejor_tamano
        if mejoro:
            mejor_tamano = tamano_intento
            print(f"[búsqueda {intento}] mejor clique: {tamano_intento}  ← mejoró")
        else:
            print(f"[búsqueda {intento}] mejor clique: {tamano_intento}  (sin mejora)")

        if intento > args.max_reintentos:
            break

        if not mejoro:
            break

        # k-core con el nuevo mejor tamaño
        print(f"[filtrado k-core tras mejora]")
        nuevo_filtrado = filtrar_kcore(grafo, vertices_filtrados, mejor_tamano)
        if len(nuevo_filtrado) == len(vertices_filtrados) or not nuevo_filtrado:
            print("[aviso] k-core no redujo el conjunto, deteniendo reintentos.")
            break
        vertices_filtrados = nuevo_filtrado
        metodos_usados.append(f"k-core(k={mejor_tamano})")

    # Filtrar pool y deduplicar
    cliques_finales = [c for c in pool_cliques if len(c) == mejor_tamano]
    vistas = set()
    cliques_unicas = []
    for c in cliques_finales:
        key = tuple(c)
        if key not in vistas:
            vistas.add(key)
            cliques_unicas.append(c)

    modo = "primera" if args.primera else "todas"
    print(f"\n[resultado] pool total: {len(pool_cliques)} cliques | "
          f"tamaño máximo: {mejor_tamano} | búsquedas: {intentos_realizados}")
    print(f"[resultado] clique máxima: tamaño {mejor_tamano} | cliques únicas: {len(cliques_unicas)}")

    tiempo = time.time() - t_inicio

    guardar_resultados(
        ruta_dat=ruta,
        num_vertices=num_vertices,
        num_aristas=num_aristas,
        vertices_filtrados=vertices_filtrados,
        metodo_filtrado="+".join(metodos_usados),
        umbral_grado=args.percentil,
        cliques=cliques_unicas,
        tiempo=tiempo,
        output_dir=output_dir,
        modo=modo,
        intentos=intentos_realizados,
        percentiles_usados=metodos_usados,
    )

    print(f"[tiempo] total: {tiempo:.2f}s")


if __name__ == "__main__":
    main()
