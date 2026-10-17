import os
from datetime import datetime
import sqlite3
import flet as ft

def conectar_banco():
    # Caminho seguro para o Android não bloquear o banco de dados
    diretorio_dados = os.path.dirname(__file__)
    caminho_banco = os.path.join(diretorio_dados, "dados_plantoes.db")
    
    conexao = sqlite3.connect(caminho_banco, check_same_thread=False)
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS escalas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tecnico TEXT, data TEXT, local TEXT, turno TEXT
        )
    """)
    conexao.commit()
    return conexao

def main(page: ft.Page):
    page.title = "Gestão de Plantões"
    page.window_width = 450
    page.window_height = 700
    page.window_min_width = 380
    page.window_min_height = 600
    page.bgcolor = ft.colors.WHITE
    page.padding = 15
    page.scroll = ft.ScrollMode.ADAPTIVE

    conexao = conectar_banco()
    
    # Armazena o ID como uma propriedade da página para evitar problemas de escopo
    page.data = {"id_edicao_atual": None}

    txt_tecnico = ft.TextField(
        label="Nome do Técnico(a):",
        placeholder_text="Digite seu nome",
        border_color="#bd274a",
        label_style=ft.TextStyle(color="#1a1a1a", weight=ft.FontWeight.BOLD, size=12),
        text_style=ft.TextStyle(color="#1a1a1a")
    )

    def mascara_data(e):
        texto = txt_data.value.replace("/", "")
        novo = ""
        for i, c in enumerate(texto[:8]):
            if i == 2 or i == 4:
                novo += "/"
            novo += c
        txt_data.value = novo
        page.update()

    txt_data = ft.TextField(
        label="Data (DD/MM/AAAA):",
        placeholder_text="Digite a data do plantão",
        border_color="#bd274a",
        on_change=mascara_data,
        label_style=ft.TextStyle(color="#1a1a1a", weight=ft.FontWeight.BOLD, size=12),
        text_style=ft.TextStyle(color="#1a1a1a")
    )

    txt_local = ft.TextField(
        label="Local do Plantão:",
        placeholder_text="Digite o local ou nome do paciente",
        border_color="#bd274a",
        label_style=ft.TextStyle(color="#1a1a1a", weight=ft.FontWeight.BOLD, size=12),
        text_style=ft.TextStyle(color="#1a1a1a")
    )

    combo_turno = ft.Dropdown(
        label="Turno / Escala:",
        border_color="#bd274a",
        label_style=ft.TextStyle(color="#1a1a1a", weight=ft.FontWeight.BOLD, size=12),
        text_style=ft.TextStyle(color="#1a1a1a"),
        options=[
            ft.dropdown.Option("12x36 Diurno (07h às 19h)"),
            ft.dropdown.Option("12x36 Noturno (19h às 07h)"),
            ft.dropdown.Option("Manhã (07h às 13h)"),
            ft.dropdown.Option("Tarde (13h às 19h)"),
            ft.dropdown.Option("Outros Horários"),
        ],
        value="12x36 Diurno (07h às 19h)"
    )

    container_scroll = ft.ListView(
        expand=True,
        spacing=8,
        padding=5,
    )

    def carregar_dados():
        container_scroll.controls.clear()
        cursor = conexao.cursor()
        cursor.execute("SELECT id, tecnico, data, local, turno FROM escalas ORDER BY id DESC")
        
        hoje = datetime.now().date()
        
        for id_db, t, d, l, tu in cursor.fetchall():
            cor_texto = "#1b5e20"
            prefixo = "[AGENDADO]"
            
            try:
                data_plantao = datetime.strptime(d, "%d/%m/%Y").date()
                if data_plantao == hoje:
                    cor_texto = "#fc8b0a"
                    prefixo = "[HOJE]"
                elif data_plantao < hoje:
                    cor_texto = "#b71c1c"
                    prefixo = "[CONCLUÍDO]"
            except ValueError:
                cor_texto = "#b71c1c"
                prefixo = "[DATA ERRA]"

            texto_exibicao = f"{prefixo} 👤 {t}\n📅 {d} | 📍 {l}\n⏱️ {tu}"
            
            def criar_card(id_p, te, da, lo, tur, txt, cor):
                return ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Expanded(
                                child=ft.Text(
                                    value=txt,
                                    color=cor,
                                    weight=ft.FontWeight.BOLD,
                                    size=12
                                )
                            ),
                            ft.Column(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.icons.EDIT,
                                        icon_color="#1a1a1a",
                                        icon_size=18,
                                        tooltip="Editar",
                                        on_click=lambda _: preparar_edicao(id_p, te, da, lo, tur)
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE,
                                        icon_color="#c62828",
                                        icon_size=18,
                                        tooltip="Apagar",
                                        on_click=lambda _: apagar_plantao(id_p)
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=2
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    bgcolor=ft.colors.WHITE,
                    padding=10,
                    border_radius=6,
                    border=ft.border.all(1, "#d0d0d0")
                )

            container_scroll.controls.append(criar_card(id_db, t, d, l, tu, texto_exibicao, cor_texto))
        
        page.update()

    def lancar_plantao(e):
        t = txt_tecnico.value.strip()
        d = txt_data.value.strip()
        l = txt_local.value.strip()
        tu = combo_turno.value
        
        if not t or not d or not l:
            return 

        cursor = conexao.cursor()
        if page.data["id_edicao_atual"] is None:
            cursor.execute("INSERT INTO escalas (tecnico, data, local, turno) VALUES (?, ?, ?, ?)", (t, d, l, tu))
        else:
            cursor.execute("UPDATE escalas SET tecnico=?, data=?, local=?, turno=? WHERE id=?", (t, d, l, tu, page.data["id_edicao_atual"]))
            page.data["id_edicao_atual"] = None
            btn_salvar.text = "CONFIRMAR PLANTÃO"
            btn_salvar.bgcolor = "#2e7d32"

        conexao.commit()
        
        txt_tecnico.value = ""
        txt_data.value = ""
        txt_local.value = ""
        combo_turno.value = "12x36 Diurno (07h às 19h)"
        
        carregar_dados()

    def preparar_edicao(id_plantao, tecnico, data, local, turno):
        page.data["id_edicao_atual"] = id_plantao
        txt_tecnico.value = tecnico
        txt_data.value = data
        txt_local.value = local
        combo_turno.value = turno
        btn_salvar.text = "SALVAR ALTERAÇÕES"
        btn_salvar.bgcolor = "#ef6c00"
        page.update()

    def apagar_plantao(id_plantao):
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM escalas WHERE id=?", (id_plantao,))
        conexao.commit()
        carregar_dados()

    btn_salvar = ft.ElevatedButton(
        text="CONFIRMAR PLANTÃO",
        bgcolor="#2e7d32",
        color=ft.colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        height=45,
        on_click=lancar_plantao
    )

    page.add(
        ft.Column(
            controls=[
                ft.Text("Gestão de Plantões", size=20, weight=ft.FontWeight.BOLD, color="#bd274a"),
                txt_tecnico,
                txt_data,
                txt_local,
                combo_turno,
                ft.Container(content=btn_salvar, alignment=ft.alignment.center, margin=ft.margin.only(top=10, bottom=10)),
                ft.Text("Plantões Lançados:", size=14, weight=ft.FontWeight.BOLD, color="#1a1a1a"),
                ft.Expanded(child=container_scroll)
            ],
            expand=True,
            spacing=10
        )
    )

    carregar_dados()

ft.app(target=main)
