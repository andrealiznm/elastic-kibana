# Elastic Lab (Docker + TLS + Metricbeat + ILM)

## 0) Requisitos
- Docker / Docker Compose
- Asigna al menos 6–8 GB de RAM a Docker Desktop si usas Mac/Windows
- Linux: `sudo sysctl -w vm.max_map_count=262144` (hazlo persistente en `/etc/sysctl.conf`)

## 1) Generar certificados con OpenSSL
```bash
cd elastic-lab
./gen-certs.sh
