#!/usr/bin/env python3
"""
reducer.py - Pregunta 0/1: Ingreso total por categoria y mes.

Entrada (ya ordenada por clave por Hadoop): categoria|AAAA-MM<TAB>ingreso_en_centavos
Salida: categoria<TAB>AAAA-MM<TAB>ingreso_total (en pesos, 2 decimales)

Como Hadoop entrega las claves agrupadas y ordenadas, basta con ir sumando
mientras la clave sea la misma y escribir el total cuando la clave cambia.
"""
import sys


def emitir(clave, centavos):
    categoria, mes = clave.split("|")
    print(f"{categoria}\t{mes}\t{centavos // 100}.{centavos % 100:02d}")


clave_actual = None
suma_actual = 0

for linea in sys.stdin:
    partes = linea.rstrip("\n").split("\t")
    if len(partes) != 2 or "|" not in partes[0]:
        continue
    clave, valor = partes
    try:
        centavos = int(valor)
    except ValueError:
        continue

    if clave == clave_actual:
        suma_actual += centavos
    else:
        if clave_actual is not None:
            emitir(clave_actual, suma_actual)
        clave_actual = clave
        suma_actual = centavos

# ultima clave
if clave_actual is not None:
    emitir(clave_actual, suma_actual)
