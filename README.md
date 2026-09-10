# Travel Expenses

MVP para registrar y dividir gastos de un viaje entre varias personas.

## Ejecutar localmente

Para trabajar sin configurar Supabase, usa el modo local explícito. Desde la raíz,
instala las dependencias y crea la base de datos:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
Set-Location ..
.\.venv\Scripts\python.exe scripts/start_local.py
```

Abre `http://127.0.0.1:5173`. Si los puertos están ocupados, añade
`--api-port 8001 --port 5179` al lanzador y abre `http://127.0.0.1:5179`.
Este modo solo funciona en esta computadora. Para iniciar con autenticación,
configura primero [Supabase y los permisos](AUTH_SETUP.md) y usa las dos
terminales descritas a continuación.

### 1. Backend

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Set-Location backend
alembic upgrade head
uvicorn app.main:app --reload
```

La API quedará disponible en `http://127.0.0.1:8000` y su documentación en
`http://127.0.0.1:8000/docs`.

### Reiniciar una base anterior a la consolidación

Las migraciones de desarrollo se consolidaron en `e579a0_initial_schema.py`.
Una instalación vacía se crea con `alembic upgrade head`. Para una base con las
revisiones antiguas, detén los servidores y ejecuta desde `backend`:

```powershell
..\.venv\Scripts\python.exe -m scripts.reset_test_data --rebuild --confirm
```

El comando crea un respaldo y reemplaza todos los datos por una base vacía con
el esquema actual. No uses `alembic stamp` para actualizar una base antigua:
eso no reconstruye sus tablas. Las nuevas modificaciones se añadirán como
migraciones posteriores a esta base inicial. Se conservan las reglas:

- borrar un gasto elimina sus participantes;
- borrar un viaje elimina sus gastos e integrantes;
- borrar una persona elimina sus participaciones, pertenencias y gastos pagados.

### 2. Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Abre `http://127.0.0.1:5173`.

## Flujo de prueba

1. En **Personas**, crea a quienes viajarán.
2. Crea el viaje y selecciona a quien lo organiza.
3. Agrega las demás personas al viaje.
4. Registra un gasto, seleccionando quién pagó y quienes participan.
5. Revisa el resumen para ver balances y pagos sugeridos.
