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
