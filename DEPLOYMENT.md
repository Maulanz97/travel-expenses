# Despliegue en Oracle Cloud

Guía del despliegue personal de Viaje Claro, validado manualmente en septiembre
de 2026. Los comandos Bash se ejecutan por SSH en Ubuntu salvo donde se indique
PowerShell. Sustituir `IP_PUBLICA`, `TU_SUBDOMINIO.duckdns.org` y los valores de
Supabase antes de ejecutar. No se incluyen credenciales ni llaves privadas.

## Arquitectura

```text
Celular / navegador
        │ HTTPS :443
        ▼
Oracle: Caddy (servicio de Ubuntu, certificados automáticos)
        │ HTTP 127.0.0.1:5173
        ▼
Docker Compose: web / Nginx
        │ /api → viaje-claro-api:8000
        ▼
FastAPI → SQLite /data/expenses.db → volumen viaje-claro-data
        │
        └── Supabase Auth: validación de la sesión

systemd timer → script de respaldo → ~/backups/viaje-claro
                                     └── SCP manual → computadora
```

Supabase almacena las identidades, no los gastos. Caddy termina TLS y Nginx
sirve el build de React y dirige las solicitudes de API. Los puertos de Docker
5173 y 8002 se publican solo en loopback; el acceso web público pasa por Caddy.
La solución usa una sola instancia de la API y una base SQLite.

## 1. Instancia y acceso SSH

Entorno utilizado: Ubuntu en Oracle, arquitectura ARM64 (`aarch64`), usuario
`ubuntu`. Confirmar la imagen y arquitectura antes de instalar herramientas:

```bash
whoami
uname -m
cat /etc/os-release
```

La instancia necesita una VNIC en una subred pública, IP pública y ruta
`0.0.0.0/0` hacia un Internet Gateway. Una IP privada por sí sola no permite
SSH directo desde Internet. La IP pública puede asignarse desde la VNIC,
IP administration, editar la IP privada principal.

Desde PowerShell:

```powershell
ssh -i "C:\ruta\privada\llave.key" ubuntu@IP_PUBLICA
```

Verificar la huella del servidor en la primera conexión mediante un canal
independiente, como la consola de Oracle. En Windows, si SSH indica
`UNPROTECTED PRIVATE KEY FILE`, restringir la ACL del archivo privado a su
propietario y las cuentas de sistema necesarias. No usar la llave `.pub`
como llave privada, subirla a Git ni dar acceso a grupos generales.

Actualizar Ubuntu y reiniciar si `/var/run/reboot-required` existe:

```bash
sudo apt update
sudo apt upgrade -y
```

Las cuotas gratuitas y la disponibilidad de Oracle deben comprobarse en la
cuenta; esta guía no garantiza un costo cero.

## 2. Docker y repositorio

Instalar Docker Engine, Buildx y el complemento Compose desde el
[repositorio oficial para Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
Usar los paquetes correspondientes a ARM64; no instalar Docker Desktop en el
servidor. Se utilizan comandos con `sudo`, sin añadir usuarios al grupo Docker.

```bash
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
sudo apt install -y git nano
mkdir -p ~/apps
cd ~/apps
git clone https://github.com/Maulanz97/travel-expenses.git
cd travel-expenses
```

Las imágenes se construyen en Oracle para su arquitectura. Un volumen de la
computadora no se transfiere al clonar: una instalación nueva empieza vacía.

## 3. Configuración y primer arranque

Crear el archivo con permisos privados desde el principio:

```bash
umask 077
touch backend/.env.docker
nano backend/.env.docker
```

Contenido de ejemplo:

```dotenv
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_TU_CLAVE_PUBLICA
ALLOWED_ORIGINS=https://TU_SUBDOMINIO.duckdns.org
```

La URL de Supabase no lleva `/rest/v1/`. La Publishable key se incorpora al
frontend y es pública por diseño; no usar `service_role`, `sb_secret_` ni el
secreto de Google. `.env.docker` está excluido de Git. Compose fuerza
`LOCAL_DEV_AUTH=0`, `APP_ENV=production` y la ruta SQLite del volumen.

```bash
chmod 600 backend/.env.docker
sudo docker volume create viaje-claro-data
sudo docker compose --env-file backend/.env.docker config --quiet
sudo docker compose --env-file backend/.env.docker up -d --build
sudo docker compose --env-file backend/.env.docker ps
curl -fsS http://127.0.0.1:5173/api/health
```

Resultado esperado: API healthy, web en ejecución y `{"status":"ok"}`.
El healthcheck no verifica el inicio de sesión ni todos los accesos a SQLite.
La API aplica `alembic upgrade head` antes de arrancar. El volumen externo
debe existir; Compose no lo crea automáticamente. Ver [DOCKER.md](DOCKER.md).

## 4. DNS y reglas de red

Registrar un subdominio en [Duck DNS](https://www.duckdns.org/) y asignarle la
IP pública de Oracle, no la IP detectada del equipo doméstico. Dejar IPv6 sin
configurar si no se ha habilitado. No compartir ni guardar su token en Git.

```bash
getent ahostsv4 TU_SUBDOMINIO.duckdns.org
```

El resultado debe coincidir con la IP pública del servidor. Si cambia la IP
efímera de Oracle, actualizar Duck DNS; no hay actualización DNS automatizada.

En una Security List asociada a la subred o un NSG asociado a la VNIC, permitir:

| Origen | Protocolo | Puerto destino | Uso |
| --- | --- | --- | --- |
| IP de administración /32 | TCP | 22 | SSH; conservar acceso antes de restringir |
| 0.0.0.0/0 | TCP | 80 | HTTP y validación de certificados |
| 0.0.0.0/0 | TCP | 443 | HTTPS |

Usar reglas stateful (Stateless desmarcado) y cualquier puerto de origen.
Las Security Lists afectan a toda la subred. No es necesario abrir 5173 ni
8002 en Oracle. Consultar las [reglas de Oracle](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm).

También revisar el firewall de Ubuntu:

```bash
sudo iptables -L INPUT -n --line-numbers
```

En la instancia utilizada, el rechazo general estaba en la posición 5.
Se insertó esta regla ANTES del rechazo; en otro servidor revisar la posición
real y evitar duplicados antes de ejecutar:

```bash
sudo iptables -I INPUT 5 -p tcp -m multiport --dports 80,443 -m conntrack --ctstate NEW -j ACCEPT
sudo netfilter-persistent save
systemctl is-enabled netfilter-persistent
```

Estos pasos corresponden al firewall encontrado, no a todas las imágenes de
Ubuntu. Mantener la regla SSH y no vaciar las reglas de Oracle o Docker.

## 5. Caddy y HTTPS

Instalar Caddy como servicio del host desde su
[repositorio oficial](https://caddyserver.com/docs/install#debian-ubuntu-raspbian).
No se ejecuta en Compose. En `/etc/caddy/Caddyfile`, configurar:

```caddyfile
TU_SUBDOMINIO.duckdns.org {
    reverse_proxy 127.0.0.1:5173
}
```

```bash
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable --now caddy
sudo systemctl reload caddy
curl -fsS https://TU_SUBDOMINIO.duckdns.org/api/health
```

Caddy obtiene y renueva certificados cuando DNS y conectividad son correctos.
Conservar su directorio de datos al mantener o actualizar el servicio.
Ver [HTTPS automático](https://caddyserver.com/docs/automatic-https).

## 6. Supabase y prueba desde celular

En Authentication → URL Configuration:

- Site URL: `https://TU_SUBDOMINIO.duckdns.org/`.
- Redirect URLs: `https://TU_SUBDOMINIO.duckdns.org/` y
  `https://TU_SUBDOMINIO.duckdns.org/?recovery=1`.
- Conservar las URLs locales si se sigue desarrollando en la computadora.

El callback de Google hacia Supabase sigue siendo el de ese proyecto:
`https://TU_PROYECTO.supabase.co/auth/v1/callback`. La dirección de la app se
configura como retorno en Supabase. Ver [AUTH_SETUP.md](AUTH_SETUP.md) y la
[documentación de redirecciones](https://supabase.com/docs/guides/auth/redirect-urls).

Probar desde un celular con datos móviles: HTTPS sin advertencias, login con
Google, regreso al dominio público y creación de un viaje. Las invitaciones
personales requieren iniciar sesión y aceptar el enlace; la cuenta entra con
permiso de consulta hasta que el organizador habilite registro de gastos.

## 7. Respaldos y recuperación

Instalar el servicio y timer siguiendo [DOCKER.md](DOCKER.md#respaldos-diarios-en-oracle).
Horario: 03:00 America/Mexico_City, más una ejecución diez minutos después
del arranque. Retención: 14 días. El script solo elimina copias antiguas
después de crear y verificar una nueva. Archivos en
`/home/ubuntu/backups/viaje-claro`, con fecha UTC y permisos 600.

```bash
sudo systemctl start viaje-claro-backup.service
sudo journalctl -u viaje-claro-backup.service --no-pager -n 30
systemctl list-timers viaje-claro-backup.timer --all --no-pager
```

Descargar periódicamente una copia a otra máquina; sustituir el nombre exacto
del archivo. Desde PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\Backups\viaje-claro"
scp -i "C:\ruta\privada\llave.key" ubuntu@IP_PUBLICA:/home/ubuntu/backups/viaje-claro/ARCHIVO.db "$HOME\Backups\viaje-claro\"
```

Las copias en el mismo servidor no cubren la pérdida de la instancia. El
respaldo SQLite tampoco incluye `.env.docker`, configuración de Supabase,
llaves SSH o Caddy; conservar esa configuración en un lugar privado separado.

### Procedimiento de recuperación

Este procedimiento es una guía operativa pendiente de ensayo completo:
se verificó integridad y restauración en memoria, no un reemplazo de producción.

1. Elegir una copia y verificar `PRAGMA integrity_check`, claves foráneas y
   versión Alembic sobre una copia aislada. Conservar el respaldo original.
2. Detener el timer y esperar a que termine cualquier respaldo activo.
3. Detener web y API con Compose para evitar escrituras. Conservar el volumen
   actual como punto de retorno; no borrarlo ni copiar encima de SQLite activa.
4. Crear un volumen nuevo e importar allí la copia con el nombre `expenses.db`.
   Usar un volumen vacío evita arrastrar archivos WAL/SHM de otra base.
5. Configurar un override de Compose para que `volumes.data.name` apunte al
   volumen nuevo. Mantener ese override en todos los comandos posteriores.
6. Arrancar con una versión del código compatible con la copia. La API aplica
   migraciones automáticamente: no usar código anterior con un esquema nuevo
   sin una estrategia de compatibilidad comprobada.
7. Verificar login, viajes, gastos, balances y permisos. Reactivar el timer
   una vez adaptado su comando al override, y comprobar un respaldo nuevo.

Preparar los comandos exactos según la copia, versión y volumen elegidos
antes de intervenir datos reales. No usar `alembic stamp` para fingir una
migración ni eliminar el volumen antiguo hasta validar la recuperación.

## 8. Actualizar la aplicación

En el servidor, desde el repositorio:

```bash
git status --short
git rev-parse HEAD
sudo systemctl start viaje-claro-backup.service
sudo journalctl -u viaje-claro-backup.service --no-pager -n 20
```

Guardar el identificador del commit y comprobar `Verified backup` antes de
continuar. Resolver cualquier modificación local antes de actualizar:

```bash
git pull --ff-only
sudo docker compose --env-file backend/.env.docker up -d --build
sudo docker compose --env-file backend/.env.docker restart web
sudo docker compose --env-file backend/.env.docker ps
curl -fsS http://127.0.0.1:5173/api/health
```

Reiniciar web permite que Nginx resuelva de nuevo el nombre de la API si su
contenedor cambió de IP. El proceso puede causar una interrupción breve.
Probar también el dominio público e inicio de sesión. Los cambios en unidades
systemd requieren reinstalarlas y ejecutar `daemon-reload`; `git pull` no las
copia automáticamente. Las imágenes base no están fijadas por digest: una
reconstrucción no garantiza reproducir exactamente una imagen anterior.

## 9. Diagnóstico y prueba de reinicio

| Síntoma | Comprobación |
| --- | --- |
| SSH rechaza la llave | ACL local, usuario ubuntu y llave correspondiente |
| Dominio no responde | DNS, IP pública, ruta, reglas OCI y firewall Ubuntu |
| Error de certificado | `sudo journalctl -u caddy --no-pager -n 50` |
| Error 502 | Compose ps, logs de web/API y health local; revisar resolución de Nginx |
| Login vuelve a localhost | Site URL y Redirect URLs de Supabase |
| No aparecen viajes locales | SQLite de Oracle es independiente de la computadora |
| Respaldo falla | journal del servicio, espacio de disco y API disponible |

```bash
sudo docker compose --env-file backend/.env.docker logs --tail 100
df -h
systemctl is-active docker caddy
```

Para comprobar arranque automático, reiniciar con `sudo reboot`, volver a
conectarse y verificar Compose ps, Caddy, el timer y los datos desde el celular.
`restart: unless-stopped` necesita que los contenedores existan y no hayan sido
detenidos explícitamente; si se ejecutó `compose down`, recrearlos con `up -d`.

## Estado verificado y trabajo pendiente

Comprobado por el operador durante el despliegue:

- Acceso SSH a Ubuntu ARM64, Docker y Compose funcionando.
- App pública por HTTPS, inicio de sesión y uso desde celular.
- Persistencia y arranque de la app tras reiniciar la instancia.
- Respaldo verificado, restauración en memoria y descarga externa por SCP.
- Ejecución manual del servicio de respaldo y próxima ejecución del timer.

Pendiente: ensayo con cuenta de acompañante, restauración completa aislada,
copias externas automáticas, alertas de fallo y CI/CD. Tener un timer habilitado
no demuestra que todas sus futuras ejecuciones vayan a terminar correctamente.
