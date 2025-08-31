#!/usr/bin/env python3
import requests, random, time, json
from datetime import datetime, timezone

# Configuración
ES = "https://localhost:9200"
INDEX_ALIAS = "logs-synthetic"   # alias de escritura
USER = "elastic"
PWD = "Elastic2025"
CA = "./certs/ca.crt"

# Datos de ejemplo
levels = ["INFO", "WARN", "ERROR", "DEBUG"]
hosts = ["web-1", "web-2", "api-1", "batch-1"]
services = ["checkout", "users", "payments", "search"]

def generate_doc():
    return {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "host": random.choice(hosts),
        "level": random.choice(levels),
        "service": random.choice(services),
        "message": f"Synthetic log message {random.randint(1, 100000)}"
    }

def main():
    session = requests.Session()
    session.auth = (USER, PWD)
    session.verify = CA

    print(f"Iniciando ingesta de logs sintéticos en {INDEX_ALIAS} … (Ctrl+C para parar)")
    i = 0
    try:
        while True:
            # lote de 100 docs
            bulk = ""
            for _ in range(100):
                bulk += json.dumps({ "index": { "_index": INDEX_ALIAS } }) + "\n"
                bulk += json.dumps(generate_doc()) + "\n"

            resp = session.post(f"{ES}/_bulk", data=bulk,
                                headers={"Content-Type": "application/x-ndjson"})
            if resp.status_code >= 300:
                print("Error en bulk:", resp.text)
                break

            i += 100
            if i % 1000 == 0:
                print(f"Ingestados {i} documentos …")

            time.sleep(1)  # pausa de 1s entre lotes (ajusta si quieres más rápido)
    except KeyboardInterrupt:
        print(f"\nProceso interrumpido. Total enviado: {i} docs")

if __name__ == "__main__":
    main()
