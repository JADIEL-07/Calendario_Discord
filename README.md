# Wipe Calendar Bot

Mantiene **un solo mensaje** en un canal de Discord con las próximas fechas de wipe de varios servidores de ARK. Las fechas usan marcas de Discord (`<t:…:f>` / `<t:…:R>`), así que cada persona ve su hora local y un contador en vivo — Discord lo cuenta solo, el bot no necesita correr seguido para eso.

Lo que el bot sí hace solo es **acelerar sus propias ediciones cuando un wipe se acerca**: GitHub Actions lo dispara cada hora; si al editar detecta que el wipe más cercano de cualquier servidor queda a menos de 1 hora, se queda despierto reeditando más seguido (30 → 10 → 5 → 1 min) hasta que pase, en vez de esperar a la próxima hora en punto. Si nada está cerca, edita una vez y sale.

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
6. Actions → "Actualizar calendario de wipes" → *Run workflow* para probar. Desde ahí corre solo cada hora (y más seguido cuando un wipe esté cerca, ver abajo).

Probar sin tocar Discord (PowerShell): `$env:PYTHONPATH = "src"; python -m wipe_bot --dry-run`. Tests: `pip install -r requirements-dev.txt; pytest`.

## Tipos de regla (`config/schedule.json`)

- `weekly`: cada semana (`weekday`, `time`, `tz`). El horario de verano se aplica solo según la zona.
- `interval`: cada N días desde una fecha ancla.
- `rotation`: un grupo por semana en ciclo (p. ej. INX 6→2→4→3 man).
- `once`: fecha única; tras pasar muestra "sin próxima fecha" hasta que la actualices.

## Cadencia de actualización

- **Disparador en GitHub Actions**: cada hora (`.github/workflows/update.yml`). Es lo único que cuesta minutos de Actions (plan gratis: 2000 min/mes en repos privados), por eso se deja ahí en vez de cada minuto: a ese ritmo el cupo se agota en 1-2 días.
- **Dentro de cada corrida** (`src/wipe_bot/main.py`, `_run_update_loop`): si el wipe más próximo de cualquier servidor queda a ≤ 1h, se queda reeditando más seguido mientras se acerca — 30min → 10min → 5min → 1min — sin esperar al cron. Si nada está cerca, edita una vez y sale. Tope de seguridad: nunca corre más de ~65 min seguidos (`MAX_LOOP_SECONDS`), por eso el workflow tiene `timeout-minutes: 70`.
- **No reescribe el cron en sí** (ej. para hacerlo "una vez al día" cuando no hay nada cerca): el token automático de Actions (`GITHUB_TOKEN`) tiene bloqueado el permiso para modificar archivos dentro de `.github/workflows/`, por seguridad. Lograrlo requeriría un Personal Access Token con scope `workflow` guardado como secreto — una credencial más amplia que el webhook — y no se hizo porque el costo actual (cron horario, ~720 min/mes) ya es barato.

## Límites conocidos

- El contador `:R` muestra la unidad más gruesa que le quede (ej. "en 3 días" en vez de "en 3 días y 4 horas"); es cómo Discord lo redondea, no algo que el bot controle.
- El cron de GitHub puede retrasarse algunos minutos y se pausa si el repo está 60 días sin actividad.
- `delete_message(webhook_url, message_id)` en `discord_webhook.py` deja que el bot borre sus propios mensajes (útil si el `MESSAGE_ID` queda inválido y hay que publicar uno nuevo). No sirve para borrar el mensaje que publicaste a mano: Discord nunca deja que un webhook borre mensajes de otro autor, sin excepción.
- Datos sin confirmar: Lunar Ark y Tazz (una sola fecha vista), New Era (estimado), Ark Nova (mensual deducido de solo 2 fechas vistas). MESA 100x tiene una encuesta cerrada "100x 1 week wipes" ganada con 83% a favor: si el servidor pasa a wipe semanal, cambia su evento a `weekly` en el JSON. Madalark sigue sin datos (no se encontró ese servidor). Si alguno cambia su calendario, edita `config/schedule.json`.
- El webhook solo edita sus propios mensajes: el mensaje que publicaste a mano seguirá existiendo; bórralo tú.
