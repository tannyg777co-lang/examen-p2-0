#!/usr/bin/env python3
"""
mapper.py - Pregunta 0/1: Ingreso total (cantidad x precio_unitario) por categoria y mes.

Entrada (CSV): id,fecha_hora,tienda,categoria,producto,cantidad,precio_unitario,metodo_pago
Salida:        categoria|AAAA-MM<TAB>ingreso_en_centavos

- La clave compuesta "categoria|mes" va unida con '|' para que Hadoop la trate
  como UNA sola clave (Hadoop Streaming toma como clave todo lo anterior al primer TAB).
- El ingreso se emite en CENTAVOS (entero) para que la suma sea exacta
  y coincida al centavo con el script secuencial (los float acumulan error).
- Se ignora el encabezado y cualquier linea mal formada (no truncan el job).
"""
import sys

NUM_CAMPOS = 8

for linea in sys.stdin:
    campos = linea.strip().split(",")

    # Linea vacia o con numero incorrecto de columnas -> se ignora
    if len(campos) != NUM_CAMPOS:
        continue

    # Encabezado del CSV -> se ignora
    if campos[0] == "id":
        continue

    try:
        fecha_hora = campos[1].strip()          # "2025-06-26 17:48:55"
        mes = fecha_hora[:7]                    # "2025-06"
        numero_mes = int(fecha_hora[5:7])
        categoria = campos[3].strip()
        cantidad = int(campos[5])
        precio_centavos = round(float(campos[6]) * 100)
    except ValueError:
        # fecha, cantidad o precio no validos -> linea mal formada
        continue

    if not categoria or fecha_hora[4:5] != "-" or not 1 <= numero_mes <= 12:
        continue

    print(f"{categoria}|{mes}\t{cantidad * precio_centavos}")
