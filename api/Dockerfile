FROM python:3.12-slim

# Cliente SSH para demostrar el acceso api -> hadoop
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

# "ssh hadoop@hadoop" usa la llave del volumen compartido /keys
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh \
    && printf 'Host hadoop\n    User hadoop\n    IdentityFile /keys/api_key\n    StrictHostKeyChecking accept-new\n' > /root/.ssh/config \
    && chmod 600 /root/.ssh/config

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/

EXPOSE 5000
CMD ["python", "app.py"]
