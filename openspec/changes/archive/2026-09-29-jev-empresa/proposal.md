## Why

Jev demostró valor con etiquetas limpias (Bitext: 94 %, automatiza 89 % con 99 %). El paso para
producción es medirlo con tickets reales de la empresa. Son datos internos con información personal:
no deben salir de la máquina ni quedar en claro en prompts/logs. Se deja un pipeline listo para que el
usuario aporte su CSV.

## What Changes

- `jev/evaluar_empresa.py`: lee un CSV local (columnas configurables de texto y área, descripciones
  opcionales en JSON), anonimiza PII, divide estratificado, mide Naive Bayes y Jev 4B, calibra, deriva
  umbrales a 5 % y 10 % de error, y guarda `data/calibracion-<nombre>.json` para el router.
- Guardas: aborta si `LLM_BASE_URL` no es local salvo `--permitir-remoto`; registra el SHA-256 del CSV.
- Prueba end-to-end con Bitext como sustituto.

## Impact

- Nuevo script y artefacto de calibración. Sin dependencias nuevas.
