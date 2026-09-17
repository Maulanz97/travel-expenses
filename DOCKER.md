# Docker Compose en local

Ejecutar los comandos desde la raíz del repositorio, con Docker Desktop activo.
Esta configuración publica la app únicamente en esta computadora. El despliegue
en Oracle necesitará configurar HTTPS, dominio y red por separado.

## Configuración

Crear `backend/.env.docker` con los valores propios del proyecto:

```dotenv
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_TU_CLAVE_PUBLICA
ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Este archivo está excluido de Git y del contexto de construcción del backend.
No usar claves secretas ni service_role. Las variables VITE de Supabase son
públicas y se incorporan al JavaScript durante la construcción del frontend.

## Primera ejecución

Si aún hay contenedores iniciados manualmente, detenerlos con Ctrl+C en sus
terminales para liberar los puertos 5173 y 8002. Compose creará sus propios
contenedores y una red propia; no necesita la red manual viaje-claro-net.

El volumen externo `viaje-claro-data` debe existir. Si ya se usó en la prueba
manual, Compose reutiliza ese mismo volumen, incluidos sus viajes. En una
instalación nueva, crearlo una vez:

```powershell
docker volume create viaje-claro-data
```

Validar sin imprimir los valores de configuración:

```powershell
docker compose --env-file backend/.env.docker config --quiet
```

Construir y arrancar:

```powershell
docker compose --env-file backend/.env.docker up -d --build
```

Abrir http://127.0.0.1:5173 e iniciar sesión. Si se reutilizó el volumen,
comprobar que aparece el viaje anterior.

## Qué hace el archivo

- `build`: construye cada imagen desde su Dockerfile.
- `env_file`: entrega la configuración al backend al iniciar su contenedor.
- `--env-file` en el comando: permite que Compose sustituya las variables de
  los argumentos de construcción del frontend. Tiene una función diferente
  al atributo `env_file` del servicio; se necesitan ambos en esta configuración.
- `command`: aplica las migraciones antes de arrancar la API. Si fallan,
  Uvicorn no arranca. Esta configuración usa una única instancia de la API.
- `healthcheck` y `depends_on`: el frontend espera a que la API responda.
  `/health` comprueba el servidor, no la conexión con Supabase.
- `restart: unless-stopped`: reinicia los servicios tras fallos y al volver
  a arrancar Docker, salvo que se hayan detenido explícitamente.
- `external: true`: conserva el volumen fuera del ciclo de vida de Compose.
- La red por defecto permite que Nginx encuentre el servicio
  `viaje-claro-api` por su nombre, tal como está configurado en nginx.conf.

## Comandos habituales

```powershell
docker compose --env-file backend/.env.docker ps
docker compose --env-file backend/.env.docker logs --tail 100
docker compose --env-file backend/.env.docker exec viaje-claro-api alembic current
docker compose --env-file backend/.env.docker down
docker compose --env-file backend/.env.docker up -d
```

`down` elimina los contenedores y la red de Compose, pero conserva el volumen
externo. No eliminar manualmente `viaje-claro-data` si se quieren conservar los
datos. Un volumen persistente no sustituye las copias de seguridad.

Tras cambios en el código o en los valores públicos de Supabase, ejecutar
`up -d --build` de nuevo. Antes de aplicar nuevas migraciones a datos
importantes, hacer una copia de seguridad.

Referencias: [variables de Compose](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
y [volúmenes externos](https://docs.docker.com/reference/compose-file/volumes/).

## Respaldos diarios en Oracle

Los archivos de `deploy/systemd` suponen Ubuntu, el repositorio en
`/home/ubuntu/apps/travel-expenses` y la API de Compose en ejecución.
El script utiliza la API de respaldo de SQLite sin detener la app, verifica
integridad, claves foráneas y versión de migración, y publica la copia solo
si todo termina correctamente. Los nombres usan UTC.

Después de subir estos archivos a GitHub, ejecutar por SSH:

```bash
cd ~/apps/travel-expenses
git pull --ff-only
sudo install -d -o ubuntu -g ubuntu -m 700 /home/ubuntu/backups/viaje-claro
sudo install -m 644 deploy/systemd/viaje-claro-backup.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/viaje-claro-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start viaje-claro-backup.service
sudo journalctl -u viaje-claro-backup.service --no-pager -n 20
```

Tras comprobar el mensaje `Verified backup`, activar la programación:

```bash
sudo systemctl enable --now viaje-claro-backup.timer
systemctl list-timers viaje-claro-backup.timer --all
```

Se ejecuta a las 03:00 de America/Mexico_City, con precisión de un minuto,
independientemente de la zona horaria del servidor. La lista de timers puede
mostrar la hora equivalente en UTC. `Persistent=true` recupera una ejecución
diaria pendiente. También se programa una ejecución diez minutos después de
cada arranque para dar tiempo a que la API esté disponible.

Solo se eliminan archivos con el patrón de nombres de estos respaldos y más
de 14 días de antigüedad, después de crear una copia nueva válida. El servicio
usa root para acceder a Docker, pero las copias conservan el propietario de
la carpeta de destino y permisos 600. Los errores se registran en journalctl;
no se envían alertas automáticamente.

Esta automatización guarda copias en el mismo servidor. La copia externa
mediante SCP sigue siendo manual. No respalda la configuración de Supabase,
el archivo de entorno ni Caddy. La prueba de integridad no sustituye una
prueba de restauración de la app en un entorno separado.

Pruebas locales del script:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p "test_backup_sqlite.py"
```
