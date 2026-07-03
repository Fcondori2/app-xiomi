import flet as ft
import sqlite3
import traceback  # <--- AGREGAR ESTA LÍNEA
# (Acá abajo siguen tus otros imports como fpdf, os, datetime, etc. dejalos tal cual)
from fpdf import FPDF
from datetime import date

# ==========================================
# CONFIGURACIÓN AUTOMÁTICA DE BASE DE DATOS
# ==========================================
def inicializar_base_datos():
    conexion = sqlite3.connect("sistema_ventas.db")
    cursor = conexion.cursor()
    # Crear tabla Clientes si no existe
    cursor.execute('''CREATE TABLE IF NOT EXISTS Clientes (
                        numero_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre_apellido TEXT NOT NULL,
                        direccion_entrega TEXT
                      )''')
    # Crear tabla Productos si no existe
    cursor.execute('''CREATE TABLE IF NOT EXISTS Productos (
                        codigo_articulo TEXT PRIMARY KEY,
                        nombre_articulo TEXT NOT NULL,
                        precio_unitario REAL NOT NULL
                      )''')
    # Crear tabla Facturas si no existe
    cursor.execute('''CREATE TABLE IF NOT EXISTS Facturas (
                        numero_factura INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT NOT NULL,
                        numero_cliente INTEGER,
                        total_a_pagar REAL NOT NULL,
                        FOREIGN KEY(numero_cliente) REFERENCES Clientes(numero_cliente)
                      )''')
    # Crear tabla Detalle_Factura si no existe
    cursor.execute('''CREATE TABLE IF NOT EXISTS Detalle_Factura (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_factura INTEGER,
        codigo_articulo TEXT,
        precio_unitario REAL,
        unidades INTEGER,
        total_linea REAL
    )''')
    # Inyectamos un cliente por defecto si la tabla está vacía para que la app no arranque en blanco
    cursor.execute("SELECT COUNT(*) FROM Clientes")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES ('CONSUMIDOR FINAL', 'PERICO')")
        
    conexion.commit()
    conexion.close()

# ==========================================
# MOTOR DE GENERACIÓN DE PDFs EN RUTA ELEGIDA
# ==========================================
def generar_pdf_facturas(ruta_destino, num_factura=None, fecha_consulta=None):
    conexion = sqlite3.connect("sistema_ventas.db")
    cursor = conexion.cursor()
    
    if num_factura:
        cursor.execute("SELECT numero_factura FROM Facturas WHERE numero_factura = ?", (num_factura,))
    elif fecha_consulta:
        cursor.execute("SELECT numero_factura FROM Facturas WHERE fecha = ?", (fecha_consulta,))
    else:
        return None

    facturas_encontradas = cursor.fetchall()
    if not facturas_encontradas:
        conexion.close()
        return None

    pdf = FPDF()
    def formato_ars(numero):
        return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    for (f_id,) in facturas_encontradas:
        cursor.execute('''SELECT f.numero_factura, f.fecha, c.nombre_apellido, c.direccion_entrega, f.total_a_pagar
                          FROM Facturas f JOIN Clientes c ON f.numero_cliente = c.numero_cliente
                          WHERE f.numero_factura = ?''', (f_id,))
        factura = cursor.fetchone()

        cursor.execute('''SELECT p.nombre_articulo, d.unidades, d.precio_unitario, d.total_linea
                          FROM Detalle_Factura d JOIN Productos p ON d.codigo_articulo = p.codigo_articulo
                          WHERE d.numero_factura = ?''', (f_id,))
        lineas = cursor.fetchall()

        pdf.add_page()
        
        # Encabezado Corporativo XIOMI
        pdf.set_xy(10, 15)
        pdf.set_text_color(12, 45, 92)
        pdf.set_font("Arial", 'B', 28)
        pdf.cell(90, 12, "XIOMI", ln=1)
        pdf.set_font("Arial", '', 14)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(90, 6, "Distribuidora", ln=1)
        
        pdf.set_xy(110, 15)
        pdf.set_fill_color(12, 45, 92)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 22)
        pdf.cell(90, 12, "FACTURA", fill=True, ln=2, align='C')
        
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(90, 10, f"Nro. {factura[0]}", border=1, fill=True, ln=2, align='C')
        pdf.set_draw_color(0, 0, 0)
        
        pdf.set_font("Arial", '', 11)
        pdf.cell(90, 8, f"Fecha: {factura[1]}", ln=1, align='C')
        pdf.ln(5)
        
        # Datos del Cliente
        pdf.set_xy(10, 42)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(20, 6, "Cliente:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(70, 6, f"{factura[2]}", ln=1)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(20, 6, "Direccion:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(70, 6, f"{factura[3]}", ln=1)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(25, 6, "Factura Nro:", ln=0)
        pdf.set_font("Arial", '', 10)
        pdf.cell(65, 6, f"{factura[0]}", ln=1)
        pdf.ln(10)

        # Tabla de Contenidos Estilizada
        pdf.set_fill_color(12, 45, 92)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 9, "Artículo", border=1, align='C', fill=True)
        pdf.cell(25, 9, "Cantidad", border=1, align='C', fill=True)
        pdf.cell(35, 9, "Precio Unitario", border=1, align='C', fill=True)
        pdf.cell(35, 9, "Importe Total", border=1, ln=True, align='C', fill=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        for art, cant, pre, tot in lineas:
            pdf.cell(95, 8, art, border='LR', align='C')
            pdf.cell(25, 8, str(cant), border='LR', align='C')
            pdf.cell(35, 8, formato_ars(pre), border='LR', align='C')
            pdf.cell(35, 8, formato_ars(tot), border='LR', ln=True, align='C')
            
        filas_vacias = max(0, 12 - len(lineas))
        for _ in range(filas_vacias):
            pdf.cell(95, 8, "", border='LR', align='C')
            pdf.cell(25, 8, "", border='LR', align='C')
            pdf.cell(35, 8, "", border='LR', align='C')
            pdf.cell(35, 8, "", border='LR', ln=True, align='C')
            
        pdf.cell(190, 0, "", border='T', ln=True)
        pdf.ln(5)
        
        # Totales y Pie de Página
        y_final = pdf.get_y()
        pdf.set_xy(10, y_final)
        pdf.set_fill_color(245, 245, 245)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(90, 6, "  Observaciones", border='LRT', ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(90, 10, "  Entrega inmediata en domicilio.", border='LRB', ln=True, fill=True)
        
        pdf.set_xy(110, y_final + 5)
        pdf.set_fill_color(230, 235, 245)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(40, 10, "Importe Total", border=1, align='C', fill=True)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(40, 10, f"$ {formato_ars(factura[4])}", border=1, ln=True, align='C', fill=True)

        pdf.set_y(258)
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(12, 45, 92)
        pdf.cell(0, 5, "Gracias por confiar en nosotros", align='C', ln=True)
        
        pdf.set_draw_color(150, 150, 150)
        pdf.line(10, 266, 200, 266)
        
        pdf.set_y(268)
        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, "XIOMI Distribuidora  |  Velez Sarsfield N°572, Perico-Jujuy  |  xiom.distribuidora@gmail.com", align='C', ln=True)
    
    pdf.output(ruta_destino)
    conexion.close()
    return True

def generar_pdf_reporte_dia(ruta_destino, fecha_consulta):
    conexion = sqlite3.connect("sistema_ventas.db")
    cursor = conexion.cursor()
    cursor.execute('''SELECT d.codigo_articulo, p.nombre_articulo, p.precio_unitario, SUM(d.unidades), SUM(d.total_linea)
                      FROM Detalle_Factura d 
                      JOIN Productos p ON d.codigo_articulo = p.codigo_articulo
                      JOIN Facturas f ON d.numero_factura = f.numero_factura
                      WHERE f.fecha = ?
                      GROUP BY d.codigo_articulo''', (fecha_consulta,))
    productos = cursor.fetchall()
    conexion.close()
    if not productos: return False

    pdf = FPDF()
    pdf.add_page()
    pdf.set_text_color(12, 45, 92)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="REPORTE DIARIO DE ARMADO Y VENTAS", ln=True, align='C')
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 8, txt=f"Fecha Operativa: {fecha_consulta}", ln=True, align='C')
    pdf.ln(10)

    pdf.set_fill_color(12, 45, 92)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(25, 10, "Codigo", border=1, align='C', fill=True)
    pdf.cell(65, 10, "Descripcion", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Precio Unit.", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Total Unid.", border=1, align='C', fill=True)
    pdf.cell(40, 10, "Total", border=1, ln=True, align='C', fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=10)
    unidades_t, dinero_t = 0, 0
    def formato_ars(numero): return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    for cod, nom, precio, unidades, total_producto in productos:
        pdf.cell(25, 9, str(cod), border='LR', align='C')
        pdf.cell(65, 9, str(nom), border='LR', align='C')
        pdf.cell(30, 9, f"$ {formato_ars(precio)}", border='LR', align='C')
        pdf.cell(30, 9, str(unidades), border='LR', align='C')
        pdf.cell(40, 9, f"$ {formato_ars(total_producto)}", border='LR', ln=True, align='C')
        unidades_t += unidades
        dinero_t += total_producto

    pdf.cell(190, 0, "", border='T', ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(120, 10, "TOTAL GENERAL DEL DIA:", border=1, align='R')
    pdf.cell(30, 10, str(unidades_t), border=1, align='C')
    pdf.cell(40, 10, f"$ {formato_ars(dinero_t)}", border=1, ln=True, align='C')
    
    pdf.output(ruta_destino)
    return True

def generar_pdf_reporte_unidades_totales(ruta_destino, fecha_inicio, fecha_fin):
    conexion = sqlite3.connect("sistema_ventas.db")
    cursor = conexion.cursor()
    cursor.execute('''SELECT d.codigo_articulo, p.nombre_articulo, p.precio_unitario, SUM(d.unidades), SUM(d.total_linea)
                      FROM Detalle_Factura d 
                      JOIN Productos p ON d.codigo_articulo = p.codigo_articulo
                      JOIN Facturas f ON d.numero_factura = f.numero_factura
                      WHERE f.fecha BETWEEN ? AND ?
                      GROUP BY d.codigo_articulo''', (fecha_inicio, fecha_fin))
    productos = cursor.fetchall()
    conexion.close()
    if not productos: return False

    pdf = FPDF()
    pdf.add_page()
    pdf.set_text_color(12, 45, 92)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="REPORTE CONSOLIDADO POR PERIODO", ln=True, align='C')
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 8, txt=f"Desde: {fecha_inicio} | Hasta: {fecha_fin}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_fill_color(12, 45, 92)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(25, 10, "Codigo", border=1, align='C', fill=True)
    pdf.cell(65, 10, "Descripcion", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Precio Unit.", border=1, align='C', fill=True)
    pdf.cell(30, 10, "Total Unid.", border=1, align='C', fill=True)
    pdf.cell(40, 10, "Total", border=1, ln=True, align='C', fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=10)
    unidades_t, dinero_t = 0, 0
    def formato_ars(numero): return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    for cod, nom, precio, unidades, total_producto in productos:
        pdf.cell(25, 9, str(cod), border='LR', align='C')
        pdf.cell(65, 9, str(nom), border='LR', align='C')
        pdf.cell(30, 9, f"$ {formato_ars(precio)}", border='LR', align='C')
        pdf.cell(30, 9, str(unidades), border='LR', align='C')
        pdf.cell(40, 9, f"$ {formato_ars(total_producto)}", border='LR', ln=True, align='C')
        unidades_t += unidades; dinero_t += total_producto

    pdf.cell(190, 0, "", border='T', ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(120, 10, "TOTAL GENERAL DISTRIBUIDO:", border=1, align='R')
    pdf.cell(30, 10, str(unidades_t), border=1, align='C')
    pdf.cell(40, 10, f"$ {formato_ars(dinero_t)}", border=1, ln=True, align='C')
    
    pdf.output(ruta_destino)
    return True

# ==========================================
# LA APLICACIÓN VISUAL (CON INTERFAZ MÓVIL)
# ==========================================
def main(page: ft.Page):
    page.title = "XIOMI Distribuidora"
    page.theme_mode = ft.ThemeMode.LIGHT
    
   # --- RED DE SEGURIDAD PARA ATRAPAR EL ERROR EN ANDROID ---
    try:
        inicializar_base_datos()
    except Exception as e:
        error_msj = f"ERROR AL ARRANCAR:\n{e}\n\n{traceback.format_exc()}"
        page.add(ft.Text(error_msj, color="red", size=14, weight="bold"))
        page.update()
        return # Frenamos la app aca para que puedas leer el error en tu pantalla

    carrito = {}

    # --- Trampa para atrapar errores ocultos en los botones ---
    def atrapar_error_interfaz(e):
        page.add(ft.Text(f"ERROR EN PANTALLA: {e.data}", color="red", size=20, weight="bold"))
        page.update()
    
    page.on_error = atrapar_error_interfaz
    # ----------------------------------------------------------

    # Memoria de control para saber que reporte disparo el guardado del celular
    operacion_actual = {}
    
        # El selector de archivos inteligente nativo para Android
    def al_elegir_ruta_guardado(e: ft.FilePickerResultEvent):
        if e.path:
            op = operacion_actual.get("tipo")
            exito = False
            if op == "factura":
                exito = generar_pdf_facturas(e.path, num_factura=operacion_actual.get("id"))
            elif op == "reporte_dia":
                exito = generar_pdf_reporte_dia(e.path, operacion_actual.get("fecha"))
            elif op == "consolidado":
                exito = generar_pdf_reporte_unidades_totales(e.path, operacion_actual.get("inicio"), operacion_actual.get("fin"))
            
            if exito:
                page.snack_bar = ft.SnackBar(ft.Text("✅ Archivo guardado y listo para compartir!"), bgcolor=ft.colors.GREEN_700)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("❌ No se encontraron datos para generar el PDF."), bgcolor=ft.colors.RED_700)
            page.snack_bar.open = True
            page.update()

    selector_archivos = ft.FilePicker(on_result=al_elegir_ruta_guardado)
    page.overlay.append(selector_archivos)

    def cambiar_pantalla(e):
        page.views.clear()
        
        # --- PANTALLA 1: INICIO ---
        if page.route == "/":
            try:
                conexion = sqlite3.connect("sistema_ventas.db")
                cursor = conexion.cursor()
                cursor.execute("SELECT COUNT(numero_factura), SUM(total_a_pagar) FROM Facturas")
                res = cursor.fetchone()
                total_pedidos = res[0] if res[0] else 0
                total_recaudado = res[1] if res[1] else 0.0
                conexion.close()
            except:
                total_pedidos, total_recaudado = 0, 0.0

            page.views.append(
                ft.View(
                    "/",
                    [
                        ft.AppBar(title=ft.Text("XIOMI Distribuidora", weight=ft.FontWeight.BOLD), bgcolor=ft.colors.BLUE_GREY_900, color=ft.colors.WHITE, center_title=True),
                        ft.Text("¡Hola, Franco!", size=24, weight=ft.FontWeight.BOLD),
                        ft.Card(content=ft.Container(padding=20, content=ft.Column([ft.Text("Resumen de Ventas", size=16, weight=ft.FontWeight.BOLD), ft.Divider(), ft.Text(f"Pedidos completados: {total_pedidos}"), ft.Text(f"Total recaudado: $ {total_recaudado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), size=18, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_700)]))),
                        ft.Container(height=10),
                        ft.ElevatedButton("LEVANTAR NUEVO PEDIDO", icon=ft.icons.SHOPPING_CART_CHECKOUT, on_click=lambda _: page.go("/carrito"), style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE, padding=20), width=float("inf")),
                        ft.Container(height=5),
                        ft.ElevatedButton("Agregar Nuevo Cliente", icon=ft.icons.PERSON_ADD, on_click=lambda _: page.go("/agregar_cliente"), style=ft.ButtonStyle(bgcolor=ft.colors.INDIGO_600, color=ft.colors.WHITE, padding=20), width=float("inf")),
                        ft.Container(height=5),
                        ft.ElevatedButton("Agregar Producto al Catálogo", icon=ft.icons.ADD_BOX, on_click=lambda _: page.go("/agregar_producto"), style=ft.ButtonStyle(bgcolor=ft.colors.TEAL_600, color=ft.colors.WHITE, padding=20), width=float("inf")),
                        ft.Container(height=5),
                        ft.ElevatedButton("Reportes y Facturación", icon=ft.icons.BAR_CHART, on_click=lambda _: page.go("/reportes"), style=ft.ButtonStyle(bgcolor=ft.colors.AMBER_800, color=ft.colors.WHITE, padding=20), width=float("inf")),
                    ], padding=20
                )
            )

        # --- PANTALLA 2: EL CARRITO ---
        elif page.route == "/carrito":
            texto_total = ft.Text("TOTAL: $ 0.00", size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
            lista_carrito_ui = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
            opciones_clientes = []
            catalogo = {}
            opciones_productos = []
            
            conexion = sqlite3.connect("sistema_ventas.db")
            cursor = conexion.cursor()
            cursor.execute("SELECT nombre_apellido FROM Clientes")
            for (nom,) in cursor.fetchall(): opciones_clientes.append(ft.dropdown.Option(text=nom))
            cursor.execute("SELECT codigo_articulo, nombre_articulo, precio_unitario FROM Productos")
            for cod, nom, precio in cursor.fetchall():
                catalogo[cod] = {"nombre": nom, "precio": precio}
                opciones_productos.append(ft.dropdown.Option(key=cod, text=f"{nom} | ${precio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")))
            conexion.close()

            dropdown_clientes = ft.Dropdown(label="1. Seleccionar Cliente", options=opciones_clientes, width=float("inf"))
            dropdown_productos = ft.Dropdown(label="Seleccionar Artículo", options=opciones_productos, expand=3)
            input_cantidad = ft.TextField(label="Cant.", keyboard_type=ft.KeyboardType.NUMBER, expand=1)

            def actualizar_carrito_ui():
                lista_carrito_ui.controls.clear()
                suma = 0
                for cod, item in carrito.items():
                    subtotal = item["cantidad"] * item["precio"]
                    suma += subtotal
                    def crear_eliminar(codigo_eliminar):
                        def eliminar(e):
                            del carrito[codigo_eliminar]
                            actualizar_carrito_ui()
                        return eliminar
                    subtotal_str = f"${subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    fila = ft.ListTile(leading=ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_600), title=ft.Text(f"{item['cantidad']}x {item['nombre']}", weight=ft.FontWeight.BOLD), subtitle=ft.Text(f"Subtotal: {subtotal_str}"), trailing=ft.IconButton(ft.icons.DELETE, icon_color=ft.colors.RED_400, on_click=crear_eliminar(cod)))
                    lista_carrito_ui.controls.append(fila)
                texto_total.value = f"TOTAL: $ {suma:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                page.update()

            def agregar_al_carrito(e):
                cod = dropdown_productos.value
                cant_texto = input_cantidad.value
                if not cod or not cant_texto: return
                try:
                    cant = int(cant_texto)
                    if cant <= 0: raise ValueError
                except: return
                if cod in carrito: carrito[cod]["cantidad"] += cant
                else: carrito[cod] = {"nombre": catalogo[cod]["nombre"], "precio": catalogo[cod]["precio"], "cantidad": cant}
                dropdown_productos.value = None
                input_cantidad.value = ""
                input_cantidad.focus()
                actualizar_carrito_ui()

            def confirmar_pedido(e):
                if not dropdown_clientes.value or not carrito: return
                nombre_cliente_val = dropdown_clientes.value
                fecha_hoy = date.today().strftime("%Y-%m-%d")
                total = sum(item["cantidad"] * item["precio"] for item in carrito.values())

                conexion = sqlite3.connect("sistema_ventas.db")
                cursor = conexion.cursor()
                cursor.execute("SELECT numero_cliente FROM Clientes WHERE nombre_apellido = ?", (nombre_cliente_val,))
                row_c = cursor.fetchone()
                num_cliente = row_c[0] if row_c else 1

                cursor.execute("SELECT MAX(numero_factura) FROM Facturas")
                max_id = cursor.fetchone()[0]
                nuevo_num = 1 if max_id is None else max_id + 1

                cursor.execute("INSERT INTO Facturas (numero_factura, fecha, numero_cliente, total_a_pagar) VALUES (?, ?, ?, ?)", (nuevo_num, fecha_hoy, num_cliente, total))
                for cod, item in carrito.items():
                    subtotal = item["cantidad"] * item["precio"]
                    cursor.execute("INSERT INTO Detalle_Factura (numero_factura, codigo_articulo, precio_unitario, unidades, total_linea) VALUES (?, ?, ?, ?, ?)", (nuevo_num, cod, item["precio"], item["cantidad"], subtotal))
                
                conexion.commit()
                conexion.close()
                carrito.clear()
                page.go("/")
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Pedido Nro {nuevo_num} registrado con éxito!"), bgcolor=ft.colors.GREEN_700)
                page.snack_bar.open = True
                page.update()

            bloque_carga = ft.Card(content=ft.Container(padding=15, content=ft.Column([dropdown_clientes, ft.Divider(), ft.Text("2. Cargar artículos al ticket", weight=ft.FontWeight.BOLD), ft.Row([dropdown_productos, input_cantidad]), ft.ElevatedButton("AGREGAR AL PEDIDO", icon=ft.icons.ADD_SHOPPING_CART, on_click=agregar_al_carrito, bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE, width=float("inf"))])))
            actualizar_carrito_ui()
            barra_inferior = ft.Container(bgcolor=ft.colors.BLUE_GREY_900, padding=20, border_radius=10, content=ft.Column([ft.Row([texto_total], alignment=ft.MainAxisAlignment.CENTER), ft.Container(height=10), ft.ElevatedButton("GUARDAR VENTA", icon=ft.icons.SAVE, on_click=confirmar_pedido, bgcolor=ft.colors.GREEN_600, color=ft.colors.WHITE, width=float("inf"), height=50)]))
            
            page.views.append(ft.View("/carrito", [ft.AppBar(title=ft.Text("Armar Pedido"), bgcolor=ft.colors.BLUE_GREY_900, color=ft.colors.WHITE, leading=ft.IconButton(ft.icons.ARROW_BACK, icon_color=ft.colors.WHITE, on_click=lambda _: page.go("/"))), bloque_carga, lista_carrito_ui, barra_inferior], padding=20))

        # --- PANTALLA 3: AGREGAR PRODUCTOS ---
        elif page.route == "/agregar_producto":
            input_codigo = ft.TextField(label="Código Único (Ej: ART-02)", width=float("inf"))
            input_nombre = ft.TextField(label="Descripción (Ej: ALFAJOR)", width=float("inf"))
            input_precio = ft.TextField(label="Precio Final", width=float("inf"), keyboard_type=ft.KeyboardType.NUMBER, prefix_text="$ ")

            def guardar_nuevo_producto(e):
                if not input_codigo.value or not input_nombre.value or not input_precio.value: return
                try:
                    precio_limpio = float(input_precio.value.replace(',', '.'))
                    codigo_limpio = input_codigo.value.strip().upper()
                    nombre_limpio = input_nombre.value.strip().upper()
                    conexion = sqlite3.connect("sistema_ventas.db")
                    cursor = conexion.cursor()
                    cursor.execute("INSERT INTO Productos (codigo_articulo, nombre_articulo, precio_unitario) VALUES (?, ?, ?)", (codigo_limpio, nombre_limpio, precio_limpio))
                    conexion.commit()
                    conexion.close()
                    input_codigo.value = ""; input_nombre.value = ""; input_precio.value = ""; input_codigo.focus()
                    page.snack_bar = ft.SnackBar(ft.Text("✅ ¡Producto guardado!"), bgcolor=ft.colors.GREEN_700)
                    page.snack_bar.open = True
                    page.update()
                except: pass

            page.views.append(ft.View("/agregar_producto", [ft.AppBar(title=ft.Text("Cargar Mercadería"), bgcolor=ft.colors.TEAL_800, color=ft.colors.WHITE, leading=ft.IconButton(ft.icons.ARROW_BACK, icon_color=ft.colors.WHITE, on_click=lambda _: page.go("/"))), ft.Text("Nuevo Artículo", size=20, weight=ft.FontWeight.BOLD), input_codigo, input_nombre, input_precio, ft.Container(height=20), ft.ElevatedButton("GUARDAR PRODUCTO", icon=ft.icons.SAVE, on_click=guardar_nuevo_producto, style=ft.ButtonStyle(bgcolor=ft.colors.TEAL_600, color=ft.colors.WHITE, padding=20), width=float("inf"))], padding=20))

        # --- PANTALLA 4: AGREGAR CLIENTE ---
        elif page.route == "/agregar_cliente":
            input_nombre = ft.TextField(label="Nombre y Apellido", width=float("inf"))
            input_direccion = ft.TextField(label="Dirección de Entrega", width=float("inf"))

            def guardar_nuevo_cliente(e):
                if not input_nombre.value or not input_direccion.value: return
                nombre_limpio = input_nombre.value.strip().upper()
                direccion_limpia = input_direccion.value.strip()
                conexion = sqlite3.connect("sistema_ventas.db")
                cursor = conexion.cursor()
                cursor.execute("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES (?, ?)", (nombre_limpio, direccion_limpia))
                conexion.commit()
                conexion.close()
                input_nombre.value = ""; input_direccion.value = ""; input_nombre.focus()
                page.snack_bar = ft.SnackBar(ft.Text("✅ Cliente guardado con éxito!"), bgcolor=ft.colors.GREEN_700)
                page.snack_bar.open = True
                page.update()

            page.views.append(ft.View("/agregar_cliente", [ft.AppBar(title=ft.Text("Directorio de Clientes"), bgcolor=ft.colors.INDIGO_800, color=ft.colors.WHITE, leading=ft.IconButton(ft.icons.ARROW_BACK, icon_color=ft.colors.WHITE, on_click=lambda _: page.go("/"))), ft.Text("Nuevo Cliente", size=20, weight=ft.FontWeight.BOLD), input_nombre, input_direccion, ft.Container(height=20), ft.ElevatedButton("GUARDAR CLIENTE", icon=ft.icons.SAVE, on_click=guardar_nuevo_cliente, style=ft.ButtonStyle(bgcolor=ft.colors.INDIGO_600, color=ft.colors.WHITE, padding=20), width=float("inf"))], padding=20))

        # --- PANTALLA 5: REPORTES ---
        elif page.route == "/reportes":
            fecha_hoy_str = date.today().strftime("%Y-%m-%d")
            input_num_factura = ft.TextField(label="Nro de Factura", keyboard_type=ft.KeyboardType.NUMBER)
            input_fecha_factura = ft.TextField(label="Fecha de Lote (YYYY-MM-DD)", value=fecha_hoy_str)
            input_fecha_reporte = ft.TextField(label="Fecha de Armado (YYYY-MM-DD)", value=fecha_hoy_str)
            input_fecha_inicio = ft.TextField(label="Fecha Inicio", value=fecha_hoy_str, expand=1)
            input_fecha_fin = ft.TextField(label="Fecha Fin", value=fecha_hoy_str, expand=1)

            # Disparadores de guardado nativo
            def click_factura_individual(e):
                if not input_num_factura.value: return
                operacion_actual.clear()
                operacion_actual.update({"tipo": "factura", "id": int(input_num_factura.value)})
                selector_archivos.save_file(file_name=f"Factura_{input_num_factura.value}.pdf")

            def click_lote_facturas(e):
                if not input_fecha_factura.value: return
                operacion_actual.clear()
                operacion_actual.update({"tipo": "factura", "id": None, "fecha": input_fecha_factura.value.strip()})
                selector_archivos.save_file(file_name=f"Lote_Facturas_{input_fecha_factura.value.strip()}.pdf")

            def click_reporte_diario(e):
                if not input_fecha_reporte.value: return
                operacion_actual.clear()
                operacion_actual.update({"tipo": "reporte_dia", "fecha": input_fecha_reporte.value.strip()})
                selector_archivos.save_file(file_name=f"Reporte_Armado_{input_fecha_reporte.value.strip()}.pdf")

            def click_consolidado_periodo(e):
                if not input_fecha_inicio.value or not input_fecha_fin.value: return
                operacion_actual.clear()
                operacion_actual.update({"tipo": "consolidado", "inicio": input_fecha_inicio.value.strip(), "fin": input_fecha_fin.value.strip()})
                selector_archivos.save_file(file_name=f"Reporte_Consolidado_{input_fecha_inicio.value.strip()}_al_{input_fecha_fin.value.strip()}.pdf")

            tarjeta_facturas = ft.Card(content=ft.Container(padding=20, content=ft.Column([ft.Text("Impresión de Facturas", weight=ft.FontWeight.BOLD), input_num_factura, ft.ElevatedButton("Generar Factura Individual", icon=ft.icons.PICTURE_AS_PDF, on_click=click_factura_individual, bgcolor=ft.colors.BLUE_GREY_700, color=ft.colors.WHITE, width=float("inf")), ft.Divider(), input_fecha_factura, ft.ElevatedButton("Imprimir TODAS las del día", icon=ft.icons.LIBRARY_BOOKS, on_click=click_lote_facturas, bgcolor=ft.colors.INDIGO_600, color=ft.colors.WHITE, width=float("inf"))])))
            tarjeta_reporte_dia = ft.Card(content=ft.Container(padding=20, content=ft.Column([ft.Text("Resumen Diario de Armado", weight=ft.FontWeight.BOLD), input_fecha_reporte, ft.ElevatedButton("Generar Reporte del Día", icon=ft.icons.FORMAT_LIST_BULLETED, on_click=click_reporte_diario, bgcolor=ft.colors.AMBER_800, color=ft.colors.WHITE, width=float("inf"))])))
            tarjeta_reporte_consolidado = ft.Card(content=ft.Container(padding=20, content=ft.Column([ft.Text("Reporte Consolidado por Período", weight=ft.FontWeight.BOLD), ft.Row([input_fecha_inicio, input_fecha_fin]), ft.ElevatedButton("Generar Consolidado", icon=ft.icons.ANALYTICS, on_click=click_consolidado_periodo, bgcolor=ft.colors.TEAL_700, color=ft.colors.WHITE, width=float("inf"))])))

            page.views.append(ft.View("/reportes", [ft.AppBar(title=ft.Text("Facturación y Reportes"), bgcolor=ft.colors.AMBER_800, color=ft.colors.WHITE, leading=ft.IconButton(ft.icons.ARROW_BACK, icon_color=ft.colors.WHITE, on_click=lambda _: page.go("/"))), ft.Container(height=10), tarjeta_facturas, ft.Container(height=10), tarjeta_reporte_dia, ft.Container(height=10), tarjeta_reporte_consolidado], padding=20, scroll=ft.ScrollMode.AUTO))

        page.update()

    # --- EL ENRUTADOR SEGURO ---
    def enrutador_seguro(e):
        try:
            cambiar_pantalla(e)
        except Exception as ex:
            page.views.clear()
            page.add(ft.Text(f"ERROR OCULTO: {ex}", color="red", size=22, weight="bold"))
            page.update()

    page.on_route_change = enrutador_seguro
    page.go("/iniciando")
    page.go("/")

ft.app(target=main)
