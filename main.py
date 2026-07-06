import flet as ft
import traceback
import os
import sqlite3
from fpdf import FPDF
from datetime import date

# ==========================================
# 1. HERRAMIENTAS DE BASE DE DATOS Y RUTAS
# ==========================================
def get_ruta_db():
    # Calcula la ruta segura del celular
    return os.path.join(os.environ.get("FLET_APP_STORAGE_DATA", "."), "sistema_ventas.db")

def db(query, parametros=(), fetch=False, fetchall=False):
    conexion = sqlite3.connect(get_ruta_db())
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
# 2. INTERFAZ GRÁFICA PROFESIONAL (FLET)
# ==========================================
def main(page: ft.Page):
    try:
        page.title = "XIOMI Distribuidora"
        page.theme_mode = "light"
        
        # Arrancamos la base de datos de forma segura
        inicializar_base_datos()
        
        carrito = {}
        estado_carrito = {"editando": False, "id_factura": None, "cargado": False}

        def cambiar_pantalla(e):
            try:
                page.views.clear()
                
                # PANTALLA 1: MENU PRINCIPAL CORPORATIVO
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

                # PANTALLA 2: PANEL DE CONTROL DE PEDIDOS
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
                                        def editar(ev):
                                            estado_carrito["editando"] = True; estado_carrito["id_factura"] = num_e; estado_carrito["cargado"] = False; carrito.clear(); page.go("/carrito")
                                        return editar
                                        
                                    tabla_pedidos.rows.append(ft.DataRow(cells=[
                                        ft.DataCell(ft.Text(str(id_f))), ft.DataCell(ft.Text(cli)), ft.DataCell(ft.Text(f"${formato_ars(tot)}")),
                                        ft.DataCell(ft.Row([ft.IconButton("edit", icon_color="blue", on_click=crear_editar_p(id_f)), ft.IconButton("delete", icon_color="red", on_click=crear_borrar_p(id_f))]))
                                    ]))
                            tabla_pedidos.update()
                        except: pass

                    def ir_nuevo_pedido(e):
                        estado_carrito["editando"] = False; estado_carrito["id_factura"] = None; estado_carrito["cargado"] = False; carrito.clear(); page.go("/carrito")
                    
                    page.views.append(ft.View("/pedidos_dia", [
                        ft.AppBar(title=ft.Text("Panel de Ventas"), bgcolor="#263238", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))), 
                        ft.ElevatedButton("+ ARMAR NUEVO PEDIDO", icon="add_shopping_cart", on_click=ir_nuevo_pedido, style=ft.ButtonStyle(bgcolor="#1565C0", color="white", padding=20), width=float("inf")),
                        ft.Divider(), ft.Text(f"Tickets de hoy ({hoy}):", weight="bold"), 
                        ft.Column([tabla_pedidos], scroll="auto", expand=True)
                    ], padding=20))
                    ref_pedidos()

                # PANTALLA 3: EL CARRITO
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

                # PANTALLA 4: ABM DE PRODUCTOS
                elif page.route == "/agregar_producto":
                    inp_cod = ft.TextField(label="Código (ART-01)", width=float("inf")); inp_nom = ft.TextField(label="Descripción", width=float("inf")); inp_pre = ft.TextField(label="Precio ($)", keyboard_type="number", width=float("inf"))
                    tabla_prod = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["Cod.", "Desc", "Prec", "X"]], rows=[])
                    
                    def ref_prod():
                        try:
                            tabla_prod.rows.clear()
                            filas = db("SELECT codigo_articulo, nombre_articulo, precio_unitario FROM Productos", fetch=True, fetchall=True)
                            if filas:
                                for c, n, p in filas:
                                    def crear_borrar_p(cod_p=c):
                                        return lambda _: (db("DELETE FROM Productos WHERE codigo_articulo=?", (cod_p,)), ref_prod())
                                    tabla_prod.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(c))), ft.DataCell(ft.Text(str(n))), ft.DataCell(ft.Text(f"${formato_ars(p)}")), ft.DataCell(ft.IconButton("delete", icon_color="red", on_click=crear_borrar_p(c)))]))
                            tabla_prod.update()
                        except: pass

                    def guardar_p(e):
                        if inp_cod.value and inp_nom.value and inp_pre.value:
                            db("INSERT INTO Productos VALUES (?, ?, ?)", (inp_cod.value.strip().upper(), inp_nom.value.strip().upper(), float(inp_pre.value.replace(',','.'))))
                            inp_cod.value = ""; inp_nom.value = ""; inp_pre.value = ""; ref_prod()

                    page.views.append(ft.View("/agregar_producto", [ft.AppBar(title=ft.Text("Catálogo"), bgcolor="#00695C", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))), inp_cod, inp_nom, inp_pre, ft.ElevatedButton("GUARDAR", icon="save", on_click=guardar_p, style=ft.ButtonStyle(bgcolor="#00695C", color="white", padding=20), width=float("inf")), ft.Divider(), ft.Column([tabla_prod], scroll="auto", expand=True)], padding=20)); ref_prod()

                # PANTALLA 5: ABM DE CLIENTES
                elif page.route == "/agregar_cliente":
                    inp_nom_c = ft.TextField(label="Nombre", width=float("inf")); inp_dir_c = ft.TextField(label="Dirección", width=float("inf"))
                    tabla_cli = ft.DataTable(columns=[ft.DataColumn(ft.Text(c, weight="bold")) for c in ["ID", "Nombre", "Dirección", "X"]], rows=[])
                    
                    def ref_cli():
                        try:
                            tabla_cli.rows.clear()
                            filas = db("SELECT numero_cliente, nombre_apellido, direccion_entrega FROM Clientes", fetch=True, fetchall=True)
                            if filas:
                                for id_c, n, d in filas:
                                    def crear_borrar_c(num_c=id_c):
                                        return lambda _: (db("DELETE FROM Clientes WHERE numero_cliente=?", (num_c,)), ref_cli())
                                    tabla_cli.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(id_c))), ft.DataCell(ft.Text(str(n))), ft.DataCell(ft.Text(str(d if d else ""))), ft.DataCell(ft.IconButton("delete", icon_color="red", on_click=crear_borrar_c(id_c)))]))
                            tabla_cli.update()
                        except: pass

                    def guardar_c(e):
                        if inp_nom_c.value:
                            db("INSERT INTO Clientes (nombre_apellido, direccion_entrega) VALUES (?, ?)", (inp_nom_c.value.upper(), inp_dir_c.value))
                            inp_nom_c.value = ""; inp_dir_c.value = ""; ref_cli()

                    page.views.append(ft.View("/agregar_cliente", [ft.AppBar(title=ft.Text("Directorio"), bgcolor="#303F9F", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))), inp_nom_c, inp_dir_c, ft.ElevatedButton("GUARDAR", icon="save", on_click=guardar_c, style=ft.ButtonStyle(bgcolor="#303F9F", color="white", padding=20), width=float("inf")), ft.Divider(), ft.Column([tabla_cli], scroll="auto", expand=True)], padding=20)); ref_cli()

                # PANTALLA 6: REPORTES
                elif page.route == "/reportes":
                    page.views.append(ft.View("/reportes", [
                        ft.AppBar(title=ft.Text("Reportes"), bgcolor="#FF8F00", color="white", leading=ft.IconButton("arrow_back", icon_color="white", on_click=lambda _: page.go("/"))),
                        ft.Text("Los reportes en PDF estarán disponibles próximamente en la versión móvil nativa.", weight="bold", color="red")
                    ], padding=20, scroll="auto"))

                page.update()
                
            except Exception as ex:
                error_pila = traceback.format_exc()
                page.clean()  
                page.add(
                    ft.Text("¡ERROR AL DIBUJAR PANTALLA!", color="white", bgcolor="red", size=24, weight="bold"),
                    ft.Text(error_pila, color="red", selectable=True)
                )
                page.update()

        page.on_route_change = cambiar_pantalla
        page.go("/")

    except Exception as e:
        error_pila = traceback.format_exc()
        page.clean() 
        page.add(
            ft.Text("¡CAZAMOS UN ERROR DE ARRANQUE!", color="white", bgcolor="red", size=24, weight="bold"),
            ft.Text(error_pila, color="red", selectable=True)
        )
        page.update()

# ======================================================================
# ATENCIÓN: ESTA ÚLTIMA LÍNEA DEFINE SI ABRÍS EN COMPU O EN EL CELULAR
# ======================================================================
if __name__ == "__main__":
    # ---> SI LO VAS A SUBIR A GITHUB PARA EL CELULAR, USA ESTA LÍNEA:
    ft.app(target=main)
    
    # ---> SI LO QUERÉS PROBAR EN LA COMPU (JUANA MANSO), BORRÁ LA LÍNEA DE ARRIBA Y USA ESTA:
    # ft.app(target=main, view=ft.AppView.WEB_BROWSER)
