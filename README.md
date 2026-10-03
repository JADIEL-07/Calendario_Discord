# Wipe Calendar Bot

Mantiene **un solo mensaje** en un canal de Discord con las próximas fechas de wipe de varios servidores de ARK. Se recalcula cada hora con GitHub Actions y edita el mensaje mediante un webhook. Las fechas usan marcas de Discord (`<t:…:f>` / `<t:…:R>`), así que cada persona ve su hora local y un contador en vivo.

## Estructura

```
config/schedule.json        # ÚNICO archivo que editas: servidores, reglas, zonas horarias
src/wipe_bot/               # código (schedule, render, discord_webhook, main)
tests/                      # pruebas (pytest)
.github/workflows/update.yml  # cron cada hora
```

## Puesta en marcha (una sola vez)

1. **Webhook**: en Discord, canal de wipes → Editar canal → Integraciones → Webhooks → Nuevo webhook → *Copiar URL*. Es un secreto: no lo pegues en chats ni en el repo.
2. **Repositorio**: crea un repo privado en GitHub y sube esta carpeta.
3. **Secreto**: Settings → Secrets and variables → Actions → *Secrets* → `WEBHOOK_URL` = la URL copiada.
4. **Publicar el mensaje inicial** (en tu PC o Codespace):

   PowerShell (Windows):
   ```powershell
   pip install -r requirements.txt
   $env:WEBHOOK_URL = "<url>"; $env:PYTHONPATH = "src"
   python -m wipe_bot --init
   ```
   Bash (Linux/Mac/Codespace):
   ```bash
   pip install -r requirements.txt
   WEBHOOK_URL="<url>" PYTHONPATH=src python -m wipe_bot --init
   ```
   Imprime un `MESSAGE_ID`.
5. **Variable**: Settings → Secrets and variables → Actions → *Variables* → `MESSAGE_ID` = ese valor.
6. Actions → "Actualizar calendario de wipes" → *Run workflow* para probar. Desde ahí corre solo cada hora.

Probar sin tocar Discord (PowerShell): `$env:PYTHONPATH = "src"; python -m wipe_bot --dry-run`. Tests: `pip install -r requirements-dev.txt; pytest`.

## Tipos de regla (`config/schedule.json`)

- `weekly`: cada semana (`weekday`, `time`, `tz`). El horario de verano se aplica solo según la zona.
- `interval`: cada N días desde una fecha ancla.
- `rotation`: un grupo por semana en ciclo (p. ej. INX 6→2→4→3 man).
- `once`: fecha única; tras pasar muestra "sin próxima fecha" hasta que la actualices.

## Límites conocidos

- El contador `:R` es aproximado ("en 3 días"), no exacto en d/h/m; Discord no permite más.
- El cron de GitHub puede retrasarse algunos minutos y se pausa si el repo está 60 días sin actividad.
- Datos sin confirmar: Lunar Ark y Tazz (una sola fecha vista), New Era (estimado), Ark Nova (mensual deducido de solo 2 fechas vistas). MESA 100x tiene una encuesta cerrada "100x 1 week wipes" ganada con 83% a favor: si el servidor pasa a wipe semanal, cambia su evento a `weekly` en el JSON. Madalark sigue sin datos (no se encontró ese servidor). Si alguno cambia su calendario, edita `config/schedule.json`.
- El webhook solo edita sus propios mensajes: el mensaje que publicaste a mano seguirá existiendo; bórralo tú.
