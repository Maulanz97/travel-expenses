# Viaje Claro · Gastos compartidos

Aplicación web personal para organizar gastos de un viaje en grupo: registrar quién pagó, repartir importes y consultar cuánto debe o recibe cada integrante.

**Menos tiempo calculando, más tiempo compartiendo.**
Divide los gastos, multiplica los momentos.

## Funcionalidades

- Viajes e integrantes, con directorio de personas reutilizable.
- Repartos iguales o personalizados y varios pagadores por gasto.
- Revisión antes de guardar, fechas, edición, anulación e historial.
- Pagos parciales, balances con desglose y pagos sugeridos.
- Resumen en texto con vista previa, copia y menú de compartir compatible.
- Acceso con Google o correo mediante Supabase Auth.
- Permisos por viaje e invitaciones personales de un solo uso, con vencimiento de siete días y cancelación. Aceptarlas concede solo consulta.
- Validaciones para evitar eliminar personas con registros asociados.
- Identificadores de operación para reintentar gastos y pagos sin duplicarlos.

## Arquitectura y decisiones

```text
React / Vite ── HTTP / API ── FastAPI ── SQLAlchemy ── SQLite
     │                         │
     └── Supabase Auth ─────────┘
         Inicio de sesión y verificación de identidad
```

El frontend presenta importes en MXN. El backend valida permisos y calcula repartos con precisión decimal y centavos enteros. Alembic versiona el esquema. Crear un viaje con su organizador y guardar un gasto con sus participantes son operaciones atómicas.

Supabase gestiona la autenticación; los viajes y gastos se guardan en SQLite. Las invitaciones vinculan una cuenta al integrante de un viaje sin fusionar personas ni alterar gastos. Sus tokens se almacenan como hashes.

El proyecto está en desarrollo. Docker, CI/CD y el despliegue en Oracle Cloud están planificados, pero aún no forman parte de esta versión. El acceso desde otros dispositivos requiere desplegar frontend y API con HTTPS y datos persistentes.

## Probar en Windows / PowerShell

Requisitos: Python 3.13, Node.js compatible con Vite 8, npm y Git. Consulta el requisito `engines` del paquete Vite instalado al elegir Node.js.

Desde la raíz del repositorio:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
Set-Location ..
.\.venv\Scripts\python.exe scripts/start_local.py
```

Abre `http://127.0.0.1:5173`. Este modo permite probar sin configurar Supabase y solo está disponible mediante el proxy local autorizado. No debe publicarse.
El lanzador selecciona otro puerto para la API si el solicitado está ocupado. Si 5173 está ocupado, detén la ejecución anterior o usa `--port 5179` en modo local.

### Con autenticación

```powershell
Copy-Item auth.local.example.json auth.local.json
Copy-Item frontend/.env.example frontend/.env.local
```

Completa los valores con tu propio proyecto y su clave pública. Luego ejecuta:

```powershell
.\.venv\Scripts\python.exe scripts/start_local.py --auth
```

El lanzador toma `auth.local.json` para ambos servicios; `frontend/.env.local` sirve también para ejecutar Vite por separado. Consulta [AUTH_SETUP.md](AUTH_SETUP.md) para configurar Google, URLs de retorno y vincular organizadores de viajes existentes. Las cuentas nuevas no reclaman viajes locales.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests
Set-Location ../frontend
npm run build
npm run lint
node --test src/*.test.js config/*.test.js
```

Las pruebas cubren cálculos, validaciones, operaciones atómicas, reintentos, autorización, invitaciones y migraciones. La autenticación se simula en las pruebas del backend: no sustituye las pruebas reales de Google desde celulares.

## Datos y configuración

- No se incluyen bases de datos, respaldos, archivos `.env`, credenciales ni dependencias instaladas. Los archivos de ejemplo contienen valores ficticios.
- El Client Secret de Google se configura en Supabase, nunca en el frontend.
- La clave Publishable es pública por diseño; los permisos se validan en la API.
- Antes de actualizar una base existente, desde `backend` ejecuta `..\.venv\Scripts\python.exe -m scripts.upgrade_payments`: crea un respaldo y aplica las migraciones pendientes.
- Las bases anteriores a la consolidación `e579a0` requieren el procedimiento explícito descrito en [AUTH_SETUP.md](AUTH_SETUP.md); no uses `alembic stamp` para simular una actualización del esquema.

## Límites actuales

- Requiere conexión para consultar y registrar datos; no hay sincronización offline.
- Compartir el resumen genera una copia de texto, no un enlace con datos en vivo.
- Las invitaciones locales solo funcionan en la misma computadora.
- No procesa transferencias bancarias: registra pagos realizados fuera de la app.
- Antes de usarla durante un viaje falta verificar el despliegue, respaldos, restauración y el flujo completo con cuentas reales.
