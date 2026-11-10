#!/bin/bash
# Corre el job de Hadoop Streaming y el script secuencial, mide ambos tiempos
# y compara los resultados.
# Uso (desde el host):
#   docker compose exec -u hadoop hadoop bash /opt/mapreduce/run_job.sh
set -e

# Hadoop Streaming extrae sus archivos auxiliares en el directorio actual.
cd /tmp

MATRICULA=${MATRICULA:-125054310}
ENTRADA=/data/input/ventas_${MATRICULA}.csv
SALIDA=/data/output/resultado
STREAMING_JAR=$(ls $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar)

if [ ! -f "$ENTRADA" ]; then
    echo "No existe $ENTRADA. Genera el CSV y ponlo en la carpeta data/ del proyecto."
    exit 1
fi

# Hadoop falla si la carpeta de salida ya existe
rm -rf "$SALIDA"

echo "===== 1) Job MapReduce (Hadoop Streaming) ====="
time hadoop jar "$STREAMING_JAR" \
    -D mapreduce.job.name="ingreso-categoria-mes-${MATRICULA}" \
    -input "$ENTRADA" \
    -output "$SALIDA" \
    -mapper "python3 mapper.py" \
    -reducer "python3 reducer.py" \
    -numReduceTasks 1 \
    -file /opt/mapreduce/mapper.py \
    -file /opt/mapreduce/reducer.py

echo
echo "===== Resultado (part-00000) ====="
cat "$SALIDA/part-00000"

echo
echo "===== 2) Script secuencial ====="
time python3 /opt/mapreduce/secuencial.py "$ENTRADA" > /data/output/secuencial.txt
cat /data/output/secuencial.txt

echo
echo "===== 3) Comparacion ====="
if diff "$SALIDA/part-00000" /data/output/secuencial.txt; then
    echo "OK: MapReduce y secuencial dan exactamente el mismo resultado."
else
    echo "ATENCION: los resultados son distintos."
fi
