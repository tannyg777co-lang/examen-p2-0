#!/usr/bin/env python3
"""
cargar_resultados.py - Lee la salida del job MapReduce (part-00000)
y la inserta en la tabla ingresos_categoria_mes de PostgreSQL.

Uso (desde el host):
    docker compose exec api python scripts/cargar_resultados.py
    docker compose exec api python scripts/cargar_resultados.py /ruta/a/part-00000

Formato de cada linea de part-00000:  categoria<TAB>AAAA-MM<TAB>ingreso_total
Usa INSERT ... ON CONFLICT (upsert): se puede correr varias veces sin duplicar.
"""
import os
import sys

import psycopg2

RUTA_DEFECTO = "/data/output/resultado/part-00000"

CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS ingresos_categoria_mes (
    categoria      VARCHAR(20) NOT NULL,
    mes            CHAR(7)     NOT NULL,
    ingreso_total  NUMERIC(16, 2) NOT NULL,
    actualizado    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (categoria, mes)
);
"""

UPSERT = """
INSERT INTO ingresos_categoria_mes (categoria, mes, ingreso_total)
VALUES (%s, %s, %s)
ON CONFLICT (categoria, mes) DO UPDATE
   SET ingreso_total = EXCLUDED.ingreso_total,
       actualizado = NOW();
"""


def leer_resultados(ruta):
    registros = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            partes = linea.strip().split("\t")
            if len(partes) != 3:
                continue
            categoria, mes, ingreso = partes
            registros.append((categoria, mes, float(ingreso)))
    return registros


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA_DEFECTO
    if not os.path.exists(ruta):
        sys.exit(f"No existe {ruta}. Corre primero el job de MapReduce.")

    registros = leer_resultados(ruta)
    if not registros:
        sys.exit(f"{ruta} esta vacio.")

    con = psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
    with con, con.cursor() as cur:
        cur.execute(CREAR_TABLA)
        cur.executemany(UPSERT, registros)
    con.close()

    categorias = sorted({r[0] for r in registros})
    print(f"Cargados {len(registros)} registros desde {ruta}")
    print(f"Categorias ({len(categorias)}): {', '.join(categorias)}")


if __name__ == "__main__":
    main()
