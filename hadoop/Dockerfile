# ------------------------------------------------------------
# Imagen de Hadoop 3.3.6 en modo standalone + OpenSSH Server
# Examen P2 - Matricula 125054310
# ------------------------------------------------------------
FROM debian:bookworm-slim

ARG HADOOP_VERSION=3.3.6
ARG HADOOP_URL=https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz

# 1) Paquetes: Java (OpenJDK 17), Python 3, OpenSSH (servidor y cliente) y utilidades
#    default-jdk-headless crea /usr/lib/jvm/default-java, que sirve en amd64 y arm64
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-jdk-headless python3 openssh-server openssh-client \
        curl ca-certificates procps rsync \
    && rm -rf /var/lib/apt/lists/*

# 2) Variables de entorno de Java y Hadoop
ENV JAVA_HOME=/usr/lib/jvm/default-java \
    HADOOP_HOME=/opt/hadoop \
    HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin

# 3) Descargar y descomprimir Hadoop en /opt/hadoop
RUN curl -fSL "$HADOOP_URL" -o /tmp/hadoop.tar.gz \
    && tar -xzf /tmp/hadoop.tar.gz -C /opt \
    && mv /opt/hadoop-${HADOOP_VERSION} $HADOOP_HOME \
    && rm /tmp/hadoop.tar.gz \
    && rm -rf $HADOOP_HOME/share/doc

# 4) JAVA_HOME dentro de hadoop-env.sh y variables para las sesiones SSH
#    (las sesiones SSH no heredan los ENV de Docker, por eso van en /etc/profile.d)
RUN echo "export JAVA_HOME=$JAVA_HOME" >> $HADOOP_CONF_DIR/hadoop-env.sh \
    && printf 'export JAVA_HOME=%s\nexport HADOOP_HOME=%s\nexport HADOOP_CONF_DIR=%s\nexport PATH=$PATH:%s/bin:%s/sbin\n' \
       "$JAVA_HOME" "$HADOOP_HOME" "$HADOOP_CONF_DIR" "$HADOOP_HOME" "$HADOOP_HOME" > /etc/profile.d/hadoop.sh

# 5) Usuario hadoop SIN contrasena utilizable ('*' = no se puede entrar con password)
RUN useradd -m -s /bin/bash hadoop \
    && usermod -p '*' hadoop \
    && mkdir -p /home/hadoop/.ssh /data/output /keys \
    && chmod 700 /home/hadoop/.ssh \
    && sed -i '1i . /etc/profile.d/hadoop.sh' /home/hadoop/.bashrc \
    && chown -R hadoop:hadoop /home/hadoop/.ssh /data/output $HADOOP_HOME

# 6) SSH solo con llaves: sin contrasenas y sin login de root
RUN mkdir -p /run/sshd \
    && sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config

# 7) Script de arranque (genera llaves y levanta sshd)
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

WORKDIR /opt/mapreduce
EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/sbin/sshd", "-D", "-e"]
