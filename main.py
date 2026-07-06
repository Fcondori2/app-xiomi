import flet as ft
import sqlite3
import time
import os
import traceback
from fpdf import FPDF
from datetime import date

# ==========================================
# 1. HERRAMIENTAS DE BASE DE DATOS (ANDROID SAFE)
# ==========================================
# Esto guarda la base de datos en la bóveda segura del celular
carpeta_segura = os.environ.get("FLET_APP_STORAGE_DATA", ".")
ruta_db = os.path.join(carpeta_segura, "sistema_ventas.db")

def ejecutar_db(query, parametros=(), fetch=False, fetchall=False):
    conexion = sqlite3.connect(ruta_db)
    cursor = conexion.cursor()
    cursor.execute(query, parametros)
    if fetch:
        resultado = cursor.fetchall() if fetchall else cursor.fetchone()
        conexion.close()
        return resultado
    conexion.commit()
    conexion.close()

def inicializar_base_datos():
    ejecutar_db('''CREATE TABLE IF NOT EXISTS Clientes (numero_cliente INTEGER PRIMARY KEY AUTOINCREMENT, nombre_apellido TEXT NOT NULL, direccion_entrega TEXT)''')
    ejecutar_db('''CREATE TABLE IF NOT EXISTS Productos (codigo_articulo TEXT PRIMARY KEY, nombre_articulo TEXT NOT NULL, precio_unitario REAL NOT NULL)''')
    ejecutar_db('''CREATE TABLE IF NOT EXISTS Facturas (numero_factura INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, numero_cliente INTEGER, total_a_pagar REAL NOT NULL, FOREIGN KEY(numero_cliente) REFERENCES Clientes(numero_cliente))''')
    ejecutar_db('''CREATE TABLE IF NOT EXISTS Detalle_Factura (id INTEGER PRIMARY KEY AUTOINCREMENT, numero_factura INTEGER, codigo_articulo TEXT, precio_unitario REAL, unidades INTEGER, total_linea REAL)''')
    if ejecutar_db("SELECT COUNT(*) FROM Clientes", fetch=True)[0] == 0:
        ejecutar_db("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES ('CONSUMIDOR FINAL', 'PERICO')")

# ==========================================
# 2. MOTOR DE REPORTES PDF 
# ==========================================
def formato_ars(numero): 
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def generar_pdf_facturas(ruta_destino, num_factura=None, fecha_consulta=None):
    if num_factura:
        facturas = ejecutar_db("SELECT numero_factura FROM Facturas WHERE numero_factura = ?", (num_factura,), fetch=True, fetchall=True)
    elif fecha_consulta:
        facturas = ejecutar_db("SELECT numero_factura FROM Facturas WHERE fecha = ?", (fecha_consulta,), fetch=True, fetchall=True)
    else: return False
    if not facturas: return False
    pdf = FPDF()
    for (f_id,) in facturas:
        factura = ejecutar_db('''SELECT f.numero_factura, f.fecha, c.nombre_apellido, c.direccion_entrega, f.total_a_pagar FROM Facturas f JOIN Clientes c ON f.numero_cliente = c.numero_cliente WHERE f.numero_factura = ?''', (f_id,), fetch=True)
        lineas = ejecutar_db('''SELECT p.nombre_articulo, d.unidades, d.precio_unitario, d.total_linea FROM Detalle_Factura d JOIN Productos p ON d.codigo_articulo = p.codigo_articulo WHERE d.numero_factura = ?''', (f_id,), fetch=True, fetchall=True)
        pdf.add_page()
        pdf.set_xy(10, 15); pdf.set_text_color(50, 150, 255); pdf.set_font("Arial", 'B', 28); pdf.cell(90, 12, "XIOMI", ln=1)
        pdf.set_font("Arial", '', 14); pdf.set_text_color(100, 100, 100); pdf.cell(90, 6, "Distribuidora", ln=1)
        pdf.set_xy(110, 15); pdf.set_fill_color(173, 216, 230); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 22)
        pdf.cell(90, 12, "FACTURA", fill=True, ln=2, align='C')
        pdf.set_fill_color(255, 255, 255); pdf.set_text_color(0, 0, 0); pdf.set_draw_color(255, 255, 255); pdf.set_font("Arial", 'B', 14)
        pdf.cell(90, 10, f"Nro. {factura[0]}", border=1, fill=True, ln=2, align='C')
        pdf.set_draw_color(0, 0, 0); pdf.set_font("Arial", '', 11); pdf.cell(90, 8, f"Fecha: {factura[1]}", ln=1, align='C')
        pdf.ln(5)
        pdf.set_xy(10, 42); pdf.set_font("Arial", 'B', 10); pdf.cell(20, 6, "Cliente:", ln=0); pdf.set_font("Arial", '', 10); pdf.cell(70, 6, f"{factura[2]}", ln=1)
        pdf.set_font("Arial", 'B', 10); pdf.cell(20, 6, "Direccion:", ln=0); pdf.set_font("Arial", '', 10); pdf.cell(70, 6, f"{factura[3]}", ln=1)
        pdf.ln(10)
        pdf.set_fill_color(173, 216, 230); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 9, "Artículo", border=1, align='C', fill=True); pdf.cell(25, 9, "Cantidad", border=1, align='C', fill=True)
        pdf.cell(35, 9, "Precio Unitario", border=1, align='C', fill=True); pdf.cell(35, 9, "Importe Total", border=1, ln=True, align='C', fill=True)
        pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 10)
        for art, cant, pre, tot in lineas:
            pdf.cell(95, 8, art, border='LR', align='C'); pdf.cell(25, 8, str(cant), border='LR', align='C')
            pdf.cell(35, 8, formato_ars(pre), border='LR', align='C'); pdf.cell(35, 8, formato_ars(tot), border='LR', ln=True, align='C')
        for _ in range(max(0, 12 - len(lineas))):
            pdf.cell(95, 8, "", border='LR', align='C'); pdf.cell(25, 8, "", border='LR', align='C'); pdf.cell(35, 8, "", border='LR', align='C'); pdf.cell(35, 8, "", border='LR', ln=True, align='C')
        pdf.cell(190, 0, "", border='T', ln=True); pdf.ln(5)
        y_final = pdf.get_y()
        pdf.set_xy(110, y_final + 5); pdf.set_fill_color(240, 248, 255); pdf.set_font("Arial", 'B', 11)
        pdf.cell(40, 10, "Importe Total", border=1, align='C', fill=True)
        pdf.set_fill_color(255, 255, 255); pdf.cell(40, 10, f"$ {formato_ars(factura[4])}", border=1, ln=True, align='C', fill=True)
        pdf.set_y(258); pdf.set_font("Arial", 'B', 10); pdf.set_text_color(50, 150, 255); pdf.cell(0, 5, "Gracias por confiar en nosotros", align='C', ln=True)
        pdf.set_draw_color(150, 150, 150); pdf.line(10, 266, 200, 266)
        pdf.set_y(268); pdf.set_font("Arial", '', 9); pdf.set_text_color(150, 150, 150); pdf.cell(0, 5, "XIOMI Distribuidora  |  Velez Sarsfield N°572, Perico-Jujuy  |  xiom.distribuidora@gmail.com", align='C', ln=True)
    pdf.output(ruta_destino)
    return True

def generar_reporte_generico(ruta_destino, query, parametros, titulo, subtitulo):
    productos = ejecutar_db(query, parametros, fetch=True, fetchall=True)
    if not productos: return False
    pdf = FPDF(); pdf.add_page()
    pdf.set_text_color(50, 150, 255); pdf.set_font("Arial", 'B', 16); pdf.cell(190, 10, txt=titulo, ln=True, align='C')
    pdf.set_text_color(100, 100, 100); pdf.set_font("Arial", size=11); pdf.cell(190, 8, txt=subtitulo, ln=True, align='C'); pdf.ln(10)
    pdf.set_fill_color(173, 216, 230); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 10)
    for col, w in [("Codigo", 25), ("Descripcion", 65), ("Precio Unit.", 30), ("Total Unid.", 30)]: pdf.cell(w, 10, col, border=1, align='C', fill=True)
    pdf.cell(40, 10, "Total", border=1, ln=True, align='C', fill=True)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", size=10)
    unidades_t, dinero_t = 0, 0
    for cod, nom, pre, uni, tot in productos:
        pdf.cell(25, 9, str(cod), border='LR', align='C'); pdf.cell(65, 9, str(nom), border='LR', align='C')
        pdf.cell(30, 9, f"$ {formato_ars(pre)}", border='LR', align='C'); pdf.cell(30, 9, str(uni), border='LR', align='C')
        pdf.cell(40, 9, f"$ {formato_ars(tot)}", border='LR', ln=True, align='C')
        unidades_t += uni; dinero_t += tot
    pdf.cell(190, 0, "", border='T', ln=True); pdf.ln(5)
    pdf.set_font("Arial", 'B', 11); pdf.cell(120, 10, "TOTAL GENERAL:", border=1, align='R')
    pdf.cell(30, 10, str(unidades_t), border=1, align='C'); pdf.cell(40, 10, f"$ {formato_ars(dinero_t)}", border=1, ln=True, align='C')
    pdf.output(ruta_destino)
    return True

# ==========================================
# 3. INTERFAZ GRÁFICA PROFESIONAL Y BLINDADA
# ==========================================
def main(page: ft.Page):
    try:
        page.title = "XIOMI Distribuidora"
        page.theme_mode = ft.ThemeMode.LIGHT
        
        # COLORES Y BOTONES CON MAYÚSCULA PARA GITHUB Y ANDROID
        estilo_btn_principal = ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, padding=20)
        estilo_btn_secundario = ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_600, color=ft.Colors.WHITE, padding=20)

        inicializar_base_datos()
            
        carrito = {}
        estado_carrito = {"editando": False, "id_factura": None, "cargado": False}

        def cambiar_pantalla(e):
            try:
                page.views.clear()
                
                if page.route == "/":
                    page.views.append(ft.View("/", [
                        ft.AppBar(title=ft.Text("XIOMI Distribuidora", weight="bold"), bgcolor=ft.Colors.BLUE_GREY_900, color=ft.Colors.WHITE, center_title=True),
                        ft.Container(height=15),
                        ft.Text("Menú Principal", size=24, weight="bold", color=ft.Colors.BLUE_GREY_900),
                        ft.ElevatedButton("Gestión de Ventas del Día", icon=ft.Icons.POINT_OF_SALE, on_click=lambda _: page.go("/pedidos_dia"), style=estilo_btn_principal, width=float("inf")),
                        ft.ElevatedButton("Gestión de Clientes", icon=ft.Icons.PEOPLE, on_click=lambda _: page.go("/agregar_cliente"), style=estilo_btn_secundario, width=float("inf")),
                        ft.ElevatedButton("Gestión de Productos", icon=ft.Icons.INVENTORY, on_click=lambda _: page.go("/agregar_producto"), style=estilo_btn_secundario, width=float("inf")),
                        ft.ElevatedButton("Reportes y Facturación", icon=ft.Icons.BAR_CHART, on_click=lambda _: page.go("/reportes"), style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_800, color=ft.Colors.WHITE, padding=20), width=float("inf")),
                    ], padding=20))

                elif page.route == "/pedidos_dia":
                    hoy = date.today().strftime("%Y-%m-%d")
                    tabla_pedidos = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["Nro", "Cliente", "Total", "X"]], rows=[])
                    def ref_pedidos():
                        try:
                            tabla_pedidos.rows.clear()
                            filas = ejecutar_db("SELECT f.numero_factura, c.nombre_apellido, f.total_a_pagar FROM Facturas f JOIN Clientes c ON f.numero_cliente = c.numero_cliente WHERE f.fecha = ?", (hoy,), fetch=True, fetchall=True)
                            if filas:
                                for id_f, cli, tot in filas:
                                    def borrar_p(e, num=id_f):
                                        ejecutar_db("DELETE FROM Detalle_Factura WHERE numero_factura=?", (num,))
                                        ejecutar_db("DELETE FROM Facturas WHERE numero_factura=?", (num,))
                                        ref_pedidos()
                                    def editar_p(e, num=id_f):
                                        estado_carrito["editando"] = True; estado_carrito["id_factura"] = num; estado_carrito["cargado"] = False; carrito.clear(); page.go("/carrito")
                                    tabla_pedidos.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(id_f))), ft.DataCell(ft.Text(cli)), ft.DataCell(ft.Text(f"${formato_ars(tot)}")), ft.DataCell(ft.Row([ft.IconButton(ft.Icons.EDIT, icon_color=ft.Colors.BLUE, on_click=editar_p), ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=borrar_p)]))]))
                            tabla_pedidos.update()
                        except: pass
                    def ir_nuevo_pedido(e):
                        estado_carrito["editando"] = False; estado_carrito["id_factura"] = None; estado_carrito["cargado"] = False; carrito.clear(); page.go("/carrito")
                    page.views.append(ft.View("/pedidos_dia", [ft.AppBar(title=ft.Text("Panel de Ventas"), bgcolor=ft.Colors.BLUE_GREY_900, color=ft.Colors.WHITE, leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda _: page.go("/"))), ft.ElevatedButton("+ ARMAR NUEVO PEDIDO", icon=ft.Icons.ADD_SHOPPING_CART, on_click=ir_nuevo_pedido, style=estilo_btn_principal, width=float("inf")), ft.Divider(), ft.Text(f"Tickets de hoy ({hoy}):", weight="bold"), ft.Column([tabla_pedidos], scroll="auto", expand=True)], padding=20)); ref_pedidos()

                elif page.route == "/carrito":
                    texto_total = ft.Text("TOTAL: $ 0.00", size=22, weight="bold", color=ft.Colors.WHITE)
                    lista_carrito_ui = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
                    opciones_cli = [ft.dropdown.Option(text=nom[0]) for nom in ejecutar_db("SELECT nombre_apellido FROM Clientes", fetch=True, fetchall=True)]
                    cat = {cod: {"nombre": nom, "precio": pre} for cod, nom, pre in ejecutar_db("SELECT codigo_articulo, nombre_articulo, precio_unitario FROM Productos", fetch=True, fetchall=True)}
                    opciones_prod = [ft.dropdown.Option(key=cod, text=f"{v['nombre']} | ${formato_ars(v['precio'])}") for cod, v in cat.items()]
                    dd_clientes = ft.Dropdown(label="1. Seleccionar Cliente", options=opciones_cli, expand=True)
                    dd_productos = ft.Dropdown(label="Seleccionar Artículo", options=opciones_prod, expand=3)
                    inp_cant = ft.TextField(label="Cant.", keyboard_type=ft.KeyboardType.NUMBER, expand=1)

                    campo_nom_cli = ft.TextField(label="Nombre", width=300); campo_dir_cli = ft.TextField(label="Dirección", width=300)
                    def guardar_cliente_rapido(e):
                        if not campo_nom_cli.value: return
                        nom_nuevo = campo_nom_cli.value.upper()
                        ejecutar_db("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES (?, ?)", (nom_nuevo, campo_dir_cli.value.upper()))
                        dd_clientes.options.append(ft.dropdown.Option(text=nom_nuevo)); dd_clientes.value = nom_nuevo; dd_clientes.update()
                        campo_nom_cli.value = ""; campo_dir_cli.value = ""; page.dialog.open = False; page.update()
                    page.dialog = ft.AlertDialog(title=ft.Text("Agregar Cliente"), content=ft.Column([campo_nom_cli, campo_dir_cli], tight=True), actions=[ft.TextButton("Guardar", on_click=guardar_cliente_rapido)])

                    if estado_carrito["editando"]:
                        id_fac = estado_carrito["id_factura"]
                        cliente_actual = ejecutar_db("SELECT c.nombre_apellido FROM Facturas f JOIN Clientes c ON f.numero_cliente = c.numero_cliente WHERE f.numero_factura = ?", (id_fac,), fetch=True)
                        if cliente_actual: dd_clientes.value = cliente_actual[0]
                        if not estado_carrito["cargado"]:
                            detalles = ejecutar_db("SELECT d.codigo_articulo, p.nombre_articulo, d.precio_unitario, d.unidades FROM Detalle_Factura d JOIN Productos p ON d.codigo_articulo = p.codigo_articulo WHERE d.numero_factura = ?", (id_fac,), fetch=True, fetchall=True)
                            carrito.clear()
                            for cod, nom, pre, uni in detalles: carrito[cod] = {"nombre": nom, "precio": pre, "cantidad": uni}
                            estado_carrito["cargado"] = True

                    def act_carrito():
                        lista_carrito_ui.controls.clear()
                        suma = sum(item["cantidad"] * item["precio"] for item in carrito.values())
                        for cod, item in carrito.items():
                            def borrar(e, c=cod): del carrito[c]; act_carrito()
                            lista_carrito_ui.controls.append(ft.ListTile(leading=ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN), title=ft.Text(f"{item['cantidad']}x {item['nombre']}", weight="bold"), subtitle=ft.Text(f"Subtotal: ${formato_ars(item['cantidad'] * item['precio'])}"), trailing=ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=borrar)))
                        texto_total.value = f"TOTAL: $ {formato_ars(suma)}"; page.update()

                    def agregar(e):
                        if not dd_productos.value or not inp_cant.value.isdigit() or int(inp_cant.value) <= 0: return
                        cod, cant = dd_productos.value, int(inp_cant.value)
                        carrito[cod] = {"nombre": cat[cod]["nombre"], "precio": cat[cod]["precio"], "cantidad": carrito.get(cod, {}).get("cantidad", 0) + cant}
                        dd_productos.value = None; inp_cant.value = ""; act_carrito()

                    def confirmar(e):
                        if not dd_clientes.value or not carrito: return
                        num_cli = ejecutar_db("SELECT numero_cliente FROM Clientes WHERE nombre_apellido = ?", (dd_clientes.value,), fetch=True)[0]
                        tot = sum(item["cantidad"] * item["precio"] for item in carrito.values())
                        if estado_carrito["editando"]:
                            id_fac = estado_carrito["id_factura"]
                            ejecutar_db("UPDATE Facturas SET numero_cliente = ?, total_a_pagar = ? WHERE numero_factura = ?", (num_cli, tot, id_fac))
                            ejecutar_db("DELETE FROM Detalle_Factura WHERE numero_factura = ?", (id_fac,))
                            for cod, item in carrito.items(): ejecutar_db("INSERT INTO Detalle_Factura (numero_factura, codigo_articulo, precio_unitario, unidades, total_linea) VALUES (?, ?, ?, ?, ?)", (id_fac, cod, item["precio"], item["cantidad"], item["cantidad"] * item["precio"]))
                        else:
                            ejecutar_db("INSERT INTO Facturas (fecha, numero_cliente, total_a_pagar) VALUES (?, ?, ?)", (date.today().strftime("%Y-%m-%d"), num_cli, tot))
                            nuevo_num = ejecutar_db("SELECT MAX(numero_factura) FROM Facturas", fetch=True)[0]
                            for cod, item in carrito.items(): ejecutar_db("INSERT INTO Detalle_Factura (numero_factura, codigo_articulo, precio_unitario, unidades, total_linea) VALUES (?, ?, ?, ?, ?)", (nuevo_num, cod, item["precio"], item["cantidad"], item["cantidad"] * item["precio"]))
                        carrito.clear(); estado_carrito["editando"] = False; page.go("/pedidos_dia")

                    tit_pantalla = f"CORRIGIENDO TICKET NRO {estado_carrito['id_factura']}" if estado_carrito["editando"] else "Armar Pedido"
                    color_fondo = ft.Colors.BLUE_800 if estado_carrito["editando"] else ft.Colors.BLUE_GREY_900
                    bloque = ft.Card(content=ft.Container(padding=15, content=ft.Column([ft.Row([dd_clientes, ft.IconButton(icon=ft.Icons.PERSON_ADD, icon_color=ft.Colors.BLUE, on_click=lambda _: setattr(page.dialog, 'open', True) or page.update())]), ft.Text("2. Agregar artículos", weight="bold"), ft.Row([dd_productos, inp_cant]), ft.ElevatedButton("AGREGAR", icon=ft.Icons.ADD, on_click=agregar, width=float("inf"))])))
                    pie = ft.Container(bgcolor=color_fondo, padding=20, border_radius=10, content=ft.Column([ft.Row([texto_total], alignment="center"), ft.ElevatedButton("GUARDAR VENTA", icon=ft.Icons.SAVE, on_click=confirmar, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, width=float("inf"), height=50)]))
                    page.views.append(ft.View("/carrito", [ft.AppBar(title=ft.Text(tit_pantalla), bgcolor=color_fondo, color=ft.Colors.WHITE, leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda _: page.go("/pedidos_dia"))), bloque, lista_carrito_ui, pie], padding=20)); act_carrito()

                elif page.route == "/agregar_producto":
                    inp_cod = ft.TextField(label="Código (ART-01)", width=float("inf")); inp_nom = ft.TextField(label="Descripción", width=float("inf")); inp_pre = ft.TextField(label="Precio ($)", keyboard_type="number", width=float("inf"))
                    tabla_prod = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["Cod.", "Desc", "Prec", "X"]], rows=[])
                    def ref_prod():
                        try:
                            tabla_prod.rows.clear()
                            filas = ejecutar_db("SELECT codigo_articulo, nombre_articulo, precio_unitario FROM Productos", fetch=True, fetchall=True)
                            if filas:
                                for c, n, p in filas:
                                    def borrar_p(e, cod=c): ejecutar_db("DELETE FROM Productos WHERE codigo_articulo=?", (cod,)); ref_prod()
                                    tabla_prod.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(c))), ft.DataCell(ft.Text(str(n))), ft.DataCell(ft.Text(f"${formato_ars(p)}")), ft.DataCell(ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=borrar_p))]))
                            tabla_prod.update()
                        except: pass
                    def guardar_p(e):
                        if inp_cod.value and inp_nom.value and inp_pre.value:
                            ejecutar_db("INSERT INTO Productos VALUES (?, ?, ?)", (inp_cod.value.strip().upper(), inp_nom.value.strip().upper(), float(inp_pre.value.replace(',','.'))))
                            inp_cod.value = ""; inp_nom.value = ""; inp_pre.value = ""; ref_prod()
                    page.views.append(ft.View("/agregar_producto", [ft.AppBar(title=ft.Text("Catálogo"), bgcolor=ft.Colors.TEAL_800, color=ft.Colors.WHITE, leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda _: page.go("/"))), inp_cod, inp_nom, inp_pre, ft.ElevatedButton("GUARDAR", icon=ft.Icons.SAVE, on_click=guardar_p, style=estilo_btn_secundario, width=float("inf")), ft.Divider(), ft.Column([tabla_prod], scroll="auto", expand=True)], padding=20)); ref_prod()

                elif page.route == "/agregar_cliente":
                    inp_nom_c = ft.TextField(label="Nombre", width=float("inf")); inp_dir_c = ft.TextField(label="Dirección", width=float("inf"))
                    tabla_cli = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["ID", "Nombre", "Dirección", "X"]], rows=[])
                    def ref_cli():
                        try:
                            tabla_cli.rows.clear()
                            filas = ejecutar_db("SELECT numero_cliente, nombre_apellido, direccion_entrega FROM Clientes", fetch=True, fetchall=True)
                            if filas:
                                for id_c, n, d in filas:
                                    def borrar_c(e, num=id_c): ejecutar_db("DELETE FROM Clientes WHERE numero_cliente=?", (num,)); ref_cli()
                                    tabla_cli.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(id_c))), ft.DataCell(ft.Text(str(n))), ft.DataCell(ft.Text(str(d if d else ""))), ft.DataCell(ft.IconButton(ft.Icons.DELETE, icon_color=ft.Colors.RED, on_click=borrar_c))]))
                            tabla_cli.update()
                        except: pass
                    def guardar_c(e):
                        if inp_nom_c.value:
                            ejecutar_db("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES (?, ?)", (inp_nom_c.value.upper(), inp_dir_c.value))
                            inp_nom_c.value = ""; inp_dir_c.value = ""; ref_cli()
                    page.views.append(ft.View("/agregar_cliente", [ft.AppBar(title=ft.Text("Directorio"), bgcolor=ft.Colors.INDIGO_800, color=ft.Colors.WHITE, leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda _: page.go("/"))), inp_nom_c, inp_dir_c, ft.ElevatedButton("GUARDAR", icon=ft.Icons.SAVE, on_click=guardar_c, style=estilo_btn_secundario, width=float("inf")), ft.Divider(), ft.Column([tabla_cli], scroll="auto", expand=True)], padding=20)); ref_cli()

                elif page.route == "/reportes":
                    page.views.append(ft.View("/reportes", [
                        ft.AppBar(title=ft.Text("Reportes"), bgcolor=ft.Colors.AMBER_800, color=ft.Colors.WHITE, leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=lambda _: page.go("/"))),
                        ft.Text("Los reportes en PDF estarán disponibles próximamente en la versión móvil.", weight="bold", color=ft.Colors.RED)
                    ], padding=20, scroll="auto"))

                page.update()
                
            except Exception as ex:
                error_pila = traceback.format_exc()
                page.views.clear()
                page.views.append(
                    ft.View(
                        "/error",
                        [
                            ft.Text("¡ERROR AL DIBUJAR PANTALLA!", color=ft.Colors.WHITE, bgcolor=ft.Colors.RED, size=24, weight="bold"),
                            ft.Text("Sacale captura a esto por favor:", color=ft.Colors.BLACK, weight="bold"),
                            ft.Text(error_pila, color=ft.Colors.RED, selectable=True)
                        ],
                        padding=20, scroll="auto"
                    )
                )
                page.update()

        page.on_route_change = cambiar_pantalla
        page.go("/")

    except Exception as e:
        error_pila = traceback.format_exc()
        page.clean()
        page.add(
            ft.Text("¡CAZAMOS EL ERROR DE ARRANQUE!", color=ft.Colors.WHITE, bgcolor=ft.Colors.RED, size=24, weight="bold"),
            ft.Text("Sacale captura a este texto:", color=ft.Colors.BLACK, weight="bold"),
            ft.Text(error_pila, color=ft.Colors.RED, selectable=True)
        )
        page.update()

# ==========================================
# ARRANQUE NATIVO PARA ANDROID/GITHUB
# ==========================================
if __name__ == "__main__":
    ft.app(target=main)
