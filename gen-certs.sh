#!/usr/bin/env bash
set -euo pipefail
mkdir -p certs
pushd certs >/dev/null

# 1) CA (Autoridad Certificadora)
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -subj "/C=CO/O=ElasticLab/OU=CA/CN=Elastic-Lab-CA" -out ca.crt

make_cert () {
  local name="$1"
  cat > "${name}.cnf" <<EOF
[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt             = no

[ req_distinguished_name ]
C  = CO
O  = ElasticLab
OU = Nodes
CN = ${name}

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = ${name}
DNS.2 = localhost
IP.1  = 127.0.0.1
EOF

  # key + CSR
  openssl genrsa -out "${name}.key" 2048
  openssl req -new -key "${name}.key" -out "${name}.csr" -config "${name}.cnf"

  # Firmar con la CA
  openssl x509 -req -in "${name}.csr" -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out "${name}.crt" -days 825 -sha256 -extensions req_ext -extfile "${name}.cnf"
}

for n in es01 es02 es03 kibana; do
  make_cert "$n"
done

echo "✅ Certificados generados en ./certs"
popd >/dev/null
