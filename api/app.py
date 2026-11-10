"""
API CRUD de DataMart - Ingreso total por categoria y mes (matricula 125054310)

Endpoints:
  GET    /                                -> estado de la API
  GET    /resultados                      -> todos los registros
  GET    /resultados/<categoria>          -> los meses de una categoria (clave de la pregunta)
  GET    /resultados/<categoria>/<mes>    -> un registro (mes en formato AAAA-MM)
  POST   /resultados                      -> crear  {"categoria": "...", "mes": "2026-01", "ingreso_total": 123.45}
  PUT    /resultados/<categoria>/<mes>    -> actualizar ingreso_total
  DELETE /resultados/<categoria>/<mes>    -> borrar
"""
import os
import re
import time

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS ingresos_categoria_mes (
    categoria      VARCHAR(20) NOT NULL,
    mes            CHAR(7)     NOT NULL,          -- AAAA-MM
    ingreso_total  NUMERIC(16, 2) NOT NULL,
    actualizado    TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (categoria, mes)
);
"""

FORMATO_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def conectar():
    return psycopg2.connect(**DB_CONFIG)


def inicializar_bd(intentos=15):
    """Crea la tabla si no existe. Reintenta mientras PostgreSQL arranca."""
    for i in range(1, intentos + 1):
        try:
            con = conectar()
            with con, con.cursor() as cur:
                cur.execute(CREAR_TABLA)
            con.close()
            print("[api] tabla ingresos_categoria_mes lista", flush=True)
            return
        except psycopg2.OperationalError as e:
            print(f"[api] esperando a la base de datos ({i}/{intentos}): {e}", flush=True)
            time.sleep(2)
    raise RuntimeError("No se pudo conectar a la base de datos")


def consultar(sql, params=(), una=False):
    """Abre conexion, ejecuta, hace commit y la cierra (una conexion por peticion)."""
    con = conectar()
    try:
        with con, con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone() if una else cur.fetchall()
    finally:
        con.close()


def a_json(fila):
    return {
        "categoria": fila["categoria"],
        "mes": fila["mes"],
        "ingreso_total": float(fila["ingreso_total"]),
        "actualizado": fila["actualizado"].isoformat() if fila["actualizado"] else None,
    }


def no_encontrado(categoria, mes=None):
    detalle = f"{categoria} {mes}" if mes else categoria
    return jsonify({"error": f"no hay registros para {detalle}"}), 404


@app.get("/")
def inicio():
    return jsonify({"api": "DataMart", "pregunta": "Ingreso total por categoria y mes",
                    "matricula": os.getenv("MATRICULA")})


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------------- READ ----------------
@app.get("/resultados")
def listar():
    filas = consultar("SELECT * FROM ingresos_categoria_mes ORDER BY categoria, mes")
    return jsonify([a_json(f) for f in filas])


@app.get("/resultados/<categoria>")
def por_categoria(categoria):
    # LOWER() para que /resultados/electronica y /resultados/Electronica funcionen igual
    filas = consultar("SELECT * FROM ingresos_categoria_mes "
                      "WHERE LOWER(categoria) = LOWER(%s) ORDER BY mes", (categoria,))
    if not filas:
        return no_encontrado(categoria)
    return jsonify([a_json(f) for f in filas])


@app.get("/resultados/<categoria>/<mes>")
def obtener(categoria, mes):
    fila = consultar("SELECT * FROM ingresos_categoria_mes "
                     "WHERE LOWER(categoria) = LOWER(%s) AND mes = %s",
                     (categoria, mes), una=True)
    if fila is None:
        return no_encontrado(categoria, mes)
    return jsonify(a_json(fila))


# ---------------- CREATE ----------------
@app.post("/resultados")
def crear():
    datos = request.get_json(silent=True) or {}
    categoria = str(datos.get("categoria", "")).strip()
    mes = str(datos.get("mes", "")).strip()
    if not categoria or "ingreso_total" not in datos:
        return jsonify({"error": "se requieren 'categoria', 'mes' e 'ingreso_total'"}), 400
    if not FORMATO_MES.match(mes):
        return jsonify({"error": "'mes' debe tener formato AAAA-MM, por ejemplo 2025-03"}), 400
    try:
        ingreso = float(datos["ingreso_total"])
    except (TypeError, ValueError):
        return jsonify({"error": "ingreso_total debe ser numerico"}), 400
    try:
        fila = consultar(
            "INSERT INTO ingresos_categoria_mes (categoria, mes, ingreso_total) "
            "VALUES (%s, %s, %s) RETURNING *",
            (categoria, mes, ingreso), una=True)
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": f"ya existe {categoria} {mes}, usa PUT"}), 409
    return jsonify(a_json(fila)), 201


# ---------------- UPDATE ----------------
@app.put("/resultados/<categoria>/<mes>")
def actualizar(categoria, mes):
    datos = request.get_json(silent=True) or {}
    try:
        ingreso = float(datos["ingreso_total"])
    except KeyError:
        return jsonify({"error": "envia 'ingreso_total'"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "ingreso_total debe ser numerico"}), 400

    fila = consultar("UPDATE ingresos_categoria_mes SET ingreso_total = %s, actualizado = NOW() "
                     "WHERE LOWER(categoria) = LOWER(%s) AND mes = %s RETURNING *",
                     (ingreso, categoria, mes), una=True)
    if fila is None:
        return no_encontrado(categoria, mes)
    return jsonify(a_json(fila))


# ---------------- DELETE ----------------
@app.delete("/resultados/<categoria>/<mes>")
def borrar(categoria, mes):
    fila = consultar("DELETE FROM ingresos_categoria_mes "
                     "WHERE LOWER(categoria) = LOWER(%s) AND mes = %s RETURNING *",
                     (categoria, mes), una=True)
    if fila is None:
        return no_encontrado(categoria, mes)
    return jsonify({"borrado": a_json(fila)})


if __name__ == "__main__":
    inicializar_bd()
    app.run(host="0.0.0.0", port=5000)
