# Producto

<!-- impeccable:product-schema 1 -->

## Platform

web

## Usuarios

Personas que disfrutan viajar en grupo y quieren simplificar los cálculos de gastos compartidos. El contexto principal son los viajes; la misma necesidad también se presenta en actividades grupales con gastos compartidos.

## Propósito del producto

Facilitar el cálculo de gastos compartidos, mantener visibles los balances durante el viaje o la actividad y mostrar cuánto debe pagar cada persona y a quién. El éxito consiste en dedicar menos tiempo a calcular y más tiempo a compartir experiencias.

## Contexto de uso

Los grupos agregan participantes, registran gastos compartidos y consultan el resumen, los balances individuales y los pagos sugeridos a medida que se acumulan los gastos.

El flujo actual descrito en `README.md` consiste en registrar personas, crear un viaje con un organizador, agregar integrantes, registrar un gasto con su pagador y participantes, y revisar balances y pagos sugeridos.

## Capacidades y restricciones

Prioridades confirmadas por el usuario que deben conservarse:

- Agregar participantes al grupo.
- Registrar gastos compartidos.
- Calcular balances durante el viaje o la actividad.
- Mostrar un resumen de gastos y los balances.
- Mostrar los importes de los pagos sugeridos, quién paga y quién recibe.

Características de la implementación actual, sin considerarlas compromisos permanentes del producto:

- La interfaz web en React/Vite utiliza textos en español y presenta los importes en MXN (`frontend/src/App.jsx`).
- Los gastos se dividen en partes iguales entre los participantes seleccionados, con manejo del remanente en centavos enteros (`backend/app/services/expense_service.py`).
- La aplicación calcula pagos sugeridos; esto no implica que procese pagos.
- La interfaz actual utiliza el nombre «viajeclaro».

## Principios del producto

- Reducir el tiempo y el esfuerzo necesarios para calcular gastos compartidos.
- Conservar la funcionalidad de cálculo mientras evoluciona la interfaz.
- Facilitar la comprensión del balance de cada persona y de los pagos que le corresponden.
- Admitir actividades compartidas además de los viajes, manteniendo los viajes grupales como caso de uso principal.

## Evidencia disponible

- `README.md`: instrucciones actuales de instalación y flujo completo de uso.
- `frontend/src/App.jsx`: interfaces de participantes, viajes, gastos, resumen, balances y pagos sugeridos.
- `backend/app/services/expense_service.py`: división de gastos, balances acumulados y cálculo de pagos sugeridos.
- El usuario confirmó directamente el propósito y las prioridades anteriores. No se ha establecido una diferenciación exclusiva frente a otros productos ni se han medido los ahorros de tiempo.

## Compromisos de comunicación

El eslogan completo debe mantenerse como un conjunto: «Menos tiempo calculando, más tiempo compartiendo.» y «Divide los gastos, multiplica los momentos.». Las dos frases evocan las cuatro operaciones matemáticas básicas. Presentarlas con jerarquía compacta, en dos líneas cuando el ancho lo permita y con ajuste natural en móvil.

«viajeclaro» es un nombre de prototipo. Proponer alternativas y esperar la elección del usuario antes de reemplazarlo.

## Decisiones pendientes del producto

- Si un organizador mantiene todos los registros o cada participante registra sus gastos de forma independiente.
- La elección del nombre definitivo y si el idioma español, la moneda MXN y la división en partes iguales son requisitos a largo plazo.
- Los requisitos de accesibilidad específicos del producto y otros idiomas o monedas que deban admitirse.
