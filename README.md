# Peruanita MRP - Planificación y Consolidación de Producción

Módulo para Odoo 18 que extiende las funcionalidades de manufactura con herramientas de planificación mensual y consolidación de componentes.

## 🎯 Características Principales

### 1. Información de Ventas en Órdenes de Fabricación
- **Cliente**: Se muestra automáticamente el cliente cuando la orden proviene de una venta
- **Distribuidor**: Información del distribuidor relacionado
- **Vínculo directo**: Botón para acceder rápidamente a la orden de venta relacionada

### 2. Consolidación de Traslados (Batches)
Permite agrupar los traslados de materia prima de múltiples órdenes de fabricación en batches para facilitar la gestión logística.

**Cómo usar:**
1. Selecciona múltiples órdenes de fabricación
2. Haz clic en **Acción** → **Consolidar Órdenes de Fabricación**
3. Revisa y selecciona los traslados a incluir en el batch
4. Crea el batch para agrupar los traslados

### 3. Consolidación de Componentes para Solicitudes de Compra ⭐

La funcionalidad estrella del módulo que permite planificar las compras mensuales de manera consolidada.

**Cómo usar:**

#### Paso 1: Seleccionar Órdenes de Producción
Desde la vista de lista de órdenes de fabricación, selecciona todas las órdenes que deseas planificar (por ejemplo, todas las órdenes del mes).

#### Paso 2: Abrir el Wizard de Consolidación
- Haz clic en **Acción** → **Consolidar para Solicitud de Compra**
- El wizard se abrirá mostrando todos los componentes consolidados

#### Paso 3: Configurar el Margen de Stock
- En el campo **% Margen de Stock**, ingresa el porcentaje de colchón que deseas agregar
- Ejemplo: Si ingresas `30`, se agregará un 30% adicional a todas las cantidades
- **Cálculo**: `Cantidad con Margen = Cantidad Requerida × (1 + Margen% / 100)`

**Ejemplo:**
```
Cantidad Requerida: 100 unidades
Margen: 30%
Cantidad con Margen: 130 unidades (100 × 1.30)
```

#### Paso 4: Revisar y Editar Componentes

En la pestaña **Componentes Consolidados** verás:

| Campo | Descripción |
|-------|-------------|
| **Producto** | Componente consolidado |
| **Referencia Interna** | Código del producto |
| **Cantidad Requerida** | Suma total de todas las órdenes (solo lectura) |
| **Cantidad con Margen** | Cantidad final a solicitar (editable) |
| **Unidad de Medida** | UdM del componente |
| **# Órdenes** | Cantidad de órdenes que requieren este componente |

**Edición Manual:**
- Puedes hacer clic en cualquier celda de **Cantidad con Margen** para editarla manualmente
- Útil para ajustar cantidades específicas independientemente del margen general

#### Paso 5: Agregar Notas (Opcional)
En la pestaña **Notas**, puedes agregar instrucciones especiales para el departamento de logística.

#### Paso 6: Crear Solicitud de Compra
- Haz clic en el botón **Crear Solicitud de Compra**
- El sistema automáticamente:
  - Agrupa los componentes por proveedor
  - Crea una o múltiples órdenes de compra (una por proveedor)
  - Incluye el precio del proveedor preferido
  - Establece el origen con las órdenes de fabricación
  - Te redirige a la(s) orden(es) creada(s)

## 📊 Ejemplo Práctico

### Escenario:
Tienes 3 órdenes de fabricación planificadas para el mes:

**OP/0001**: 10 unidades de Producto A
- 20 kg de Acero
- 30 unidades de Tornillos

**OP/0002**: 5 unidades de Producto B
- 10 kg de Acero
- 15 unidades de Pernos

**OP/0003**: 8 unidades de Producto A
- 16 kg de Acero
- 24 unidades de Tornillos

### Consolidación:
Al seleccionar las 3 órdenes y abrir el wizard, verás:

| Producto | Cantidad Requerida | # Órdenes |
|----------|-------------------|-----------|
| Acero | 46 kg | 3 |
| Tornillos | 54 unidades | 2 |
| Pernos | 15 unidades | 1 |

### Con Margen del 30%:

| Producto | Cant. Requerida | Cant. con Margen |
|----------|----------------|------------------|
| Acero | 46 kg | 59.8 kg |
| Tornillos | 54 unidades | 70.2 unidades |
| Pernos | 15 unidades | 19.5 unidades |

### Resultado:
Se crearán órdenes de compra agrupadas por proveedor, listas para que logística las revise y confirme.

## ⚙️ Configuración Necesaria

### Proveedores
Para que el sistema pueda crear automáticamente las órdenes de compra, asegúrate de:
1. Ir a **Inventario** → **Productos**
2. Para cada componente, configurar al menos un proveedor en la pestaña **Compra**
3. Establecer el precio de compra

Si un producto no tiene proveedor configurado, el sistema mostrará un error informativo.

## 🔧 Dependencias

- `mrp`: Módulo de manufactura de Odoo
- `sale_mrp`: Integración de ventas con manufactura
- `purchase`: Módulo de compras de Odoo

## 📝 Notas Técnicas

- Los componentes se consolidan automáticamente por producto y unidad de medida
- Solo se consideran movimientos de materia prima que no estén cancelados
- Las órdenes de compra se agrupan automáticamente por proveedor
- Si hay múltiples proveedores, se crearán múltiples órdenes de compra

## 👨‍💻 Autor

**Juan Salvador**
- Website: https://jsalvador.dev

## 📄 Licencia

LGPL-3

---

**Versión**: 18.0.2.0.0  
**Compatible con**: Odoo 18.0
