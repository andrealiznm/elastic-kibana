#!/usr/bin/env bash
set -euo pipefail
ES="${ES:-https://localhost:9200}"
ES_USER="${ES_USER:-elastic}"
ES_PWD="${ES_PWD:-Elastic2025}"
CA="${CA:-./certs/ca.crt}"
ALIAS="${ALIAS:-logs-synthetic}"
PATTERN="${PATTERN:-logs-synthetic-*}"
INIT_INDEX="${INIT_INDEX:-logs-synthetic-000001}"

if [ -n "${CA:-}" ]; then CURL=(curl -sS --fail-with-body --cacert "$CA" -u "$ES_USER:$ES_PWD"); else CURL=(curl -sS --fail-with-body -k -u "$ES_USER:$ES_PWD"); fi
json(){ "${CURL[@]}" -H 'Content-Type: application/json' "$@"; }
plain(){ "${CURL[@]}" "$@"; }

setup-index(){
  json -X PUT "$ES/_ilm/policy/logs_policy" --data-binary @ilm/logs-ilm.json
  json -X PUT "$ES/_index_template/logs-synth-template" --data-binary @templates/logs-template.json
  if ! plain "$ES/$INIT_INDEX" >/dev/null 2>&1; then
    json -X PUT "$ES/$INIT_INDEX" -d "{\"aliases\": {\"$ALIAS\": {\"is_write_index\": true}}}"
  fi
  echo " listo: ILM+template+índice inicial ($INIT_INDEX) con alias $ALIAS"
}

ingest-index(){
  n="${1:-1000}"
  tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
  levels=(INFO WARN ERROR DEBUG); hosts=(web-1 web-2 api-1 batch-1); services=(checkout users payments search)
  for ((i=1;i<=n;i++)); do
    ts="$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")"
    printf '{"index":{"_index":"%s"}}\n' "$ALIAS" >>"$tmp"
    printf '{"@timestamp":"%s","host":"%s","level":"%s","service":"%s","message":"Synthetic log %d"}\n' \
      "$ts" "${hosts[RANDOM%4]}" "${levels[RANDOM%4]}" "${services[RANDOM%4]}" "$RANDOM" >>"$tmp"
  done
  "${CURL[@]}" -H 'Content-Type: application/x-ndjson' -X POST "$ES/_bulk" --data-binary @"$tmp" >/dev/null
  echo " ingestados $n docs en alias $ALIAS"
}

status-index(){
  plain "$ES/_cluster/health?pretty" || true; echo
  plain "$ES/_cat/indices/$PATTERN?v" || true; echo
  plain "$ES/$PATTERN/_ilm/explain?human&pretty" || true
}

rollover-index(){
  json -X POST "$ES/$ALIAS/_rollover?pretty" || true
  status-index
}

delete-indexes(){
  json -X DELETE "$ES/$PATTERN" || true
  echo "borrados índices $PATTERN"
}

case "${1:-}" in
  setup-index) shift; setup-index "$@";;
  ingest-index) shift; ingest-index "$@";;
  status-index) shift; status-index "$@";;
  rollover-index) shift; rollover-index "$@";;
  delete-indexes) shift; delete-indexes "$@";;
  *) echo "Uso: $0 {setup-index|ingest-index [N]|status-index|rollover-index|delete-indexes}"; exit 1;;
esac
