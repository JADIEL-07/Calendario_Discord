# Wipe Calendar Bot

Mantiene **un solo mensaje** en un canal de Discord con las próximas fechas de wipe de varios servidores de ARK. Las fechas usan marcas de Discord (`<t:…:f>` / `<t:…:R>`), así que cada persona ve su hora local y un contador en vivo — Discord lo cuenta solo, el bot no necesita correr seguido para eso.

Lo que el bot sí hace solo es **acelerar sus propias ediciones cuando un wipe se acerca**: GitHub Actions lo dispara cada hora; si al editar detecta que el wipe más cercano de cualquier servidor queda a menos de 1 hora, se queda despierto reeditando más seguido (30 → 10 → 5 → 1 min) hasta que pase, en vez de esperar a la próxima hora en punto. Si nada está cerca, edita una vez y sale.

## Estructura

```
config/schedule.json        # ÚNICO archivo que editas: servidores, reglas, zonas horarias
src/wipe_bot/                 # código
  schedule.py                   # calculo de fechas (DST) y de cadencia
  render.py                     # construye el texto del mensaje
  discord_webhook.py            # publica/edita/borra via webhook (solo sus propios mensajes)
  discord_bot.py                # limpia el canal via bot (puede borrar mensajes de cualquiera)
  main.py                       # punto de entrada
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

## Limpieza automática del canal (opcional)

Un webhook solo puede editar/borrar los mensajes que él mismo publicó — nunca uno que pegaste a mano. Para que el bot borre *cualquier* mensaje que no sea el del calendario (y así limpiar el que publicaste manualmente, o cualquier otro que aparezca después), hace falta un **bot de Discord** de verdad, con permiso "Gestionar mensajes". Es una credencial más amplia que el webhook: con ese permiso puede borrar mensajes de cualquier persona en el canal donde lo invites, así que inviítalo solo a ese canal.

1. **Crear la app y el bot**: [discord.com/developers/applications](https://discord.com/developers/applications) → *New Application* → pestaña *Bot* → *Reset Token* → copiar el token. Es un secreto, igual que `WEBHOOK_URL`.
2. **Invitarlo solo al canal de wipes**: pestaña *OAuth2* → *URL Generator* → scope `bot` → permisos `View Channel`, `Read Message History`, `Manage Messages` → abrir la URL generada y añadirlo a tu servidor. Luego, en el canal `🔄┃ᴡɪᴘᴇ` → Editar canal → Permisos → dale esos mismos permisos solo ahí si quieres limitarlo más (opcional pero recomendado).
3. **Canal ID**: activa el modo desarrollador en Discord (Ajustes → Avanzado → Modo desarrollador), luego clic derecho sobre el canal → *Copiar ID de canal*.
4. **Secreto y variable en GitHub**: `DISCORD_BOT_TOKEN` (Secrets) = el token del paso 1; `CHANNEL_ID` (Variables) = el id del paso 3.
5. Lanza el workflow a mano una vez: debería borrar el mensaje viejo (y cualquier otro que no sea el calendario) en esa misma corrida.

Si no configuras `DISCORD_BOT_TOKEN`/`CHANNEL_ID`, el bot sigue funcionando igual, solo que sin esta limpieza (lo avisa en el log de Actions).

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
- `delete_message(webhook_url, message_id)` en `discord_webhook.py` deja que el bot (via webhook) borre sus propios mensajes (útil si el `MESSAGE_ID` queda inválido y hay que publicar uno nuevo). Para borrar mensajes de otro autor hace falta el bot de "Limpieza automática del canal" de arriba.
- La limpieza del canal (bot) borra mensajes de hasta 100 a la vez si tienen menos de 14 días; los más viejos los borra uno por uno porque la API de Discord no permite bulk-delete sobre mensajes más viejos que eso. Si el canal tiene muchísimo historial, solo revisa las últimas ~500 entradas por corrida (5 páginas de 100).
- Datos sin confirmar: Lunar Ark y Tazz (una sola fecha vista), New Era (estimado), Ark Nova (mensual deducido de solo 2 fechas vistas). MESA 100x tiene una encuesta cerrada "100x 1 week wipes" ganada con 83% a favor: si el servidor pasa a wipe semanal, cambia su evento a `weekly` en el JSON. Madalark sigue sin datos (no se encontró ese servidor). Si alguno cambia su calendario, edita `config/schedule.json`.
