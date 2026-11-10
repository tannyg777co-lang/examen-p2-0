#!/usr/bin/env python3
"""
secuencial.py - Misma pregunta que el job MapReduce (ingreso total por categoria
y mes), pero en un solo proceso, leyendo el CSV linea por linea (sin pandas,
para no cargar 400 MB en memoria).

Uso:
    time python3 secuencial.py /data/input/ventas_125054310.csv > secuencial.txt
Salida: mismo formato y orden que part-00000 -> categoria<TAB>AAAA-MM<TAB>ingreso_total
"""
import sys
from collections import defaultdict

NUM_CAMPOS = 8


def main(ruta):
    totales = defaultdict(int)  # "categoria|mes" -> centavos
    descartadas = 0

    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            campos = linea.strip().split(",")
            if len(campos) != NUM_CAMPOS or campos[0] == "id":
                continue
            try:
                fecha_hora = campos[1].strip()
                mes = fecha_hora[:7]
                numero_mes = int(fecha_hora[5:7])
                categoria = campos[3].strip()
                cantidad = int(campos[5])
                precio_centavos = round(float(campos[6]) * 100)
            except ValueError:
                descartadas += 1
                continue
            if not categoria or fecha_hora[4:5] != "-" or not 1 <= numero_mes <= 12:
                descartadas += 1
                continue
            totales[f"{categoria}|{mes}"] += cantidad * precio_centavos

    # Mismo orden que Hadoop: por clave (categoria y luego mes)
    for clave in sorted(totales):
        categoria, mes = clave.split("|")
        centavos = totales[clave]
        print(f"{categoria}\t{mes}\t{centavos // 100}.{centavos % 100:02d}")

    print(f"[secuencial] combinaciones categoria-mes: {len(totales)}, "
          f"lineas descartadas: {descartadas}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 secuencial.py <ruta_csv>")
    main(sys.argv[1])
