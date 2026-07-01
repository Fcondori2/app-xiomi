import sqlite3
from datetime import date
import os
import sys

# 1. Dejamos las variables vacías (así NO se ejecuta nada al importar)
conexion = None
cursor = None

def inicializar_base_datos():
    global conexion, cursor
    
    # 2. Detectamos si estamos en el celular o en la compu para elegir la carpeta correcta
    if hasattr(sys, "getandroidsdkversion") or os.environ.get("ANDROID_ROOT"):
        # En el celular: Guardamos en la carpeta interna segura de la App
        ruta_db = os.path.join(os.path.expanduser("~"), "sistema_ventas.db")
    else:
        # En la compu: Sigue usando el archivo local de siempre
        ruta_db = "sistema_ventas.db"
    
    # 3. Conectamos de forma segura aquí adentro
    conexion = sqlite3.connect(ruta_db)
    cursor = conexion.cursor()
    
    # =====================================================================
    # (ACÁ ABAJO SEGUÍ CON LAS LÍNEAS QUE YA TENÍAS PARA CREAR LAS TABLAS)
    # Por ejemplo, tus: cursor.execute("CREATE TABLE IF NOT EXISTS...")
    # =====================================================================
# ==========================================
# FASE 1: CREACIÓN DE LA ESTRUCTURA (TABLAS)
# ==========================================

cursor.executescript('''
-- Tabla de Clientes
CREATE TABLE IF NOT EXISTS Clientes (
    numero_cliente INTEGER PRIMARY KEY,
    nombre_apellido TEXT NOT NULL,
    cuit_dni INTEGER,
    direccion_entrega TEXT,
    telefono TEXT
);

-- Tabla de Productos (Catálogo)
CREATE TABLE IF NOT EXISTS Productos (
    codigo_articulo TEXT PRIMARY KEY,
    nombre_articulo TEXT NOT NULL,
    precio_unitario REAL NOT NULL
);

-- Tabla de Facturas (Cabecera)
CREATE TABLE IF NOT EXISTS Facturas (
    numero_factura INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    numero_cliente INTEGER,
    total_a_pagar REAL NOT NULL,
    FOREIGN KEY (numero_cliente) REFERENCES Clientes (numero_cliente)
);

-- Tabla de Detalle_Factura (Líneas del pedido)
CREATE TABLE IF NOT EXISTS Detalle_Factura (
    id_linea INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_factura INTEGER,
    codigo_articulo TEXT,
    precio_unitario REAL NOT NULL,
    unidades INTEGER NOT NULL,
    total_linea REAL NOT NULL,
    FOREIGN KEY (numero_factura) REFERENCES Facturas (numero_factura),
    FOREIGN KEY (codigo_articulo) REFERENCES Productos (codigo_articulo)
);
''')

# ==========================================
# FASE 2: CARGA DE DATOS MAESTROS (EJEMPLO)
# ==========================================

# Limpiamos las tablas para evitar duplicados si corres el script varias veces
cursor.executescript('''
    DELETE FROM Detalle_Factura; DELETE FROM Facturas; 
    DELETE FROM Productos; DELETE FROM Clientes;
''')

# Insertamos un cliente
cursor.execute('''
    INSERT INTO Clientes (numero_cliente, nombre_apellido, cuit_dni, direccion_entrega, telefono)
    VALUES (1570, 'Mejias Brisa', 27123456789, 'Barrio Virgen De Luján, Callé Pinamar Y Puerto Madero Mz517 Lt1', '388-1234567')
''')

# Insertamos un producto
cursor.execute('''
    INSERT INTO Productos (codigo_articulo, nombre_articulo, precio_unitario)
    VALUES ('ART-01', 'PREMIUM LIMONADA 3L. X 4', 7000.00)
''')

# ==========================================
# FASE 3: SIMULACIÓN DE UNA VENTA (APPK)
# ==========================================

# Variables que llegarían desde la pantalla de la app
numero_factura_app = 2031
cliente_seleccionado = 1570
fecha_hoy = date.today().strftime("%Y-%m-%d")

# Artículos en el carrito: [(codigo, unidades)]
carrito = [('ART-01', 2)]

# Calculamos el total buscando el precio vigente en la base de datos
total_factura = 0
lineas_a_insertar = []

for codigo, unidades in carrito:
    cursor.execute("SELECT precio_unitario FROM Productos WHERE codigo_articulo = ?", (codigo,))
    precio_db = cursor.fetchone()[0]
    total_linea = precio_db * unidades
    total_factura += total_linea
    
    lineas_a_insertar.append((numero_factura_app, codigo, precio_db, unidades, total_linea))

# Guardamos la Cabecera de la factura
cursor.execute('''
    INSERT INTO Facturas (numero_factura, fecha, numero_cliente, total_a_pagar)
    VALUES (?, ?, ?, ?)
''', (numero_factura_app, fecha_hoy, cliente_seleccionado, total_factura))

# Guardamos el Detalle de la factura
cursor.executemany('''
    INSERT INTO Detalle_Factura (numero_factura, codigo_articulo, precio_unitario, unidades, total_linea)
    VALUES (?, ?, ?, ?, ?)
''', lineas_a_insertar)

conexion.commit() # Guardamos los cambios definitivamente

# ==========================================
# FASE 4: AUDITORÍA Y REPORTE
# ==========================================

print("--- REPORTE DE VENTA REGISTRADA ---")
cursor.execute('''
    SELECT f.numero_factura, f.fecha, c.nombre_apellido, f.total_a_pagar 
    FROM Facturas f
    JOIN Clientes c ON f.numero_cliente = c.numero_cliente
''')
cabecera = cursor.fetchone()
print(f"Factura N°: {cabecera[0]} | Fecha: {cabecera[1]}")
print(f"Cliente: {cabecera[2]}")
print(f"Total a Pagar: ${cabecera[3]:.2f}")
print("-" * 35)

cursor.execute('''
    SELECT p.nombre_articulo, d.unidades, d.precio_unitario, d.total_linea
    FROM Detalle_Factura d
    JOIN Productos p ON d.codigo_articulo = p.codigo_articulo
    WHERE d.numero_factura = ?
''', (numero_factura_app,))

for fila in cursor.fetchall():
    print(f"{fila[1]}x {fila[0]}")
    print(f"Precio Unitario: ${fila[2]:.2f} -> Subtotal: ${fila[3]:.2f}")

conexion.close()