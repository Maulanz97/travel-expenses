# Activar acceso y permisos

## Seguir usando la app en esta computadora

Desde la raíz del proyecto, ejecuta:

```powershell
.\.venv\Scripts\python.exe scripts/start_local.py
```

Abre http://127.0.0.1:5173. El lanzador inicia ambos servidores solo en la interfaz local y muestra «Modo local · sin iniciar sesión». Permite usar los viajes existentes sin Supabase; no modifica las cuentas vinculadas ni sus permisos de acceso. Detén ambos servidores con Ctrl+C.

Si esos puertos están ocupados, usa `.\.venv\Scripts\python.exe scripts/start_local.py --api-port 8001 --port 5179` y abre http://127.0.0.1:5179.

Este modo se activa únicamente en ese proceso, con una clave aleatoria entre el proxy y el backend que no se entrega al navegador. Requiere entorno de desarrollo, conexión local y el proxy autorizado. Una compilación de producción no incluye el acceso local. No configures `LOCAL_DEV_AUTH` ni uses este lanzador al publicar; usa el arranque normal con Supabase.

La integración usa Supabase Auth; los gastos continúan en FastAPI y SQLite. No requiere trasladar las cuentas a Supabase ni una clave service_role.

## Configurar Supabase

1. Crea un proyecto y copia su URL y su **Publishable key** (también se admite la clave pública `anon`). Nunca uses `service_role` ni una clave secreta en el frontend.
2. Activa Email/password, confirmación de correo y una política de contraseñas de al menos 8 caracteres. Para entregar correos fuera de pruebas, configura SMTP en Supabase.
3. Activa Google siguiendo la guía oficial. Registra en Google el callback que muestra Supabase y guarda el Client ID y Client Secret **en Supabase**, no en esta app.
4. Configura Site URL con la dirección de la app. Autoriza las URLs de retorno exactas: por ejemplo `http://localhost:5173/` y `http://localhost:5173/?recovery=1`. Añade sus equivalentes HTTPS al publicar. El flujo PKCE de confirmación/recuperación debe terminar en el navegador que lo inició.
5. Copia `frontend/.env.example` a `frontend/.env.local`, completa los dos valores públicos y reinicia Vite.
6. En la terminal donde arrancas el backend, configura las mismas variables públicas:

```powershell
$env:SUPABASE_URL = 'https://YOUR_PROJECT.supabase.co'
$env:SUPABASE_PUBLISHABLE_KEY = 'YOUR_PUBLIC_PUBLISHABLE_KEY'
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Ejecuta el comando desde `backend`. El servidor verifica cada token contra `/auth/v1/user`; si Supabase no está configurado o disponible, no concede acceso. No hay un modo anónimo que eluda los permisos.

Si frontend y backend están en orígenes distintos al publicar, establece `ALLOWED_ORIGINS` en el backend con los orígenes HTTPS autorizados separados por comas. No uses `*`.

## Viajes existentes

La revisión inicial se consolidó en `e579a0`. Las bases anteriores necesitan un
reinicio explícito que elimina sus datos: desde `backend`, ejecuta
`..\.venv\Scripts\python.exe -m scripts.reset_test_data --rebuild --confirm`.
En una base nueva no hay organizadores antiguos que vincular: crea tu primer viaje.
El procedimiento siguiente aplica a viajes creados con el esquema actual.

Aplica primero la migración con respaldo desde `backend`:

```powershell
..\.venv\Scripts\python.exe -m scripts.upgrade_payments
```

Antes del primer inicio de sesión de un organizador existente, vincula explícitamente su ID de persona y su correo de acceso:

```powershell
..\.venv\Scripts\python.exe -m scripts.link_organizer --user-id ID_REAL --email CORREO_REAL
```

El script crea un respaldo y se niega a reemplazar una cuenta vinculada. No asocia automáticamente correos de contacto antiguos: eso permitiría reclamar datos ajenos. No ejecutarlo con IDs o correos de ejemplo. Los gastos anteriores conservan su autor desconocido y solo el organizador puede modificarlos.

Los intentos de gasto pendientes nuevos se guardan por cuenta y viaje. Los intentos locales anteriores a esta integración permanecen en su clave anterior; deben revisarse antes de volver a registrar esos gastos. Un organizador puede recuperar una operación antigua con su identificador original mediante la API, sin duplicarla.

## Permisos

- Cada cuenta ve únicamente sus viajes y las personas de esos viajes (o las personas que creó).
- Quien crea un viaje es su organizador, aunque se intente enviar otro organizador a la API.
- En Integrantes → Acceso al viaje, el organizador fija un correo de acceso explícito y el permiso «Puede registrar gastos».
- El integrante entra con Google o con correo confirmado. Supabase vincula los métodos compatibles de la misma identidad; la app usa el ID verificado, no el nombre ni los metadatos para autorizar.
- Una persona sin cuenta puede seguir participando en el reparto. Un integrante con cuenta y sin permiso consulta el viaje.
- El permiso permite crear gastos y editar, anular o restaurar los propios. Retirarlo impide las siguientes escrituras. Los demás registros solo los modifica el organizador.
- Los pagos, integrantes y permisos los administra el organizador. El permiso de gastos no permite conceder permisos ni convertirse en organizador.
- No se envían invitaciones desde esta interfaz: comparte el enlace de la app por tu cuenta.
- Un correo ya vinculado a otra persona se rechaza; no se fusionan participantes con balances automáticamente. Prepara el acceso de los integrantes existentes antes de que se registren para evitar esta situación.

## Verificación pendiente del proveedor

Probar con dos cuentas reales: correo confirmado, Google, recuperación de contraseña, cierre de sesión, acceso invitado, concesión/revocación y separación de viajes. Las pruebas automatizadas verifican la autorización con identidades simuladas, no sustituyen esta comprobación OAuth.

Documentación oficial: [Google](https://supabase.com/docs/guides/auth/social-login/auth-google), [contraseñas y recuperación](https://supabase.com/docs/guides/auth/passwords), [vinculación de identidades](https://supabase.com/docs/guides/auth/auth-identity-linking).
