import PySimpleGUI as sg
import os
import json
import functools
from bs4 import BeautifulSoup
from json import load, dump
from PySimpleGUI import popup_ok


""" CONSTANTES """
SIZE = (900, 700)
HEADERS_TABLE = [
    "Nome do Arquivo",
    "Metros",
    "Data da Impressão"]

PLOTTERS = {"mutoh": "1604", "prisamjet": "1602", "prismatetext": "1904"}

""" BACKEND """

CHAVES = (
    'ARQUIVO',
    'DIMENSÃO',
    'INÍCIO, DATA E HORA DO RIP',
    'PERFIL ICC DE SAÍDA',
    'QUANTIDADE DE CÓPIAS',
)


class ParserHtml:
    def __init__(self, encode) -> None:
        self.encode = encode

    def create_context_html(self, path_file_html: str):
        with open(path_file_html, "r", encoding=self.encode) as file:
            html_content = file.read()
        return BeautifulSoup(html_content, "html.parser")

    def struct_base_file(self, content_html, target_tag="table"):
        return list(content_html.find_all(target_tag))

    # @functools.lru_cache()
    def create_dict_dados(self, base_list):
        lista_dicionarios = []
        for tabela in base_list:
            chaves = list(map(lambda item: item.get_text().strip().replace(":", "").upper(),
                              tabela.find_all("th")))
            valores = list(map(lambda item: item.get_text().strip(),
                               tabela.find_all("td")))

            # removendo o primeiro elemento
            valor_0 = chaves.pop(0)

            if valor_0 == "INICIAR TRABALHO DE RIP":
                # # removendo o ultimo elemento
                chaves.pop(len(chaves) - 1)
                dicionario_temp = dict(zip(chaves, valores))
                dicionario = {}
                for chave, valor in dicionario_temp.items():
                    if chave in CHAVES:
                        dicionario[chave] = valor
                chaves.clear()
                valores.clear()

                lista_dicionarios.append(dicionario.copy())
                dicionario.clear()

        dicionarios = {
            f"imp_{k}": v
            for k, v in enumerate(lista_dicionarios)
        }

        return dicionarios


class PyJson:
    def __init__(self):
        pass

    def ler_json(self, nome_arquivo_json) -> dict:
        with open(nome_arquivo_json, "r") as file:
            data = load(file)
        return data

    def escrever_json(self, dados, nome_arquivo) -> bool:
        try:
            fp = open(nome_arquivo, "w+")
            dump(dados, fp)
        except:
            return False

        finally:
            fp.close()

        return True


def limpar_nome(texto):
    lista_texto = texto.split("\\")
    return lista_texto[len(lista_texto) - 1]


def limpar_dimensao(texto):
    return float(texto.replace("cm", "").split(" x ")[1])

@functools.lru_cache()
def orgnizar_lista(dicionario, env):

    for chave, valor in dicionario.items():
        if chave == "DIMENSÃO":
            qtd_copias = 1
            try:
                qtd_copias = int(dicionario["QUANTIDADE DE C\u00d3PIAS"])
            except:
                qtd_copias = 1
            metros = str(round(qtd_copias * limpar_dimensao(valor))/100)
            env.append(metros)
        elif chave == "ARQUIVO":
            nome_limpo = limpar_nome(valor)
            env.append(nome_limpo)
        elif chave != "QUANTIDADE DE C\u00d3PIAS" and \
                chave != "PERFIL ICC DE SA\u00cdDA":
            env.append(valor)

    return env

@functools.lru_cache()
def criar_matrix(dados: dict):
    matrix = []
    tmp = []
    for _, dado in dados.items():
        tmp = orgnizar_lista(dado, tmp)
        matrix.append(tmp[:])
        tmp.clear()
    return matrix


def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, "r") as file:
        dados = json.load(file)
    return dados


def validar_extensao(extensao_arquivo, extensao_alvo="html") -> bool:
    return True if extensao_arquivo.strip(".").lower() == extensao_alvo else False


def pegar_arquivos_html(path):
    import glob
    lista_arquivos = []
    for arquivo in os.listdir(path):
        _, extensao = os.path.splitext(arquivo)

        if validar_extensao(extensao):
            __ = os.path.join(path, arquivo)
            lista_arquivos.append(__)

    return sorted(lista_arquivos)


def verificar_pasta_existente(caminho_pasta: str) -> bool:
    if os.path.exists(caminho_pasta) and os.path.isdir(caminho_pasta):
        return True
    return False


def search_term(term:str, list_terms:str) -> str:
    impressoes = list_terms.values()
    nomes = list(map(lambda v : v.get("ARQUIVO"),impressoes))
    for nome in nomes:
        if term.lower() in nome.lower():
            return nome
    return ""
    

    # for t in list_terms:
    #     print(t,type(t))
    #     if term in t:
    #         return t
    # return None


""" FRONTEND """
layout = [

    [sg.Text("Caminho do arquivo json"), sg.Input(key="-PATH_JSON-"),
     sg.FileBrowse(button_text="Abrir Arquivo",
                   initial_folder="/media/mateus/D395-E345/ProjetctFiles/arquivos_json/arquivos_antigos/")
     ],
     [
        sg.Text("Digite o termo de busca"),sg.Input(key="-TERM_SEARCH-"),sg.Button("Buscar",key="-BTN_SEARCH-"),
     ],
    [sg.Table(values=[],
              headings=HEADERS_TABLE,
              enable_click_events=True, enable_events=True,
              col_widths=100,
              expand_x=True,
              expand_y=True,
              selected_row_colors="Red on Yellow", justification="left",
              auto_size_columns=True, size=(45, 32), alternating_row_color="Gray", k="-TABELA-",
              )
     ],
    [
        sg.Button("Gerar Tabela", key="-LOAD_TABLE-"),
        sg.Button("Limpar Tabela", key="-CLEAR_TABLE-"),
        sg.Button("Somar Linhas", key="-SUM_TABLES-"),
        sg.Button("Criar Json", key="-CREATE_JSON_FILES-"),
    ]

]


def carregar_frontend():
    window = sg.Window("Gerenciador de LOG", layout, size=SIZE)

    while 1:
        events, values = window.read()
        py_json = PyJson()
        valores = None

        if events == "-LOAD_TABLE-":
            valores = criar_matrix(py_json.ler_json(values["-PATH_JSON-"]))
            window["-TABELA-"].update(values=valores)
            window.refresh()
        elif events == "-CLEAR_TABLE-":
            window["-TABELA-"].update(values=[])
            window.refresh()
        elif events == "-BTN_SEARCH-":
            term = values["-TERM_SEARCH-"]
            valores = py_json.ler_json(values["-PATH_JSON-"])
            result = search_term(term,valores)
            popup_ok(result)
        elif events == "--":
            indices = values["-TABELA-"]
            s = 0
            for indice in indices:
                metros = float(valores[indice][1])
                s += metros
            msg = f"{s:.2f}"
            popup_ok(msg)

        elif events == "-CREATE_JSON_FILES-":
            criar_json_files()

        if events == sg.WIN_CLOSED:
            break

        # print(values)

    window.close()


@functools.lru_cache()
def criar_json_files():
    PATH = r"\\Storage-silkart\IMPRESSAO\LOGS DAS MAQUINAS\MAQUINAS"
    PATH_DESTINO = r"\\Storage-silkart\IMPRESSAO\LOGS DAS MAQUINAS\ARQUIVOS_JSON"
    ANO = "24"
    MESES = {
        "janeiro": f"01 {ANO}",
        "fevereiro": f"02 {ANO}",
        "março": f"03 {ANO}",
        "abril": f"04 {ANO}",
        "maio": f"05 {ANO}",
        "junho": f"06 {ANO}",
        "julho": f"07 {ANO}",
        "agosto": f"08 {ANO}",
        "setembro": f"09 {ANO}",
        "outubro": f"10 {ANO}",
        "novembro": f"11 {ANO}",
        "dezembro": f"12 {ANO}",
    }
    MES_ALVO = MESES["setembro"]
    parserhtml = ParserHtml("latin-1")
    pyjson = PyJson()
    for plotter in PLOTTERS.values():
        p = os.path.join(PATH, plotter)

        for mes in os.listdir(p):
            p_destino = os.path.join(PATH_DESTINO, plotter, mes)
            try:
                os.mkdir(p_destino)
            except Exception as error:
                pass
                print(error)

            if mes == MES_ALVO:
                arquivos = pegar_arquivos_html(
                    os.path.join(PATH, plotter, mes))
                for arquivo in arquivos:
                    novo_nome = pegar_nome_arquivo(
                        arquivo).replace(".HTML", ".json")
                    arquivo_destino = os.path.join(p_destino, novo_nome)
                    print(arquivo_destino)
                    contexto = parserhtml.create_context_html(arquivo)
                    listadados = parserhtml.struct_base_file(contexto)
                    matrixdicionarios = parserhtml.create_dict_dados(
                        listadados)
                    pyjson.escrever_json(
                        dados=matrixdicionarios,
                        nome_arquivo=arquivo_destino
                    )



def pegar_arquivos_html(path):
    arquivos = [
        os.path.join(path, file)
        for file in os.listdir(path)
        if os.path.isfile(os.path.join(path, file))
    ]
    return arquivos


def pegar_nome_arquivo(path):
    return os.path.split(path)[1]


if __name__ == "__main__":
    criar_json_files()
    #carregar_frontend()

                
                # print(pegar_arquivos_html(p))
        # print(p)