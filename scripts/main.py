import argparse
import os
import sys
import time
from datetime import datetime

from loader import cargar_grafo
from filter import filtrar_vertices, filtrar_kcore
from clique_finder import buscar_cliques
from output import guardar_resultados


def main():
    parser = argparse.ArgumentParser(description="Heurística para clique de mayor tamaño")
    parser.add_argument("archivo", help="Ruta al archivo .dat a procesar")
    parser.add_argument("--percentil", type=int, default=75,
                        help="Porcentaje de vértices a conservar en el filtro inicial (default: 75)")
    parser.add_argument("--top-k", type=int, default=5,
                        help="Cantidad de semillas greedy (default: 5)")
    parser.add_argument("--primera", action="store_true",
                        help="Detener al encontrar la primera clique máxima")
    parser.add_argument("--umbral-gap", type=float, default=0.5,
                        help="Score mínimo para aplicar el gap combinado (default: 0.5)")
    parser.add_argument("--factor-reintento", type=float, default=0.3,
                        help="Umbral para detectar resultado sospechoso (default: 0.3)")
    parser.add_argument("--max-reintentos", type=int, default=2,
                        help="Máximo de reintentos con k-core (default: 2)")
    parser.add_argument("--output-dir", default=None,
                        help="Directorio de salida (default: resultados/<nombre_grafo>)")
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

    pool_cliques = []
    mejor_tamano = 0
    metodos_usados = []
    ultimo_metodo = None
    ultimo_umbral = None
    ultimo_filtrado = None
    intentos_realizados = 0
    max_intentos = 1 + args.max_reintentos

    for intento in range(1, max_intentos + 1):
        print(f"\n--- intento {intento}/{max_intentos} ---")

        if intento == 1:
            vertices_filtrados, metodo, umbral = filtrar_vertices(grafo, args.percentil, args.umbral_gap)
        else:
            vertices_filtrados = filtrar_kcore(grafo, ultimo_filtrado, mejor_tamano)
            metodo = f"k-core (k={mejor_tamano})"
            umbral = mejor_tamano

        metodos_usados.append(metodo)
        ultimo_metodo = metodo
        ultimo_umbral = umbral
        ultimo_filtrado = vertices_filtrados
        intentos_realizados = intento

        if not vertices_filtrados:
            print("[aviso] sin vértices tras filtrado, deteniendo.")
            break

        cliques_intento = buscar_cliques(grafo, vertices_filtrados, args.top_k, args.primera)

        tamano_intento = max((len(c) for c in cliques_intento), default=0)
        pool_cliques.extend(cliques_intento)

        indicador = ""
        if tamano_intento > mejor_tamano:
            indicador = "  ← mejoró"
        elif intento == 1 and tamano_intento < umbral * args.factor_reintento:
            indicador = "  ← sospechoso"

        print(f"[intento {intento}/{max_intentos}] método: {metodo} | "
              f"vértices: {len(vertices_filtrados)}/{num_vertices} | "
              f"mejor clique: {tamano_intento}{indicador}")

        tamano_anterior = mejor_tamano
        if tamano_intento > mejor_tamano:
            mejor_tamano = tamano_intento

        if intento == max_intentos:
            break

        if intento == 1:
            sospechoso = tamano_intento < umbral * args.factor_reintento
            if not sospechoso:
                break
        else:
            sin_mejora = tamano_intento <= tamano_anterior
            if sin_mejora:
                break

    # Filtrar pool: solo cliques del tamaño máximo
    cliques_finales = [c for c in pool_cliques if len(c) == mejor_tamano]

    # Deduplicar
    vistas = set()
    cliques_unicas = []
    for c in cliques_finales:
        key = tuple(c)
        if key not in vistas:
            vistas.add(key)
            cliques_unicas.append(c)

    modo = "primera" if args.primera else "todas"
    print(f"\n[resultado] pool total: {len(pool_cliques)} cliques | "
          f"tamaño máximo: {mejor_tamano} | intentos usados: {intentos_realizados}")
    print(f"[resultado] clique máxima: tamaño {mejor_tamano} | cliques encontradas: {len(cliques_unicas)}")

    tiempo = time.time() - t_inicio

    guardar_resultados(
        ruta_dat=ruta,
        num_vertices=num_vertices,
        num_aristas=num_aristas,
        vertices_filtrados=ultimo_filtrado,
        metodo_filtrado=ultimo_metodo,
        umbral_grado=ultimo_umbral,
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
