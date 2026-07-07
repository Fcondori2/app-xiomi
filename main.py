import flet as ft
import os
import sqlite3
import traceback
from datetime import date

# Aseguramos que exista la carpeta de descargas temporales en el servidor
if not os.path.exists("assets"):
    os.makedirs("assets")

# ==========================================
# 1. HERRAMIENTAS DE BASE DE DATOS
# ==========================================
def db(query, parametros=(), fetch=False, fetchall=False):
    conexion = sqlite3.connect("sistema_ventas.db")
    cursor = conexion.cursor()
    cursor.execute(query, parametros)
    if fetch:
        res = cursor.fetchall() if fetchall else cursor.fetchone()
        conexion.close()
        return res
    conexion.commit()
    conexion.close()

def inicializar_base_datos():
    db('''CREATE TABLE IF NOT EXISTS Clientes (numero_cliente INTEGER PRIMARY KEY AUTOINCREMENT, nombre_apellido TEXT NOT NULL, direccion_entrega TEXT)''')
    db('''CREATE TABLE IF NOT EXISTS Productos (codigo_articulo TEXT PRIMARY KEY, nombre_articulo TEXT NOT NULL, precio_unitario REAL NOT NULL)''')
    db('''CREATE TABLE IF NOT EXISTS Facturas (numero_factura INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, numero_cliente INTEGER, total_a_pagar REAL NOT NULL, FOREIGN KEY(numero_cliente) REFERENCES Clientes(numero_cliente))''')
    db('''CREATE TABLE IF NOT EXISTS Detalle_Factura (id INTEGER PRIMARY KEY AUTOINCREMENT, numero_factura INTEGER, codigo_articulo TEXT, precio_unitario REAL, unidades INTEGER, total_linea REAL)''')
    if db("SELECT COUNT(*) FROM Clientes", fetch=True)[0] == 0:
        db("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES ('CONSUMIDOR FINAL', 'PERICO')")

def formato_ars(numero): 
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==========================================
# 2. MOTOR DE PDF (DESCARGA DIRECTA WEB)
# ==========================================
def generar_pdf_facturas(ruta_destino, num_factura=None, fecha_consulta=None):
    from fpdf import FPDF 
    if num_factura:
        facturas = db("SELECT numero_factura FROM Facturas WHERE numero_factura = ?", (num_factura,), fetch=True, fetchall=True)
    elif fecha_consulta:
        facturas = db("SELECT numero_factura FROM Facturas WHERE fecha = ?", (fecha_consulta,), fetch=True, fetchall=True)
    else: return False
    
    if not facturas: return False
    pdf = FPDF()
    for (f_id,) in facturas:
        factura = db('''SELECT f.numero_factura, f.fecha, c.nombre_apellido, c.direccion_entrega, f.total_a_pagar FROM Facturas f JOIN Clientes c ON f.numero_cliente = c.numero_cliente WHERE f.numero_factura = ?''', (f_id,), fetch=True)
        lineas = db('''SELECT p.nombre_articulo, d.unidades, d.precio_unitario, d.total_linea FROM Detalle_Factura d JOIN Productos p ON d.codigo_articulo = p.codigo_articulo WHERE d.numero_factura = ?''', (f_id,), fetch=True, fetchall=True)
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
    from fpdf import FPDF
    productos = db(query, parametros, fetch=True, fetchall=True)
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
# 3. INTERFAZ GRÁFICA WEB
# ==========================================
def main(page: ft.Page):
    try:
        page.title = "XIOMI Distribuidora"
        page.theme_mode = "light"
        inicializar_base_datos()
        
        carrito = {}
        estado_carrito = {"editando": False, "id_factura": None, "cargado": False}

        def cambiar_pantalla(e):
            try:
                page.views.clear()
                
                if page.route == "/":
                    page.views.append(ft.View("/", [
                        ft.AppBar(title=ft.Text("XIOMI Distribuidora", weight="bold"), bgcolor="#263238", color="white", center_title=True),
                        ft.Container(height=15),
                        ft.Text("Menú Principal", size=24, weight="bold", color="#263238"),
                        ft.ElevatedButton("Gestión de Ventas del Día", icon="point_of_sale", on_click=lambda _: page.go("/pedidos_dia"), style=ft.ButtonStyle(bgcolor="#1565C0", color="white", padding=20), width=float("inf")),
                        ft.ElevatedButton("Gestión de Clientes", icon="people", on_click=lambda _: page.go("/agregar_cliente"), style=ft.ButtonStyle(bgcolor="#3F51B5", color="white", padding=20), width=float("inf")),
                        ft.ElevatedButton("Gestión de Productos", icon="inventory", on_click=lambda _: page.go("/agregar_producto"), style=ft.ButtonStyle(bgcolor="#3F51B5", color="white", padding=20), width=float("inf")),
                        ft.ElevatedButton("Reportes y Facturación", icon="bar_chart", on_click=lambda _: page.go("/reportes"), style=ft.ButtonStyle(bgcolor="#FF8F00", color="white", padding=20), width=float("inf")),
                    ], padding=20))

                elif page.route == "/pedidos_dia":
                    hoy = date.today().strftime("%Y-%m-%d")
                    tabla_pedidos = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["Nro", "Cliente", "Total", "X"]], rows=[])
                    def ref_pedidos():
                        try:
                            tabla_pedidos.rows.clear()
                            filas = db("SELECT f.numero_factura, c.nombre_apellido, f.total_a_pagar FROM Facturas f JOIN Clientes c ON f.numero_cliente = c.numero_cliente WHERE f.fecha = ?", (hoy,), fetch=True, fetchall=True)
                            if filas:
                                for id_f, cli, tot in filas:
                                    def crear_borrar_p(num_b=id_f):
                                        return lambda _: (db("DELETE FROM Detalle_Factura WHERE numero_factura=?", (num_b,)), db("DELETE FROM Facturas WHERE numero_factura=?", (num_b,)), ref_pedidos())
                                    def crear_editar_p(num_e=id_f):
                                        return lambda _: (estado_carrito.update({"editando": True, "id_factura": num_e, "cargado": False}), carrito.clear(), page.go("/carrito"))
                                    tabla_pedidos.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(id_f))), ft.DataCell(ft.Text(cli)), ft.DataCell(ft.Text(f"${formato_ars(tot)}")), ft.DataCell(ft.Row([ft.IconButton("edit", icon_color="blue", on_click=crear_editar_p(id_f)), ft.IconButton("delete", icon_color="red", on_click=crear_borrar_p(id_f))]))]))
                            tabla_pedidos.update()
                        except: pass
                    page.views.append(ft.View("/pedidos_dia", [ft.AppBar(title=ft.Text("Panel de Ventas"), bgcolor="#263238", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))), ft.ElevatedButton("+ ARMAR NUEVO PEDIDO", icon="add_shopping_cart", on_click=lambda _: (estado_carrito.update({"editando": False, "id_factura": None, "cargado": False}), carrito.clear(), page.go("/carrito")), style=ft.ButtonStyle(bgcolor="#1565C0", color="white", padding=20), width=float("inf")), ft.Divider(), ft.Text(f"Tickets de hoy ({hoy}):", weight="bold"), ft.Column([tabla_pedidos], scroll="auto", expand=True)], padding=20)); ref_pedidos()

                elif page.route == "/carrito":
                    texto_total = ft.Text("TOTAL: $ 0.00", size=22, weight="bold", color="white")
                    lista_carrito_ui = ft.Column(scroll="auto", expand=True)
                    opciones_cli = [ft.dropdown.Option(text=nom[0]) for nom in db("SELECT nombre_apellido FROM Clientes", fetch=True, fetchall=True)]
                    cat = {cod: {"nombre": nom, "precio": pre} for cod, nom, pre in db("SELECT codigo_articulo, nombre_articulo, precio_unitario FROM Productos", fetch=True, fetchall=True)}
                    opciones_prod = [ft.dropdown.Option(key=cod, text=f"{v['nombre']} | ${formato_ars(v['precio'])}") for cod, v in cat.items()]
                    dd_clientes = ft.Dropdown(label="1. Seleccionar Cliente", options=opciones_cli, expand=True)
                    dd_productos = ft.Dropdown(label="Seleccionar Artículo", options=opciones_prod, expand=3)
                    inp_cant = ft.TextField(label="Cant.", keyboard_type="number", expand=1)

                    campo_nom_cli = ft.TextField(label="Nombre", width=300); campo_dir_cli = ft.TextField(label="Dirección", width=300)
                    def guardar_cliente_rapido(e):
                        if not campo_nom_cli.value: return
                        nom_nuevo = campo_nom_cli.value.upper()
                        db("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES (?, ?)", (nom_nuevo, campo_dir_cli.value.upper()))
                        dd_clientes.options.append(ft.dropdown.Option(text=nom_nuevo)); dd_clientes.value = nom_nuevo; dd_clientes.update()
                        campo_nom_cli.value = ""; campo_dir_cli.value = ""; page.dialog.open = False; page.update()
                    page.dialog = ft.AlertDialog(title=ft.Text("Agregar Cliente"), content=ft.Column([campo_nom_cli, campo_dir_cli], tight=True), actions=[ft.TextButton("Guardar", on_click=guardar_cliente_rapido)])

                    if estado_carrito["editando"]:
                        id_fac = estado_carrito["id_factura"]
                        cliente_actual = db("SELECT c.nombre_apellido FROM Facturas f JOIN Clientes c ON f.numero_cliente = c.numero_cliente WHERE f.numero_factura = ?", (id_fac,), fetch=True)
                        if cliente_actual: dd_clientes.value = cliente_actual[0]
                        if not estado_carrito["cargado"]:
                            detalles = db("SELECT d.codigo_articulo, p.nombre_articulo, d.precio_unitario, d.unidades FROM Detalle_Factura d JOIN Productos p ON d.codigo_articulo = p.codigo_articulo WHERE d.numero_factura = ?", (id_fac,), fetch=True, fetchall=True)
                            carrito.clear()
                            for cod, nom, pre, uni in detalles: carrito[cod] = {"nombre": nom, "precio": pre, "cantidad": uni}
                            estado_carrito["cargado"] = True

                    def act_carrito():
                        lista_carrito_ui.controls.clear()
                        suma = sum(item["cantidad"] * item["precio"] for item in carrito.values())
                        for cod, item in carrito.items():
                            def crear_borrar_item(c_item=cod):
                                return lambda _: (carrito.pop(c_item), act_carrito())
                            lista_carrito_ui.controls.append(ft.ListTile(leading=ft.Icon("check_circle", color="green"), title=ft.Text(f"{item['cantidad']}x {item['nombre']}", weight="bold"), subtitle=ft.Text(f"Subtotal: ${formato_ars(item['cantidad'] * item['precio'])}"), trailing=ft.IconButton("delete", icon_color="red", on_click=crear_borrar_item(cod))))
                        texto_total.value = f"TOTAL: $ {formato_ars(suma)}"; page.update()

                    def agregar(e):
                        if not dd_productos.value or not inp_cant.value.isdigit() or int(inp_cant.value) <= 0: return
                        cod, cant = dd_productos.value, int(inp_cant.value)
                        carrito[cod] = {"nombre": cat[cod]["nombre"], "precio": cat[cod]["precio"], "cantidad": carrito.get(cod, {}).get("cantidad", 0) + cant}
                        dd_productos.value = None; inp_cant.value = ""; act_carrito()

                    def confirmar(e):
                        if not dd_clientes.value or not carrito: return
                        num_cli = db("SELECT numero_cliente FROM Clientes WHERE nombre_apellido = ?", (dd_clientes.value,), fetch=True)[0]
                        tot = sum(item["cantidad"] * item["precio"] for item in carrito.values())
                        if estado_carrito["editando"]:
                            id_fac = estado_carrito["id_factura"]
                            db("UPDATE Facturas SET numero_cliente = ?, total_a_pagar = ? WHERE numero_factura = ?", (num_cli, tot, id_fac))
                            db("DELETE FROM Detalle_Factura WHERE numero_factura = ?", (id_fac,))
                            for cod, item in carrito.items(): db("INSERT INTO Detalle_Factura (numero_factura, codigo_articulo, precio_unitario, unidades, total_linea) VALUES (?, ?, ?, ?, ?)", (id_fac, cod, item["precio"], item["cantidad"], item["cantidad"] * item["precio"]))
                        else:
                            db("INSERT INTO Facturas (fecha, numero_cliente, total_a_pagar) VALUES (?, ?, ?)", (date.today().strftime("%Y-%m-%d"), num_cli, tot))
                            nuevo_num = db("SELECT MAX(numero_factura) FROM Facturas", fetch=True)[0]
                            for cod, item in carrito.items(): db("INSERT INTO Detalle_Factura (numero_factura, codigo_articulo, precio_unitario, unidades, total_linea) VALUES (?, ?, ?, ?, ?)", (nuevo_num, cod, item["precio"], item["cantidad"], item["cantidad"] * item["precio"]))
                        carrito.clear(); estado_carrito["editando"] = False; page.go("/pedidos_dia")

                    tit_pantalla = f"CORRIGIENDO TICKET NRO {estado_carrito['id_factura']}" if estado_carrito["editando"] else "Armar Pedido"
                    color_fondo = "#1565C0" if estado_carrito["editando"] else "#263238"
                    bloque = ft.Card(content=ft.Container(padding=15, content=ft.Column([ft.Row([dd_clientes, ft.IconButton(icon="person_add", icon_color="blue", on_click=lambda _: setattr(page.dialog, 'open', True) or page.update())]), ft.Text("2. Agregar artículos", weight="bold"), ft.Row([dd_productos, inp_cant]), ft.ElevatedButton("AGREGAR", icon="add", on_click=agregar, width=float("inf"))])))
                    pie = ft.Container(bgcolor=color_fondo, padding=20, border_radius=10, content=ft.Column([ft.Row([texto_total], alignment="center"), ft.ElevatedButton("GUARDAR VENTA", icon="save", on_click=confirmar, bgcolor="green", color="white", width=float("inf"), height=50)]))
                    page.views.append(ft.View("/carrito", [ft.AppBar(title=ft.Text(tit_pantalla), bgcolor=color_fondo, color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/pedidos_dia"))), bloque, lista_carrito_ui, pie], padding=20)); act_carrito()

                elif page.route == "/agregar_producto":
                    inp_cod = ft.TextField(label="Código (ART-01)", width=float("inf")); inp_nom = ft.TextField(label="Descripción", width=float("inf")); inp_pre = ft.TextField(label="Precio ($)", keyboard_type="number", width=float("inf"))
                    tabla_prod = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["Cod.", "Desc", "Prec", "X"]], rows=[])
                    def ref_prod():
                        try:
                            tabla_prod.rows.clear()
                            filas = db("SELECT codigo_articulo, nombre_articulo, precio_unitario FROM Productos", fetch=True, fetchall=True)
                            if filas:
                                for c, n, p in filas:
                                    def crear_borrar_p(cod_p=c): return lambda _: (db("DELETE FROM Productos WHERE codigo_articulo=?", (cod_p,)), ref_prod())
                                    tabla_prod.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(c))), ft.DataCell(ft.Text(str(n))), ft.DataCell(ft.Text(f"${formato_ars(p)}")), ft.DataCell(ft.IconButton("delete", icon_color="red", on_click=crear_borrar_p(c)))]))
                            tabla_prod.update()
                        except: pass
                    def guardar_p(e):
                        if inp_cod.value and inp_nom.value and inp_pre.value:
                            db("INSERT INTO Productos VALUES (?, ?, ?)", (inp_cod.value.strip().upper(), inp_nom.value.strip().upper(), float(inp_pre.value.replace(',','.'))))
                            inp_cod.value = ""; inp_nom.value = ""; inp_pre.value = ""; ref_prod()
                    page.views.append(ft.View("/agregar_producto", [ft.AppBar(title=ft.Text("Catálogo"), bgcolor="#00695C", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))), inp_cod, inp_nom, inp_pre, ft.ElevatedButton("GUARDAR", icon="save", on_click=guardar_p, style=ft.ButtonStyle(bgcolor="#00695C", color="white", padding=20), width=float("inf")), ft.Divider(), ft.Column([tabla_prod], scroll="auto", expand=True)], padding=20)); ref_prod()

                elif page.route == "/agregar_cliente":
                    inp_nom_c = ft.TextField(label="Nombre", width=float("inf")); inp_dir_c = ft.TextField(label="Dirección", width=float("inf"))
                    tabla_cli = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["ID", "Nombre", "Dirección", "X"]], rows=[])
                    def ref_cli():
                        try:
                            tabla_cli.rows.clear()
                            filas = db("SELECT numero_cliente, nombre_apellido, direccion_entrega FROM Clientes", fetch=True, fetchall=True)
                            if filas:
                                for id_c, n, d in filas:
                                    def crear_borrar_c(num_c=id_c): return lambda _: (db("DELETE FROM Clientes WHERE numero_cliente=?", (num_c,)), ref_cli())
                                    tabla_cli.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(id_c))), ft.DataCell(ft.Text(str(n))), ft.DataCell(ft.Text(str(d if d else ""))), ft.DataCell(ft.IconButton("delete", icon_color="red", on_click=crear_borrar_c(id_c)))]))
                            tabla_cli.update()
                        except: pass
                    def guardar_c(e):
                        if inp_nom_c.value:
                            db("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES (?, ?)", (inp_nom_c.value.upper(), inp_dir_c.value))
                            inp_nom_c.value = ""; inp_dir_c.value = ""; ref_cli()
                    page.views.append(ft.View("/agregar_cliente", [ft.AppBar(title=ft.Text("Directorio"), bgcolor="#303F9F", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))), inp_nom_c, inp_dir_c, ft.ElevatedButton("GUARDAR", icon="save", on_click=guardar_c, style=ft.ButtonStyle(bgcolor="#303F9F", color="white", padding=20), width=float("inf")), ft.Divider(), ft.Column([tabla_cli], scroll="auto", expand=True)], padding=20)); ref_cli()

                # PANTALLA 6: REPORTES - TOTALMENTE COMPATIBLE CON LA WEB
                elif page.route == "/reportes":
                    hoy = date.today().strftime("%Y-%m-%d")
                    inp_num = ft.TextField(label="Nro Factura", keyboard_type="number")
                    inp_fec = ft.TextField(label="Fecha (YYYY-MM-DD)", value=hoy)
                    inp_inicio = ft.TextField(label="Desde (YYYY-MM-DD)", value=hoy, expand=True)
                    inp_fin = ft.TextField(label="Hasta (YYYY-MM-DD)", value=hoy, expand=True)

                    def pedir_pdf(tipo, id_f=None, f=None, finio=None, ffin=None):
                        import time
                        # Se guarda directo en la carpeta "assets" del servidor
                        nombre_archivo = f"Reporte_{tipo}_{int(time.time())}.pdf"
                        ruta_completa = os.path.join("assets", nombre_archivo)
                        
                        exito = False
                        if tipo == "factura":
                            exito = generar_pdf_facturas(ruta_completa, num_factura=id_f, fecha_consulta=f)
                        elif tipo == "reporte_dia":
                            exito = generar_reporte_generico(ruta_completa, "SELECT d.codigo_articulo, p.nombre_articulo, p.precio_unitario, SUM(d.unidades), SUM(d.total_linea) FROM Detalle_Factura d JOIN Productos p ON d.codigo_articulo = p.codigo_articulo JOIN Facturas f ON d.numero_factura = f.numero_factura WHERE f.fecha = ? GROUP BY d.codigo_articulo", (f,), "REPORTE DIARIO DE VENTAS", f"Fecha: {f}")
                        elif tipo == "consolidado":
                            exito = generar_reporte_generico(ruta_completa, "SELECT d.codigo_articulo, p.nombre_articulo, p.precio_unitario, SUM(d.unidades), SUM(d.total_linea) FROM Detalle_Factura d JOIN Productos p ON d.codigo_articulo = p.codigo_articulo JOIN Facturas f ON d.numero_factura = f.numero_factura WHERE f.fecha BETWEEN ? AND ? GROUP BY d.codigo_articulo", (finio, ffin), "REPORTE CONSOLIDADO", f"Periodo: {finio} al {ffin}")
                        
                        if exito:
                            # LA MAGIA WEB: El navegador del celular descarga el PDF al instante
                            page.launch_url(f"/{nombre_archivo}")
                            page.snack_bar = ft.SnackBar(ft.Text("✅ ¡PDF Descargado! Buscalo en las descargas de tu celu.", color="white"), bgcolor="green")
                        else:
                            page.snack_bar = ft.SnackBar(ft.Text("❌ No se encontraron datos para generar el PDF.", color="white"), bgcolor="red")
                        page.snack_bar.open = True; page.update()

                    page.views.append(ft.View("/reportes", [
                        ft.AppBar(title=ft.Text("Reportes y Balances"), bgcolor="#FF8F00", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))),
                        ft.Card(content=ft.Container(padding=20, content=ft.Column([
                            ft.Text("Facturas Físicas", weight="bold"), inp_num, 
                            ft.ElevatedButton("Reimprimir por Número", on_click=lambda _: pedir_pdf("factura", id_f=int(inp_num.value) if inp_num.value else 0)), ft.Divider(), inp_fec, 
                            ft.ElevatedButton("Lote Diario Completo", on_click=lambda _: pedir_pdf("factura", f=inp_fec.value))]))),
                        ft.Card(content=ft.Container(padding=20, content=ft.Column([
                            ft.Text("Balances de Mercadería y Caja", weight="bold"), 
                            ft.ElevatedButton("Reporte Diario", icon="today", on_click=lambda _: pedir_pdf("reporte_dia", f=inp_fec.value)), ft.Divider(),
                            ft.Text("Consolidado por Fechas", weight="bold"), ft.Row([inp_inicio, inp_fin]),
                            ft.ElevatedButton("Generar Balance", icon="date_range", bgcolor="#00695C", color="white", on_click=lambda _: pedir_pdf("consolidado", finio=inp_inicio.value.strip(), ffin=inp_fin.value.strip()))])))
                    ], padding=20, scroll="auto"))

                page.update()
                
            except Exception as ex:
                error_pila = traceback.format_exc()
                page.clean()  
                page.add(ft.Text("¡ERROR GRÁFICO!", color="white", bgcolor="red", size=24, weight="bold"), ft.Text(error_pila, color="red"))
                page.update()

        page.on_route_change = cambiar_pantalla
        page.go("/")

    except Exception as e:
        error_pila = traceback.format_exc()
        page.clean() 
        page.add(ft.Text("¡ERROR DE ARRANQUE!", color="white", bgcolor="red", size=24, weight="bold"), ft.Text(error_pila, color="red"))
        page.update()

# ==========================================
# CONFIGURACIÓN DINÁMICA DE PUERTOS PARA LA NUBE
# ==========================================
if __name__ == "__main__":
    puerto_servidor = int(os.environ.get("PORT", 8080))
    ft.app(target=main, host="0.0.0.0", port=puerto_servidor, assets_dir="assets")
