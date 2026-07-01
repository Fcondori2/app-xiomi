import sqlite3
from fpdf import FPDF

# 1. Conectamos a tu base de datos para extraer los datos
conexion = sqlite3.connect("sistema_ventas.db")
cursor = conexion.cursor()

cursor.execute('''
    SELECT f.numero_factura, f.fecha, c.numero_cliente, c.nombre_apellido, c.direccion_entrega, f.total_a_pagar
    FROM Facturas f
    JOIN Clientes c ON f.numero_cliente = c.numero_cliente
    WHERE f.numero_factura = 2031
''')
factura = cursor.fetchone()

cursor.execute('''
    SELECT p.nombre_articulo, d.unidades, d.precio_unitario, d.total_linea
    FROM Detalle_Factura d
    JOIN Productos p ON d.codigo_articulo = p.codigo_articulo
    WHERE d.numero_factura = 2031
''')
lineas = cursor.fetchall()
conexion.close()

# 2. Dibujamos el PDF con FPDF
pdf = FPDF()
pdf.add_page()

# Título Principal
pdf.set_font("Arial", 'B', 16)
pdf.cell(190, 10, txt="FACTURA COMERCIAL", ln=True, align='C')
pdf.ln(5)

# Cuadro con Datos del Cliente
pdf.set_font("Arial", size=11)
pdf.cell(190, 8, txt=f"Cliente Nro: {factura[2]} - {factura[3]}", ln=True)
pdf.cell(190, 8, txt=f"Direccion de Entrega: {factura[4]}", ln=True)
pdf.cell(190, 8, txt=f"Fecha: {factura[1]}   |   Factura Nro: {factura[0]}", ln=True)
pdf.ln(10)

# Encabezado de la tabla de artículos
pdf.set_font("Arial", 'B', 10)
pdf.cell(90, 10, "Descripcion del Articulo", border=1)
pdf.cell(25, 10, "Unidades", border=1, align='C')
pdf.cell(35, 10, "Precio Unit.", border=1, align='C')
pdf.cell(40, 10, "Subtotal", border=1, ln=True, align='C')

# Filas de los artículos cruzados
pdf.set_font("Arial", size=10)
for articulo, cantidad, precio, subtotal in lineas:
    pdf.cell(90, 10, articulo, border=1)
    pdf.cell(25, 10, str(cantidad), border=1, align='C')
    pdf.cell(35, 10, f"$ {precio:,.2f}", border=1, align='R')
    pdf.cell(40, 10, f"$ {subtotal:,.2f}", border=1, ln=True, align='R')

# Fila del Total
pdf.set_font("Arial", 'B', 12)
pdf.cell(150, 10, "TOTAL A PAGAR", border=1, align='R')
pdf.cell(40, 10, f"$ {factura[5]:,.2f}", border=1, ln=True, align='R')

# 3. Guardamos el archivo final
nombre_archivo = f"Factura_{factura[0]}.pdf"
pdf.output(nombre_archivo)

print(f"¡Éxito total! Se generó el documento: {nombre_archivo}")