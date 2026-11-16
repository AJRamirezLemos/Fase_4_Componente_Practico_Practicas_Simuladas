# Software FJ – Sistema Integral de Gestión de Clientes, Servicios y Reservas

UNAD · Programación 213023_125 · Fase 4 – Prácticas simuladas · Ejercicio 1

Aplicación de consola orientada a objetos, sin base de datos. Gestiona clientes,
servicios (reserva de salas, alquiler de equipos, asesorías) y reservas en listas
en memoria, con manejo avanzado de excepciones y registro de eventos en
`software_fj.log`.

## Integrantes
   Alex Jefferson Ramirez Lemos

## Archivos
| Archivo | Descripción |
|---|---|
| `Proyecto_Fase4_SoftwareFJ.py` | Código fuente completo con la demostración |
| `Proyecto_Fase4_SoftwareFJ.ipynb` | Mismo código en cuaderno (ejecutar las celdas en orden) |
| `software_fj.log` | Se genera automáticamente al ejecutar (no hace falta crearlo) |

## Cómo ejecutarlo
Requiere Python 3.8 o superior (se usan parámetros de solo posición).

```
python Proyecto_Fase4_SoftwareFJ.py
```

O abra el `.ipynb` en Jupyter/Colab y use "Ejecutar todo".

## Qué demuestra
- Clase abstracta `Entidad`; `Cliente` con propiedades validadas; clase abstracta
  `Servicio` con tres servicios derivados (sobrescritura de `calcular_costo`).
- Sobrecarga simulada en `Servicio.calcular_costo_total` (costo, con descuento,
  con descuento e impuesto).
- `Reserva` con estados PENDIENTE → CONFIRMADA → PROCESADA / CANCELADA.
- Excepciones personalizadas, `try/except/else/finally` y encadenamiento (`raise ... from`).
- 46 operaciones de demostración (válidas e inválidas) con verificación explícita
  de costos y estados; el sistema continúa tras cada error.

