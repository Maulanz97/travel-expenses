# Travel Expenses

MVP para registrar y dividir gastos de un viaje entre varias personas.

## Ejecutar localmente

Abre dos terminales en la raíz del repositorio.

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

### Actualizar una base de prueba existente

La primera migración crea llaves foráneas con borrado en cascada. Si ya tenías
un archivo `backend/expenses.db` creado antes de este cambio, haz una copia de
seguridad y elimínalo **solo si deseas reiniciar los datos de prueba**. Después
ejecuta `alembic upgrade head` otra vez. Así la nueva base aplicará las reglas:

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
