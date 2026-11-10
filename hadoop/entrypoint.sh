#!/bin/bash
# Arranque del contenedor hadoop:
#  1. Llaves de host de SSH (si faltan)
#  2. Llave del usuario hadoop para "ssh localhost" (requisito del modo pseudo-distribuido)
#  3. Llave para que el contenedor api entre como hadoop@hadoop (se comparte por el volumen ssh_keys)
#  4. Ejecuta el CMD (sshd en primer plano)
set -e

ssh-keygen -A >/dev/null

# --- 2) ssh localhost sin contrasena ---
if [ ! -f /home/hadoop/.ssh/id_ed25519 ]; then
    su hadoop -c "ssh-keygen -t ed25519 -N '' -q -f /home/hadoop/.ssh/id_ed25519"
fi

# --- 3) llave para el contenedor api (vive en el volumen compartido /keys) ---
if [ ! -f /keys/api_key ]; then
    ssh-keygen -t ed25519 -N '' -q -C "api@datamart" -f /keys/api_key
fi
chmod 600 /keys/api_key
chmod 644 /keys/api_key.pub

# authorized_keys = llave propia + llave del api
cat /home/hadoop/.ssh/id_ed25519.pub /keys/api_key.pub > /home/hadoop/.ssh/authorized_keys

# Que "ssh localhost" acepte la huella del host la primera vez sin preguntar
printf 'Host localhost 127.0.0.1\n    StrictHostKeyChecking accept-new\n' > /home/hadoop/.ssh/config
chmod 600 /home/hadoop/.ssh/config

chown -R hadoop:hadoop /home/hadoop/.ssh
chmod 600 /home/hadoop/.ssh/authorized_keys

echo "[hadoop] llaves listas, iniciando sshd..."
exec "$@"
