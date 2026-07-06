import flet as ft

def main(page: ft.Page):
    page.title = "Prueba de Diagnóstico"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    page.add(
        ft.Text("¡EL APK NUEVO FUNCIONA!", size=30, color=ft.Colors.GREEN_700, weight="bold"),
        ft.Text("Si ves esto, GitHub y tu celular están perfectos.", size=16, color=ft.Colors.BLACK)
    )
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
