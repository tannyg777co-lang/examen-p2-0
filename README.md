# Examen Parcial 2 — Pipeline DataMart con Docker, Hadoop y PostgreSQL

| | |
|---|---|
| **Alumna** | Tanny Geraldine Correa Chávez |
| **Matrícula** | 125054310 |
| **Pregunta asignada** (último dígito **0**) | **Ingreso total (cantidad × precio_unitario) por categoría y mes** |
| **Dataset** | `ventas_125054310.csv` — 5,000,000 registros (~336 MB), 10 categorías × 12 meses de 2025 |

## Arquitectura

```
                 red: datamart_net (bridge)
 ┌────────────────────────┐     ┌──────────────┐      ┌────────────────────┐
 │ hadoop                 │     │ db           │      │ api (Flask)        │
 │ Hadoop 3.3.6 standalone│     │ PostgreSQL 16│◄─────│ GET/POST/PUT/DELETE│
 │ OpenSSH Server         │     │ vol: pg_data │      │ puerto ${API_PORT} │
 │ /data/input  (ro) ◄── ./data │              │      │ ssh hadoop@hadoop ─┼──► hadoop:22
 │ /data/output ───────► vol hadoop_output ──────────► │ cargar_resultados  │
 └────────────────────────┘     └──────────────┘      └────────────────────┘
```

1. **hadoop** procesa el CSV con Hadoop Streaming (`mapper.py` / `reducer.py`) y deja `part-00000` en el volumen `hadoop_output`.
2. **api** lee ese archivo con `cargar_resultados.py` y lo inserta en la tabla `ingresos_categoria_mes` de **db**.
3. **api** expone la tabla por HTTP. La base vive en el volumen nombrado `pg_data`, así que persiste.

## Estructura

```
examen-p2-125054310/
├── README.md
├── .gitignore            # *.csv y .env
├── .gitattributes        # fuerza LF (evita errores \r en .sh al clonar en Windows)
├── .env.example
├── docker-compose.yml
├── data/                 # aquí va ventas_125054310.csv (NO se sube)
├── hadoop/
│   ├── Dockerfile
│   └── entrypoint.sh     # genera llaves SSH y arranca sshd
├── mapreduce/
│   ├── mapper.py
│   ├── reducer.py
│   ├── secuencial.py
│   └── run_job.sh        # corre MapReduce + secuencial, mide tiempos y compara
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── scripts/
│   ├── cargar_resultados.py
│   └── generar_dataset.py   # script del examen (Paso 0)
└── evidencias/
```

Reproducir paso a paso
1. Preparar el entorno
bash
cd ruta/del/proyecto
mkdir -p evidencias
cp .env.example .env

Contenido esperado del .env:

MATRICULA=125054310
API_PORT=5000
POSTGRES_DB=datamart
POSTGRES_USER=datamart
POSTGRES_PASSWORD=change-this-password
2. Generar el dataset

Solo si aún no existe data/ventas_125054310.csv:

bash
cd data && python3 ../scripts/generar_dataset.py 125054310 && cd ..
3. Levantar los servicios
bash
docker compose up --build -d
docker compose ps

Esperado: db en healthy, y api y hadoop en Up.

4. Verificar Hadoop y SSH
bash
docker compose exec hadoop hadoop version
docker compose exec -u hadoop hadoop ssh localhost hostname
docker compose exec api ssh hadoop@hadoop hostname
docker compose exec api ssh hadoop@hadoop hadoop version

Esperado: muestra la versión de Hadoop y el hostname sin pedir contraseña.

5. Ejecutar MapReduce, secuencial y comparación
bash
docker compose exec -u hadoop hadoop bash /opt/mapreduce/run_job.sh 2>&1 | tee evidencias/job.log

Esperado en evidencias/job.log:

Job ... completed successfully
Map input records=5000001 y Reduce output records=120
Los tiempos real del job MapReduce y del script secuencial
Al final: OK: MapReduce y secuencial dan exactamente el mismo resultado.

Con un solo equipo (modo local de Hadoop), el secuencial puede ser más rápido que MapReduce. El costo de iniciar la JVM, el shuffle y el ordenamiento pesa más que el cálculo. MapReduce muestra su ventaja con volúmenes mayores y un clúster real.

6. Cargar el resultado a PostgreSQL
bash
docker compose exec api python scripts/cargar_resultados.py

Esperado:

Cargados 120 registros desde /data/output/resultado/part-00000
Categorias (10): Abarrotes, Bebidas, Deportes, Electronica, Farmacia, Hogar, Juguetes, Mascotas, Papeleria, Ropa
7. Consultar la API y el dashboard

Dashboard (usar http://, no https://): http://localhost:5000/dashboard

bash
curl http://localhost:5000/resultados
curl http://localhost:5000/resultados/Electronica
curl http://localhost:5000/resultados/Electronica/2025-03
Método	Ruta	Descripción
GET	/dashboard	Dashboard web
GET	/resultados	Todos los registros
GET	/resultados/<categoria>	Registros de una categoría
GET	/resultados/<categoria>/<mes>	Un registro
POST	/resultados	Crear registro
PUT	/resultados/<categoria>/<mes>	Actualizar ingreso_total
DELETE	/resultados/<categoria>/<mes>	Eliminar registro

Prueba del CRUD:

bash
# Crear
curl -X POST http://localhost:5000/resultados \
  -H "Content-Type: application/json" \
  -d '{"categoria":"Ropa","mes":"2026-01","ingreso_total":123.45}'

# Actualizar
curl -X PUT http://localhost:5000/resultados/Ropa/2026-01 \
  -H "Content-Type: application/json" \
  -d '{"ingreso_total":999.90}'

# Eliminar
curl -X DELETE http://localhost:5000/resultados/Ropa/2026-01

Esperado: el POST devuelve el registro con 123.45, el PUT lo devuelve con 999.9 y el DELETE responde con {"borrado": {...}}.

8. Comprobar la persistencia
bash
docker compose down        # sin -v, para conservar el volumen
docker compose up -d
curl -s http://localhost:5000/resultados | head -c 200

Esperado: los registros siguen apareciendo sin volver a cargar nada.

Detener y limpiar
bash
docker compose down        # detiene, conserva los datos
docker compose down -v     # detiene y borra el volumen de PostgreSQL

## Resultado del job

El job produce 120 líneas (`categoria<TAB>AAAA-MM<TAB>ingreso_total`). Resumen en **millones de pesos**:

| Categoría | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | **Total anual** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Abarrotes | 350.0 | 312.7 | 345.6 | 333.9 | 344.6 | 333.9 | 349.6 | 345.6 | 336.4 | 348.0 | 332.1 | 347.1 | **4,079.6** |
| Bebidas | 346.7 | 310.5 | 348.2 | 334.5 | 345.8 | 336.1 | 347.9 | 347.7 | 331.2 | 346.1 | 336.1 | 346.4 | **4,077.3** |
| Deportes | 344.6 | 315.1 | 346.0 | 337.5 | 343.2 | 334.2 | 343.6 | 346.0 | 333.0 | 346.6 | 336.6 | 346.5 | **4,072.7** |
| Electronica | 346.4 | 313.1 | 349.9 | 331.1 | 345.1 | 334.4 | 343.4 | 348.8 | 335.5 | 347.2 | 336.7 | 345.6 | **4,077.4** |
| Farmacia | 345.0 | 312.0 | 346.2 | 332.7 | 344.9 | 332.2 | 345.6 | 345.7 | 335.1 | 348.8 | 337.1 | 345.8 | **4,071.1** |
| Hogar | 345.7 | 310.5 | 342.4 | 332.7 | 348.0 | 334.0 | 346.3 | 345.1 | 334.4 | 344.3 | 338.6 | 347.4 | **4,069.4** |
| Juguetes | 346.8 | 312.1 | 348.7 | 340.2 | 348.3 | 331.7 | 346.1 | 348.9 | 331.3 | 348.5 | 334.9 | 349.3 | **4,086.9** |
| Mascotas | 345.9 | 314.1 | 345.4 | 336.5 | 347.0 | 336.7 | 343.1 | 345.1 | 334.5 | 346.1 | 333.2 | 347.7 | **4,075.4** |
| Papeleria | 346.7 | 310.1 | 347.6 | 334.1 | 344.5 | 333.1 | 346.1 | 341.2 | 338.1 | 346.7 | 334.8 | 346.9 | **4,069.9** |
| Ropa | 345.5 | 319.7 | 343.7 | 336.2 | 342.5 | 333.1 | 347.5 | 343.1 | 333.5 | 344.6 | 335.2 | 346.0 | **4,070.6** |
| **Total mes** | **3,463.4** | **3,129.9** | **3,463.8** | **3,349.4** | **3,454.0** | **3,339.5** | **3,459.3** | **3,457.2** | **3,342.9** | **3,466.8** | **3,355.2** | **3,468.7** | **40,750.2** |

**Interpretación:**
- Las 10 categorías tienen ingresos anuales casi iguales (entre 4,069 y 4,087 millones; Juguetes es la mayor y Hogar la menor, con menos de 0.5 % de diferencia). Es lo esperado: el generador elige la categoría al azar con la misma probabilidad para todas.
- La diferencia entre meses depende de **cuántos días tiene el mes**: febrero (28 días) es el más bajo en todas las categorías (~3,130 millones), los meses de 30 días quedan en ~3,340–3,355 y los de 31 días en ~3,455–3,470. La fecha se genera uniforme a lo largo del año, así que cada día recibe en promedio la misma cantidad de ventas.

**Decisiones del código:**
- La clave del mapper es **compuesta**: `categoria|AAAA-MM`. Se une con `|` porque Hadoop Streaming toma como clave todo lo que está antes del primer TAB; así el shuffle agrupa por categoría *y* mes juntos. El reducer separa la clave al escribir el resultado.
- El mes se toma de `fecha_hora[:7]` (`"2025-06-26 17:48:55"` → `"2025-06"`), y se valida que sea un mes entre 01 y 12.
- El mapper emite el ingreso en **centavos (entero)**, así la suma es exacta y el resultado coincide al centavo con el secuencial; con `float` aparecerían diferencias por redondeo.
- El mapper ignora el encabezado (`campos[0] == "id"`), líneas con un número de columnas distinto de 8, fechas mal formadas y valores no numéricos (`try/except ValueError`), sin detener el job.
- Se usa un reducer (`-numReduceTasks 1`) para obtener un solo `part-00000` ordenado, que es el archivo que lee `cargar_resultados.py`.

## Comparativa de rendimiento (C2)

| Método | Tiempo `real` | Resultado |
|---|---:|---|
| Hadoop Streaming (standalone) | 19.740 s | 120 registros |
| `secuencial.py` (línea por línea) | 5.132 s | 120 registros |
| ¿Coinciden? | `diff` sin diferencias | ✅ |

**¿Por qué el secuencial fue más rápido?** En modo standalone Hadoop corre todo en una sola JVM con el `LocalJobRunner`, sin paralelismo real entre máquinas, así que no gana nada frente a un solo proceso y en cambio paga costos extra: arrancar la JVM y el framework, dividir el archivo en splits de 32 MB, lanzar un proceso de Python por cada tarea, pasar los 5 millones de pares clave-valor como texto por stdin/stdout entre Java y Python, y luego ordenarlos y escribirlos a disco en la fase *shuffle & sort* antes del reducer. El script secuencial lee el archivo una sola vez y acumula solo 120 totales en un diccionario en memoria, sin serializar ni ordenar millones de registros. Con 336 MB el archivo cabe de sobra en una sola máquina, así que la sobrecarga de MapReduce pesa más que su beneficio.

## Teoría (Parte E)

**1. Modos de Hadoop.** En *standalone* (local) todo corre en un solo proceso Java, sin demonios y usando el sistema de archivos local; sirve para desarrollar y depurar. En *pseudo-distribuido* cada demonio (NameNode, DataNode, ResourceManager, NodeManager) corre como proceso separado pero en una sola máquina, comunicándose por SSH/red como si fuera un clúster. En *totalmente distribuido* los demonios se reparten entre varias máquinas reales con replicación de datos. HDFS se usa en pseudo-distribuido y en totalmente distribuido; standalone usa el disco local.

**2. Volumen vs `COPY`.** (a) Tamaño: copiar 400 MB dentro de la imagen la hace enorme, lenta de construir y de distribuir. (b) Los datos cambian independientemente del código: con un volumen se reemplaza el CSV sin reconstruir la imagen, y cada alumno monta su propio archivo con la misma imagen. (c) Seguridad y repositorio: el dataset no queda dentro de las capas de la imagen ni en Git. Además, `:ro` garantiza que el contenedor no lo modifique.

**3. `down` vs `down -v`.** `docker compose down` detiene y elimina los contenedores y la red, pero los volúmenes nombrados (`pg_data`) se conservan, así que al volver a levantar los datos siguen ahí. `docker compose down -v` además borra los volúmenes nombrados declarados en el compose, por lo que la base de datos se pierde y hay que volver a cargar los resultados (y en este proyecto también se borran la salida del job y las llaves SSH, que se regeneran al arrancar).

**4. ¿Por qué MapReduce no siempre es más rápido?** Con 400 MB el problema cabe en memoria de una sola máquina y el costo fijo de MapReduce (arranque de JVM, planificación de tareas, serialización, shuffle/sort a disco) es mayor que el trabajo útil. MapReduce conviene cuando los datos son demasiado grandes para una sola máquina (decenas de GB a TB), cuando hay un clúster real con varios nodos que procesan bloques en paralelo cerca de donde están guardados (localidad de datos en HDFS), y cuando se necesita tolerancia a fallos en trabajos largos.

**5. `CMD` vs `ENTRYPOINT`, `COPY` vs `ADD`.** `ENTRYPOINT` define el ejecutable fijo del contenedor; `CMD` define el comando o los argumentos por defecto, que se reemplazan fácilmente con `docker run imagen otro_comando`. Combinados, `CMD` se pasa como argumentos al `ENTRYPOINT` (aquí `entrypoint.sh` prepara las llaves y luego ejecuta `sshd -D` que viene del `CMD`). `COPY` solo copia archivos del contexto de construcción; `ADD` además descomprime automáticamente archivos `.tar` locales y puede descargar URLs. Se recomienda `COPY` salvo que se necesite esa función extra.

## Evidencias

Las salidas de comandos y las verificaciones ejecutadas se guardan en `evidencias/`:

- `hadoop_version.txt` — versión Hadoop 3.3.6.
- `ssh_localhost.txt` y `ssh_api_hadoop.txt` — acceso por llave desde ambos contenedores.
- `job.log` — salida de MapReduce y secuencial, tiempos medidos y comparación exacta.
- `api_crud.txt` — respuestas GET, POST, PUT y DELETE; termina con los 120 registros originales.
- `persistencia.txt` — reinicio con `docker compose down` / `up` y verificación de los 120 registros.
- `dashboard.png` — captura de la vista visual de resultados.

## Guía rápida para la defensa oral

- **Cambiar el puerto de la API:** editar `API_PORT` en `.env` → `docker compose up -d api` → `curl http://localhost:NUEVO/resultados`. El puerto interno de Flask sigue siendo 5000; solo cambia el del host.
- **De suma a promedio:** en `reducer.py` llevar también un contador (`conteo_actual += 1` por línea) y al emitir escribir `suma / conteo`. Así sale el ingreso promedio por venta en cada categoría y mes.
- **Filtrar por un mes:** en `mapper.py`, justo antes del `print`, agregar `if mes != "2025-03": continue`.
- **Agrupar solo por categoría (sin mes):** cambiar la clave del mapper a `print(f"{categoria}\t{...}")` y adaptar `emitir()` del reducer.
- **Borrar el volumen y recargar:** `docker compose down -v` → `docker compose up -d` → `run_job.sh` → `cargar_resultados.py`.
- **Si algo falla:** `docker compose logs hadoop` / `docker compose logs api`; si el job dice que la salida ya existe, borrar `/data/output/resultado` (el script ya lo hace); si `ssh` pide contraseña, revisar permisos de `~/.ssh` (700) y `authorized_keys` (600).
