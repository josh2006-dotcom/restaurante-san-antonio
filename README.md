# 🍽️ Restaurante San Antonio — Aplicación Web
## Trabajo Aplicativo — Gestión de Base de Datos

---

## ✅ REQUISITOS PREVIOS

- Python 3.10 o superior → https://www.python.org/downloads/
- SQL Server con la base de datos "RestauranteSanAntonio" ya creada
- ODBC Driver 17 for SQL Server → https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

---

## 📦 INSTALACIÓN

### 1. Instalar dependencias Python
Abre CMD (Símbolo del sistema) y ejecuta:
```
pip install flask pyodbc
```

### 2. Configurar la conexión a SQL Server
Abre el archivo `database.py` y edita estas líneas:
```python
SERVER   = 'localhost'           # Cámbialo si tu SQL Server tiene otro nombre (ej: PC-JUAN\SQLEXPRESS)
DATABASE = 'RestauranteSanAntonio'
DRIVER   = 'ODBC Driver 17 for SQL Server'
```

Si usas autenticación con usuario/contraseña en vez de Windows Auth,
descomenta el segundo bloque de código en database.py.

### 3. Ejecutar la aplicación
Desde la carpeta del proyecto:
```
python app.py
```

### 4. Abrir en el navegador
```
http://127.0.0.1:5000
```

---

## 🗂️ ESTRUCTURA DEL PROYECTO

```
RestauranteSanAntonio/
│
├── app.py              ← Servidor Flask (rutas y lógica)
├── database.py         ← Conexión a SQL Server
├── README.md           ← Este archivo
│
└── templates/
    ├── base.html       ← Plantilla base (navbar, estilos globales)
    ├── index.html      ← Página de inicio / carta del menú
    ├── registro.html   ← Registro / login de cliente
    ├── pedido.html     ← Hacer un pedido (con resumen en tiempo real)
    ├── mis_pedidos.html← Ver el historial de pedidos del cliente
    ├── admin_login.html← Login del administrador
    └── admin.html      ← Panel de administración
```

---

## 🔑 ACCESO AL PANEL DE ADMINISTRACIÓN

URL: http://127.0.0.1:5000/admin
Contraseña: admin123

Puedes cambiar la contraseña en app.py, línea:
```python
if password == 'admin123':
```

---

## 🛠️ SOLUCIÓN DE PROBLEMAS

| Error | Solución |
|-------|----------|
| `No module named 'flask'` | Ejecuta: pip install flask pyodbc |
| Error de conexión SQL Server | Verifica que SQL Server está corriendo. Revisa SERVER en database.py |
| `ODBC Driver not found` | Descarga e instala "ODBC Driver 17 for SQL Server" de Microsoft |
| Puerto 5000 ocupado | En app.py, cambia a: app.run(port=5001) |

---

## 📱 PÁGINAS DEL SISTEMA

| Página | URL | Descripción |
|--------|-----|-------------|
| Menú | / | Carta pública del restaurante |
| Registro | /registro | Crear cuenta / retomar sesión |
| Hacer Pedido | /pedido | Seleccionar platos + personalizar + ver total |
| Mis Pedidos | /mis_pedidos | Historial del cliente |
| Admin Login | /admin/login | Acceso al panel |
| Admin Panel | /admin | Ver todos los pedidos + cambiar estados |

---

## 🗄️ BASE DE DATOS UTILIZADA

Tablas: Cliente, Plato, Opcion_Personalizacion, Pedido, Detalle_Pedido, Detalle_Personalizacion

El script SQL completo está en el archivo entregado con el trabajo aplicativo.
