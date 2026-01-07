import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys

# Adiciona o diretório do frontend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from zig_bridge import ZigBackend
except ImportError:
    ZigBackend = None
    print("Aviso: zig_bridge não encontrado. Funcionalidade de processamento desabilitada.")


class LogManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações da janela
        self.title("Gerenciador de Logs")
        self.geometry("900x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Backend Zig (opcional - pode não estar disponível)
        self.zig_backend = None
        if ZigBackend:
            try:
                self.zig_backend = ZigBackend()
            except (FileNotFoundError, RuntimeError) as e:
                print(f"Aviso: Backend Zig não disponível: {e}")

        # Dados da tabela
        self.dados_tabela = []

        # Criar interface
        self.create_top_frame()
        self.create_table_frame()
        self.create_button_frame()

    def create_top_frame(self):
        """Frame com inputs e controles"""
        frame = ctk.CTkFrame(self)
        frame.pack(pady=10, padx=10, fill="x")

        # Linha 1: Arquivo JSON
        ctk.CTkLabel(frame, text="Arquivo JSON:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.entry_json = ctk.CTkEntry(frame, width=500)
        self.entry_json.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(
            frame, text="Abrir Arquivo", command=self.browse_file, width=120
        ).grid(row=0, column=2, padx=5, pady=5)

        frame.grid_columnconfigure(1, weight=1)

        # Linha 2: Busca
        ctk.CTkLabel(frame, text="Buscar:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.entry_search = ctk.CTkEntry(frame, width=500)
        self.entry_search.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.entry_search.bind("<KeyRelease>", self.on_search_change)
        ctk.CTkButton(
            frame, text="Buscar", command=self.search_term, width=120
        ).grid(row=1, column=2, padx=5, pady=5)

    def create_table_frame(self):
        """Frame com tabela"""
        frame = ctk.CTkFrame(self)
        frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        # Treeview (tabela)
        self.table = ttk.Treeview(
            frame,
            columns=("arquivo", "metros", "data"),
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="extended",
        )

        self.table.heading("arquivo", text="Nome do Arquivo")
        self.table.heading("metros", text="Metros")
        self.table.heading("data", text="Data da Impressão")

        self.table.column("arquivo", width=450)
        self.table.column("metros", width=150, anchor="center")
        self.table.column("data", width=250, anchor="center")

        self.table.pack(fill="both", expand=True, padx=5, pady=5)
        scrollbar.configure(command=self.table.yview)

        # Estilo para alternância de cores
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            rowheight=25,
        )
        style.map("Treeview", background=[("selected", "#1f538d")])
        style.configure(
            "Treeview.Heading",
            background="#1f538d",
            foreground="white",
            relief="flat",
        )

    def create_button_frame(self):
        """Frame com botões de ação"""
        frame = ctk.CTkFrame(self)
        frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkButton(
            frame, text="Carregar Tabela", command=self.load_table, width=150
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            frame, text="Limpar Tabela", command=self.clear_table, width=150
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            frame, text="Somar Linhas", command=self.sum_rows, width=150
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            frame, text="Processar Logs", command=self.process_logs, width=150
        ).pack(side="left", padx=5)

    def browse_file(self):
        """Abre diálogo para selecionar arquivo JSON"""
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if filename:
            self.entry_json.delete(0, "end")
            self.entry_json.insert(0, filename)

    def load_table(self):
        """Carrega dados do JSON na tabela"""
        caminho_json = self.entry_json.get().strip()
        if not caminho_json:
            messagebox.showwarning("Aviso", "Por favor, selecione um arquivo JSON.")
            return

        if not os.path.exists(caminho_json):
            messagebox.showerror("Erro", f"Arquivo não encontrado: {caminho_json}")
            return

        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                dados = json.load(f)

            if not isinstance(dados, list):
                messagebox.showerror("Erro", "O JSON deve ser um array de objetos.")
                return

            # Limpar tabela antes de carregar
            self.clear_table()

            # Carregar dados
            self.dados_tabela = dados
            for item in dados:
                nome = item.get("nome_arquivo", "")
                metros = item.get("metros", 0.0)
                data = item.get("data_impressao", "")

                self.table.insert(
                    "",
                    "end",
                    values=(nome, f"{metros:.2f}", data),
                )

            messagebox.showinfo(
                "Sucesso", f"Carregados {len(dados)} registros na tabela."
            )

        except json.JSONDecodeError as e:
            messagebox.showerror("Erro", f"Erro ao decodificar JSON: {e}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivo: {e}")

    def clear_table(self):
        """Limpa todos os dados da tabela"""
        for item in self.table.get_children():
            self.table.delete(item)
        self.dados_tabela = []

    def on_search_change(self, event=None):
        """Busca em tempo real enquanto digita"""
        self.search_term()

    def search_term(self):
        """Busca termo nos nomes de arquivo"""
        termo = self.entry_search.get().strip().lower()

        # Limpar seleção anterior
        for item in self.table.get_children():
            self.table.set(item, "arquivo", self.table.item(item)["values"][0])

        if not termo:
            return

        # Destacar linhas que contêm o termo
        encontrados = 0
        for item in self.table.get_children():
            valores = self.table.item(item)["values"]
            nome_arquivo = valores[0].lower() if valores else ""
            if termo in nome_arquivo:
                encontrados += 1
                # Selecionar item
                self.table.selection_add(item)
                self.table.see(item)

        if encontrados == 0:
            messagebox.showinfo("Busca", f"Nenhum arquivo encontrado com o termo '{termo}'.")
        else:
            # Scroll para primeiro item encontrado
            selecionados = self.table.selection()
            if selecionados:
                self.table.see(selecionados[0])

    def sum_rows(self):
        """Soma metros das linhas selecionadas"""
        selecionados = self.table.selection()
        if not selecionados:
            messagebox.showwarning(
                "Aviso", "Por favor, selecione uma ou mais linhas para somar."
            )
            return

        total = 0.0
        for item_id in selecionados:
            valores = self.table.item(item_id)["values"]
            if len(valores) >= 2:
                try:
                    metros = float(valores[1])
                    total += metros
                except ValueError:
                    pass

        messagebox.showinfo(
            "Soma de Metros",
            f"Total de metros das linhas selecionadas: {total:.2f} m\n"
            f"({len(selecionados)} linha(s) selecionada(s))",
        )

    def process_logs(self):
        """Abre diálogo e processa logs usando backend Zig"""
        if not self.zig_backend:
            messagebox.showerror(
                "Erro",
                "Backend Zig não disponível.\n"
                "Certifique-se de que a biblioteca foi compilada e está em ./dist/",
            )
            return

        # Diálogo para selecionar diretório de origem
        origem = filedialog.askdirectory(title="Selecionar diretório com arquivos HTML")
        if not origem:
            return

        # Diálogo para selecionar diretório de destino
        destino = filedialog.askdirectory(
            title="Selecionar diretório de destino para JSON"
        )
        if not destino:
            return

        try:
            # Mostrar progresso
            self.update()
            messagebox.showinfo(
                "Processando",
                f"Processando arquivos HTML de:\n{origem}\n\n"
                f"Resultado será salvo em:\n{destino}\n\n"
                "Aguarde...",
            )

            # Processar usando backend Zig
            sucesso = self.zig_backend.processar_diretorio(origem, destino)

            if sucesso:
                caminho_resultado = os.path.join(destino, "resultado.json")
                messagebox.showinfo(
                    "Sucesso",
                    f"Processamento concluído com sucesso!\n\n"
                    f"Resultado salvo em:\n{caminho_resultado}\n\n"
                    f"Atualize o campo 'Arquivo JSON' e clique em 'Carregar Tabela'.",
                )
                # Atualizar campo de arquivo JSON
                self.entry_json.delete(0, "end")
                self.entry_json.insert(0, caminho_resultado)
            else:
                messagebox.showerror(
                    "Erro", "Erro ao processar logs. Verifique os arquivos HTML."
                )

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao processar logs: {e}")


if __name__ == "__main__":
    app = LogManagerApp()
    app.mainloop()

