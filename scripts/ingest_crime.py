import os, sys, json, requests
import pandas as pd

# Ingesta del CSV de Chicago Crime (2001 - presente).
# Uso: python3 ingest_crime.py /ruta/Chicage_Crime_Data.csv
# NOTA: Ajusta los nombres de columnas si difieren en tu CSV.

if len(sys.argv) < 2:
    print("Uso: python3 ingest_crime.py /ruta/Chicage_Crime_Data.csv")
    sys.exit(1)

csv_path = sys.argv[1]
ES = os.getenv("ES", "https://localhost:9200")
USER = os.getenv("USER", "elastic")
PWD = os.getenv("PWD", "Elastic2025")
CA = os.getenv("CA", None)  # ruta a ca.crt si quieres verificar
INDEX = os.getenv("INDEX", "chicago-crimes")

auth = (USER, PWD)

# Crear índice con mapping
mapping = {
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1
  },
  "mappings": {
    "properties": {
      "case_number": {"type": "keyword"},
      "primary_type": {"type": "keyword"},
      "location_description": {"type": "keyword"},
      "arrest": {"type": "boolean"},
      "domestic": {"type": "boolean"},
      "date": {"type": "date"},
      "year": {"type": "integer"},
      "hour": {"type": "integer"},
      "is_night": {"type": "boolean"},
      "block": {"type": "keyword"},
      "iucr": {"type": "keyword"}
    }
  }
}

r = requests.put(f"{ES}/{INDEX}", auth=auth, json=mapping, verify=CA if CA else False)
if r.status_code not in (200, 400):
    print("Error creando índice:", r.text)
    sys.exit(1)

# Cargar por chunks para no reventar RAM
chunksize = 10000
for chunk in pd.read_csv(csv_path, chunksize=chunksize, low_memory=False):
    # Ajusta nombres de columnas si es necesario según tu CSV real
    # Supuestos comunes:
    # 'Case Number', 'Primary Type', 'Location Description', 'Arrest', 'Domestic', 'Date', 'Year', 'Block', 'IUCR'
    # La columna 'Date' suele venir en formato 'MM/DD/YYYY HH:MM:SS AM/PM'
    if 'Date' in chunk.columns:
        chunk['Date'] = pd.to_datetime(chunk['Date'], errors='coerce')
    else:
        raise RuntimeError("No encuentro columna 'Date' en el CSV.")

    df = pd.DataFrame({
        'case_number': chunk.get('Case Number'),
        'primary_type': chunk.get('Primary Type'),
        'location_description': chunk.get('Location Description'),
        'arrest': chunk.get('Arrest').astype('bool', errors='ignore') if 'Arrest' in chunk.columns else None,
        'domestic': chunk.get('Domestic').astype('bool', errors='ignore') if 'Domestic' in chunk.columns else None,
        'date': chunk['Date'],
        'year': chunk.get('Year'),
        'block': chunk.get('Block'),
        'iucr': chunk.get('IUCR')
    })

    df['hour'] = df['date'].dt.hour
    df['is_night'] = df['hour'].apply(lambda h: bool(h >= 22 or h < 8) if pd.notnull(h) else False)

    def to_actions(rows):
        for _, row in rows.iterrows():
            doc = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
            yield json.dumps({"index": {"_index": INDEX}})
            yield json.dumps(doc, default=str)

    lines = "\n".join(to_actions(df)) + "\n"
    br = requests.post(f"{ES}/_bulk", data=lines,
                       headers={"Content-Type":"application/x-ndjson"},
                       auth=auth, verify=CA if CA else False)
    br.raise_for_status()
    print("Ingestados:", df.shape[0])

print("✅ Ingesta completa")
