# Frontend · Viaje Claro

Interfaz React y Vite para gestionar viajes, gastos, pagos e invitaciones.

Consulta el [README principal](../README.md) para instalación, arquitectura y pruebas, y la [guía de autenticación](../AUTH_SETUP.md) para Supabase.

Desde esta carpeta:

```powershell
npm ci
npm run dev
npm run build
npm run lint
node --test src/*.test.js config/*.test.js
```

El desarrollo independiente requiere una API en el puerto 8000 y las variables públicas de `frontend/.env.example`. Para iniciar ambos servicios juntos, usa el lanzador de la raíz. Nunca pongas claves secretas en variables `VITE_*`.
