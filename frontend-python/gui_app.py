import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import sys
from datetime import datetime

# Adiciona o diretório do frontend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from zig_bridge import ZigBackend
except ImportError:
    ZigBackend = None
    print("Aviso: zig_bridge não encontrado. Funcionalidade de processamento desabilitada.")

# ATENÇÃO: import do watcher deve ficar após ajuste de sys.path
try:
    from utils.log_watcher import LogWatcher
except Exception:
    # Se der erro aqui, o modo automático ficará indisponível, mas o manual continua
    LogWatcher = None


class LogManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configurações da janela
        self.title("Gerenciador de Logs de Impressão")
        self.geometry("1200x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Cores customizadas
        self.colors = {
            "primary": "#1f538d",
            "success": "#28a745",
            "danger": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
        }

        # Backend Zig (opcional - pode não estar disponível)
        self.zig_backend = None
        if ZigBackend:
            try:
                self.zig_backend = ZigBackend()
            except (FileNotFoundError, RuntimeError) as e:
                print(f"Aviso: Backend Zig não disponível: {e}")

        # Dados da tabela
        self.dados_tabela = []

        # Estado do watcher (monitoramento automático)
        self.watcher = None  # ATENÇÃO: não renomear, usado em start_watcher/stop_watcher
        self.watcher_ativo = False
        self.modo_var = ctk.StringVar(value="manual")  # "manual" ou "auto"

        # Criar interface
        self.create_header()
        self.create_stats_cards()
        self.create_tabview()
        self.create_footer()

        # Garantir parada do watcher ao fechar
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_header(self):
        """Header com logo, título e botão de ajuda"""
        header_frame = ctk.CTkFrame(self, height=60, fg_color=self.colors["primary"])
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)

        # Título
        title = ctk.CTkLabel(
            header_frame,
            text="🖨️  Gerenciador de Logs de Impressão",
            font=("Arial", 20, "bold"),
            text_color="white",
        )
        title.pack(side="left", padx=20)

        # Botão help
        help_btn = ctk.CTkButton(
            header_frame,
            text="?",
            width=35,
            height=35,
            corner_radius=17,
            fg_color="#2c5f8d",
            hover_color="#1a4270",
            command=self.show_help,
        )
        help_btn.pack(side="right", padx=20)

    def create_stats_cards(self):
        """Cards de estatísticas"""
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=10)

        # Card 1: Total Impressões
        self.card_impressoes = self.create_stat_card(
            stats_frame, "📄", "Total de Impressões", "0", 0
        )

        # Card 2: Total Metros
        self.card_metros = self.create_stat_card(
            stats_frame, "📏", "Total de Metros", "0.0 m", 1
        )

        # Card 3: Arquivos
        self.card_arquivos = self.create_stat_card(
            stats_frame, "📁", "Arquivos Processados", "0", 2
        )

    def create_stat_card(self, parent, icon, title, value, column):
        """Card individual de estatística"""
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color=("#f0f0f0", "#2b2b2b"))
        card.grid(row=0, column=column, padx=10, pady=5, sticky="ew")
        parent.columnconfigure(column, weight=1)

        # Ícone
        icon_label = ctk.CTkLabel(card, text=icon, font=("Arial", 30))
        icon_label.pack(pady=(15, 5))

        # Título
        title_label = ctk.CTkLabel(
            card, text=title, font=("Arial", 11), text_color=("#333", "#ccc")
        )
        title_label.pack()

        # Valor
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=("Arial", 24, "bold"),
            text_color=self.colors["primary"],
        )
        value_label.pack(pady=(5, 15))

        return value_label  # Retorna para atualizar depois

    def create_tabview(self):
        """Sistema de abas"""
        self.tabview = ctk.CTkTabview(self, height=500)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        # Criar abas
        self.tabview.add("Visualizar")
        self.tabview.add("Processar")
        self.tabview.add("Relatórios")

        # Popular cada aba
        self.create_tab_visualizar()
        self.create_tab_processar()
        self.create_tab_relatorios()

    def create_tab_visualizar(self):
        """Aba 1: Visualizar Dados"""
        tab = self.tabview.tab("Visualizar")

        # Toolbar
        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        # Busca
        ctk.CTkLabel(toolbar, text="🔍 Buscar:", font=("Arial", 11)).pack(
            side="left", padx=5
        )
        self.search_entry = ctk.CTkEntry(
            toolbar, width=300, placeholder_text="Digite o nome do arquivo..."
        )
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search_change)

        ctk.CTkButton(
            toolbar, text="Buscar", width=100, command=self.search_term
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            toolbar, text="Limpar Busca", width=100, command=self.clear_search
        ).pack(side="left", padx=5)

        # Botões de ação
        ctk.CTkButton(
            toolbar, text="📊 Exportar CSV", width=120, command=self.export_csv
        ).pack(side="right", padx=5)

        # Frame para tabela
        table_frame = ctk.CTkFrame(tab)
        table_frame.pack(fill="both", expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        hsb = ttk.Scrollbar(table_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        # Treeview melhorada
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            borderwidth=0,
            font=("Arial", 10),
            rowheight=25,
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["primary"],
            foreground="white",
            font=("Arial", 11, "bold"),
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", self.colors["primary"])],
            foreground=[("selected", "white")],
        )

        self.table = ttk.Treeview(
            table_frame,
            columns=("arquivo", "metros", "data"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended",
        )

        # Configurar colunas
        self.table.heading("arquivo", text="Nome do Arquivo")
        self.table.heading("metros", text="Metros")
        self.table.heading("data", text="Data/Hora")

        self.table.column("arquivo", width=500, anchor="w")
        self.table.column("metros", width=150, anchor="center")
        self.table.column("data", width=250, anchor="center")

        self.table.pack(fill="both", expand=True, padx=5, pady=5)

        vsb.configure(command=self.table.yview)
        hsb.configure(command=self.table.xview)

        # Botões inferiores
        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            actions, text="📂 Carregar JSON", command=self.load_table, width=150
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            actions, text="🗑️ Limpar Tabela", command=self.clear_table, width=150
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            actions,
            text="➕ Somar Selecionados",
            command=self.sum_rows,
            width=150,
        ).pack(side="left", padx=5)

        # Label de info
        self.info_label = ctk.CTkLabel(
            actions, text="Nenhum arquivo carregado", font=("Arial", 10)
        )
        self.info_label.pack(side="right", padx=10)

        # Campo para arquivo JSON (oculto mas funcional)
        self.entry_json = ctk.CTkEntry(tab, width=0, height=0)
        self.entry_json.pack_forget()

    def create_tab_processar(self):
        """Aba 2: Processar Logs"""
        tab = self.tabview.tab("Processar")

        # Frame de configuração
        config_frame = ctk.CTkFrame(tab)
        config_frame.pack(fill="x", padx=10, pady=10)

        # Origem
        ctk.CTkLabel(
            config_frame,
            text="📁 Diretório de Origem:",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.origem_entry = ctk.CTkEntry(config_frame, width=400)
        self.origem_entry.grid(row=0, column=1, padx=10, pady=10)
        ctk.CTkButton(
            config_frame, text="Selecionar", width=100, command=self.select_origem
        ).grid(row=0, column=2, padx=10, pady=10)

        # Destino
        ctk.CTkLabel(
            config_frame,
            text="💾 Diretório de Destino:",
            font=("Arial", 12, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.destino_entry = ctk.CTkEntry(config_frame, width=400)
        self.destino_entry.grid(row=1, column=1, padx=10, pady=10)
        ctk.CTkButton(
            config_frame, text="Selecionar", width=100, command=self.select_destino
        ).grid(row=1, column=2, padx=10, pady=10)

        # ------------------------------------------------------------------
        # Modo de operação: Manual x Automático (file watcher)
        # ------------------------------------------------------------------
        modo_frame = ctk.CTkFrame(tab)
        modo_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            modo_frame, text="Modo de Operação:", font=("Arial", 11, "bold")
        ).grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Radio - Modo Manual (default)
        self.radio_manual = ctk.CTkRadioButton(
            modo_frame,
            text="Modo Manual (processamento sob demanda)",
            variable=self.modo_var,
            value="manual",
            command=self.toggle_modo,
        )
        self.radio_manual.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Radio - Modo Automático (monitorar em tempo real)
        self.radio_auto = ctk.CTkRadioButton(
            modo_frame,
            text="Modo Automático (monitorar pasta em tempo real)",
            variable=self.modo_var,
            value="auto",
            command=self.toggle_modo,
        )
        self.radio_auto.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Botão iniciar monitoramento
        self.btn_start_watch = ctk.CTkButton(
            modo_frame,
            text="▶ Iniciar Monitoramento",
            width=180,
            fg_color=self.colors["success"],
            hover_color="#218838",
            command=self.start_watcher,
        )
        self.btn_start_watch.grid(row=0, column=2, padx=10, pady=5)

        # Botão parar monitoramento
        self.btn_stop_watch = ctk.CTkButton(
            modo_frame,
            text="⏹ Parar Monitoramento",
            width=180,
            fg_color=self.colors["danger"],
            hover_color="#b52a3a",
            command=self.stop_watcher,
        )
        self.btn_stop_watch.grid(row=1, column=2, padx=10, pady=5)

        # Status do watcher
        self.watcher_status_label = ctk.CTkLabel(
            modo_frame,
            text="● Desativado",
            font=("Arial", 11, "bold"),
            text_color="#888888",
        )
        self.watcher_status_label.grid(row=0, column=3, padx=10, pady=5, sticky="e")

        modo_frame.grid_columnconfigure(1, weight=1)

        # Estado inicial dos botões conforme modo selecionado
        self.toggle_modo()

        # Filtros
        filter_frame = ctk.CTkFrame(tab)
        filter_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            filter_frame, text="Filtros:", font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.filter_html = ctk.CTkCheckBox(
            filter_frame, text="Processar HTML", onvalue=True, offvalue=False
        )
        self.filter_html.pack(side="left", padx=10)
        self.filter_html.select()

        self.filter_csv = ctk.CTkCheckBox(
            filter_frame, text="Processar CSV", onvalue=True, offvalue=False
        )
        self.filter_csv.pack(side="left", padx=10)
        self.filter_csv.select()

        # Progress
        progress_frame = ctk.CTkFrame(tab)
        progress_frame.pack(fill="x", padx=10, pady=10)

        self.progress_label = ctk.CTkLabel(
            progress_frame, text="Aguardando...", font=("Arial", 11)
        )
        self.progress_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=500)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        # Botão processar
        process_btn = ctk.CTkButton(
            tab,
            text="▶ PROCESSAR LOGS",
            height=50,
            font=("Arial", 14, "bold"),
            fg_color=self.colors["success"],
            hover_color="#218838",
            command=self.process_logs,
        )
        process_btn.pack(pady=20)

        # Log de processamento
        log_frame = ctk.CTkFrame(tab)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            log_frame, text="Log de Processamento:", font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            bg="#2b2b2b",
            fg="white",
            font=("Consolas", 9),
            insertbackground="white",
        )
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def create_tab_relatorios(self):
        """Aba 3: Relatórios"""
        tab = self.tabview.tab("Relatórios")

        # Filtros
        filter_frame = ctk.CTkFrame(tab)
        filter_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            filter_frame, text="Filtrar Dados:", font=("Arial", 12, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=5)

        # Data início
        ctk.CTkLabel(filter_frame, text="Data Início:").grid(
            row=1, column=0, padx=10, pady=5
        )
        self.date_inicio = ctk.CTkEntry(
            filter_frame, placeholder_text="DD/MM/YYYY", width=150
        )
        self.date_inicio.grid(row=1, column=1, padx=10, pady=5)

        # Data fim
        ctk.CTkLabel(filter_frame, text="Data Fim:").grid(
            row=2, column=0, padx=10, pady=5
        )
        self.date_fim = ctk.CTkEntry(
            filter_frame, placeholder_text="DD/MM/YYYY", width=150
        )
        self.date_fim.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkButton(
            filter_frame, text="Aplicar Filtros", command=self.apply_filters
        ).grid(row=3, column=0, columnspan=2, pady=10)

        # Resumo
        summary_frame = ctk.CTkFrame(tab)
        summary_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            summary_frame, text="Resumo Estatístico:", font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=10)

        self.summary_text = ctk.CTkTextbox(
            summary_frame, height=300, font=("Consolas", 10)
        )
        self.summary_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Botão gerar relatório
        ctk.CTkButton(
            tab,
            text="📄 Gerar Relatório PDF",
            height=40,
            command=self.generate_report,
        ).pack(pady=10)

    def create_footer(self):
        """Footer com informações de status"""
        footer = ctk.CTkFrame(self, height=30, fg_color=("#e0e0e0", "#2b2b2b"))
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            footer, text="✓ Pronto", font=("Arial", 9), text_color=("#333", "#ccc")
        )
        self.status_label.pack(side="left", padx=10)

        self.time_label = ctk.CTkLabel(
            footer, text="", font=("Arial", 9), text_color=("#333", "#ccc")
        )
        self.time_label.pack(side="right", padx=10)
        self.update_time()

    def update_time(self):
        """Atualiza hora atual no footer"""
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.configure(text=f"⏰ {now}")
        self.after(1000, self.update_time)

    # ========== FUNÇÕES DE UTILIDADE ==========

    def update_stats(self):
        """Atualiza cards de estatísticas"""
        total_impressoes = len(self.table.get_children())
        total_metros = 0.0
        for item in self.table.get_children():
            valores = self.table.item(item)["values"]
            if len(valores) >= 2:
                try:
                    total_metros += float(valores[1])
                except ValueError:
                    pass

        self.card_impressoes.configure(text=str(total_impressoes))
        self.card_metros.configure(text=f"{total_metros:.2f} m")
        self.card_arquivos.configure(text=str(total_impressoes))

    def log_message(self, message):
        """Adiciona mensagem ao log de processamento"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.update()

    def show_help(self):
        """Mostra janela de ajuda"""
        help_window = ctk.CTkToplevel(self)
        help_window.title("Ajuda - Gerenciador de Logs")
        help_window.geometry("500x450")

        help_text = """
GERENCIADOR DE LOGS DE IMPRESSÃO

Como usar:

1. ABA VISUALIZAR:
   - Clique em "Carregar JSON" para abrir um arquivo JSON
   - Use a busca para filtrar arquivos por nome
   - Selecione linhas e clique em "Somar Selecionados" 
     para calcular total de metros
   - Exporte os dados para CSV se necessário

2. ABA PROCESSAR:
   - Selecione pasta com logs (HTML/CSV)
   - Escolha pasta de destino para JSONs
   - Marque os tipos de arquivo a processar
   - Clique em "PROCESSAR LOGS"
   - Acompanhe o progresso no log

3. ABA RELATÓRIOS:
   - Filtre dados por período (data início/fim)
   - Veja estatísticas resumidas
   - Gere relatórios em PDF (em desenvolvimento)

Dicas:
- O sistema detecta automaticamente HTML e CSV
- Os dados são salvos em formato JSON unificado
- Use a busca para encontrar arquivos rapidamente
        """

        text_label = ctk.CTkLabel(
            help_window, text=help_text, justify="left", font=("Arial", 11)
        )
        text_label.pack(padx=20, pady=20)

    # ========== FUNÇÕES DA ABA VISUALIZAR ==========

    def load_table(self):
        """Carrega dados do JSON na tabela"""
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not filename:
            return

        if not os.path.exists(filename):
            messagebox.showerror("Erro", f"Arquivo não encontrado: {filename}")
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
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

            self.update_stats()
            self.info_label.configure(
                text=f"✓ {len(dados)} registros carregados"
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
        self.update_stats()
        self.info_label.configure(text="Nenhum arquivo carregado")

    def on_search_change(self, event=None):
        """Busca em tempo real enquanto digita"""
        self.search_term()

    def search_term(self):
        """Busca termo nos nomes de arquivo"""
        termo = self.search_entry.get().strip().lower()

        # Limpar seleção anterior
        for item in self.table.get_children():
            self.table.selection_remove(item)

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
            self.info_label.configure(
                text=f"⚠ Nenhum arquivo encontrado com '{termo}'"
            )
        else:
            self.info_label.configure(text=f"✓ {encontrados} arquivo(s) encontrado(s)")

    def clear_search(self):
        """Limpa a busca"""
        self.search_entry.delete(0, "end")
        for item in self.table.get_children():
            self.table.selection_remove(item)
        self.info_label.configure(
            text=f"{len(self.table.get_children())} registros"
        )

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

    def export_csv(self):
        """Exporta tabela atual para CSV"""
        if len(self.table.get_children()) == 0:
            messagebox.showwarning("Aviso", "Não há dados para exportar.")
            return

        filename = filedialog.asksaveasfilename(
            title="Salvar CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            import csv

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Nome do Arquivo", "Metros", "Data da Impressão"])

                for item in self.table.get_children():
                    valores = self.table.item(item)["values"]
                    writer.writerow(valores)

            messagebox.showinfo("Sucesso", f"CSV exportado para: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar CSV: {e}")

    # ========== FUNÇÕES DA ABA PROCESSAR ==========

    def select_origem(self):
        """Seleciona diretório de origem"""
        origem = filedialog.askdirectory(title="Selecionar diretório com arquivos HTML/CSV")
        if origem:
            self.origem_entry.delete(0, "end")
            self.origem_entry.insert(0, origem)

    def select_destino(self):
        """Seleciona diretório de destino"""
        destino = filedialog.askdirectory(
            title="Selecionar diretório de destino para JSON"
        )
        if destino:
            self.destino_entry.delete(0, "end")
            self.destino_entry.insert(0, destino)

    def process_logs(self):
        """Processa logs usando backend Zig"""
        if not self.zig_backend:
            messagebox.showerror(
                "Erro",
                "Backend Zig não disponível.\n"
                "Certifique-se de que a biblioteca foi compilada e está em ./dist/",
            )
            return

        origem = self.origem_entry.get().strip()
        destino = self.destino_entry.get().strip()

        if not origem:
            messagebox.showwarning("Aviso", "Selecione o diretório de origem.")
            return

        if not destino:
            messagebox.showwarning("Aviso", "Selecione o diretório de destino.")
            return

        if not os.path.exists(origem):
            messagebox.showerror("Erro", f"Diretório de origem não existe: {origem}")
            return

        try:
            # Limpar log anterior
            self.log_text.delete("1.0", "end")

            # Atualizar UI
            self.progress_label.configure(text="Processando...")
            self.progress_bar.set(0.3)
            self.log_message(f"Iniciando processamento...")
            self.log_message(f"Origem: {origem}")
            self.log_message(f"Destino: {destino}")
            self.update()

            # Processar usando backend Zig
            self.log_message("Chamando backend Zig...")
            sucesso = self.zig_backend.processar_diretorio(origem, destino)

            if sucesso:
                self.progress_bar.set(1.0)
                self.progress_label.configure(text="Concluído!")
                caminho_resultado = os.path.join(destino, "resultado.json")
                self.log_message(f"✓ Processamento concluído com sucesso!")
                self.log_message(f"Resultado salvo em: {caminho_resultado}")

                messagebox.showinfo(
                    "Sucesso",
                    f"Processamento concluído com sucesso!\n\n"
                    f"Resultado salvo em:\n{caminho_resultado}\n\n"
                    f"Vá para a aba 'Visualizar' e carregue o arquivo JSON.",
                )

                # Atualizar campo de destino
                self.destino_entry.delete(0, "end")
                self.destino_entry.insert(0, destino)
            else:
                self.progress_bar.set(0)
                self.progress_label.configure(text="Erro no processamento")
                self.log_message("✗ Erro ao processar logs")
                messagebox.showerror(
                    "Erro", "Erro ao processar logs. Verifique os arquivos e o log."
                )

        except Exception as e:
            self.progress_bar.set(0)
            self.progress_label.configure(text="Erro")
            self.log_message(f"✗ Erro: {str(e)}")
            messagebox.showerror("Erro", f"Erro ao processar logs: {e}")

    # ========== FUNÇÕES DO MODO AUTOMÁTICO (WATCHER) ==========

    def update_watcher_status(self, ativo: bool):
        """Atualiza label e flag de status do watcher."""
        self.watcher_ativo = ativo
        if ativo:
            self.watcher_status_label.configure(
                text="● Ativo", text_color=self.colors["success"]
            )
        else:
            self.watcher_status_label.configure(
                text="● Desativado", text_color="#888888"
            )

    def toggle_modo(self):
        """
        Alterna comportamento da UI entre modo manual e automático.
        # ATENÇÃO: NÃO alterar o comportamento do botão PROCESSAR LOGS (modo manual).
        """
        modo = self.modo_var.get()

        if modo == "manual":
            # Modo manual: watcher desabilitado por padrão
            self.btn_start_watch.configure(state="disabled")
            self.btn_stop_watch.configure(state="disabled")
            # Não força parada aqui para permitir parar explicitamente
            if not self.watcher_ativo:
                self.update_watcher_status(False)
        else:
            # Modo automático: habilita controle do watcher
            self.btn_start_watch.configure(state="normal")
            # Botão de parar só habilita se já estiver ativo
            self.btn_stop_watch.configure(
                state="normal" if self.watcher_ativo else "disabled"
            )

    def start_watcher(self):
        """Inicia o monitoramento automático de arquivos."""
        if LogWatcher is None:
            messagebox.showerror(
                "Erro",
                "Dependência watchdog não disponível ou erro ao carregar LogWatcher.\n"
                "Verifique se 'watchdog' está instalado.",
            )
            return

        if not self.zig_backend:
            messagebox.showerror(
                "Erro",
                "Backend Zig não disponível.\n"
                "Certifique-se de que a biblioteca foi compilada e está em ./dist/",
            )
            return

        origem = self.origem_entry.get().strip()
        destino = self.destino_entry.get().strip()

        if not origem:
            messagebox.showwarning("Aviso", "Selecione o diretório de origem.")
            return

        if not destino:
            messagebox.showwarning("Aviso", "Selecione o diretório de destino.")
            return

        if not os.path.exists(origem):
            messagebox.showerror("Erro", f"Diretório de origem não existe: {origem}")
            return

        try:
            # Parar watcher anterior, se existir
            if self.watcher is not None:
                try:
                    self.watcher.stop()
                except Exception:
                    pass
                self.watcher = None

            # Criar novo watcher
            self.watcher = LogWatcher(
                origem=origem,
                destino=destino,
                log_callback=self.log_message,  # ASSUMINDO QUE log_message existe
            )
            self.watcher.start()

            self.update_watcher_status(True)
            self.btn_start_watch.configure(state="disabled")
            self.btn_stop_watch.configure(state="normal")
            self.log_message("Monitoramento automático iniciado.")

        except Exception as e:
            self.update_watcher_status(False)
            self.btn_start_watch.configure(state="normal")
            self.btn_stop_watch.configure(state="disabled")
            self.log_message(f"✗ Erro ao iniciar monitoramento: {e}")
            messagebox.showerror("Erro", f"Erro ao iniciar monitoramento: {e}")

    def stop_watcher(self):
        """Interrompe o monitoramento automático, se ativo."""
        if self.watcher is not None:
            try:
                self.watcher.stop()
            except Exception:
                pass
            self.watcher = None

        self.update_watcher_status(False)
        # Se modo automático ainda estiver selecionado, permitir iniciar novamente
        if self.modo_var.get() == "auto":
            self.btn_start_watch.configure(state="normal")
            self.btn_stop_watch.configure(state="disabled")
        else:
            self.btn_start_watch.configure(state="disabled")
            self.btn_stop_watch.configure(state="disabled")

        self.log_message("Monitoramento automático parado.")

    # ========== FUNÇÕES DA ABA RELATÓRIOS ==========

    def apply_filters(self):
        """Aplica filtros de data"""
        date_inicio = self.date_inicio.get().strip()
        date_fim = self.date_fim.get().strip()

        # Por enquanto, apenas mostra mensagem
        messagebox.showinfo(
            "Filtros",
            f"Filtros aplicados:\nInício: {date_inicio or 'Não especificado'}\nFim: {date_fim or 'Não especificado'}",
        )

        # TODO: Implementar filtragem real dos dados

    def generate_report(self):
        """Gera relatório em PDF"""
        messagebox.showinfo(
            "Relatório",
            "Geração de relatório PDF em desenvolvimento.\n"
            "Esta funcionalidade será implementada em breve.",
        )

    def on_closing(self):
        """
        Handler de fechamento da janela.
        # ATENÇÃO: garantir que o watcher seja parado antes de destruir a janela.
        """
        try:
            self.stop_watcher()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = LogManagerApp()
    app.mainloop()
