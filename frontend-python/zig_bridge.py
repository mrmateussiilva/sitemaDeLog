import ctypes
import platform
import os


class ZigBackend:
    def __init__(self):
        # Detecta sistema e carrega biblioteca apropriada
        sistema = platform.system()
        if sistema == "Linux":
            lib_path = "./dist/liblogparser.so"
        elif sistema == "Windows":
            lib_path = "./dist/logparser.dll"
        else:
            raise RuntimeError(f"Sistema não suportado: {sistema}")

        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Biblioteca não encontrada: {lib_path}")

        # Carrega biblioteca
        self.lib = ctypes.CDLL(lib_path)

        # Define assinaturas das funções
        self.lib.processarHtml.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.processarHtml.restype = ctypes.c_int

        self.lib.processarDiretorio.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.processarDiretorio.restype = ctypes.c_int

        self.lib.calcularMetros.argtypes = [ctypes.c_char_p, ctypes.c_int]
        self.lib.calcularMetros.restype = ctypes.c_double

        self.lib.limparNomeArquivo.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        self.lib.limparNomeArquivo.restype = ctypes.c_int

    def processar_html(self, caminho_html: str, caminho_json: str) -> bool:
        """Processa um arquivo HTML individual"""
        html_bytes = caminho_html.encode("utf-8")
        json_bytes = caminho_json.encode("utf-8")
        result = self.lib.processarHtml(html_bytes, json_bytes)
        return result == 0

    def processar_diretorio(self, origem: str, destino: str) -> bool:
        """Processa todos os HTMLs de um diretório"""
        origem_bytes = origem.encode("utf-8")
        destino_bytes = destino.encode("utf-8")
        result = self.lib.processarDiretorio(origem_bytes, destino_bytes)
        return result == 0

    def calcular_metros(self, dimensao: str, copias: int) -> float:
        """Calcula metros baseado na dimensão e quantidade"""
        dimensao_bytes = dimensao.encode("utf-8")
        return self.lib.calcularMetros(dimensao_bytes, copias)

    def limpar_nome(self, caminho: str) -> str:
        """Remove caminho completo, retorna apenas nome do arquivo"""
        caminho_bytes = caminho.encode("utf-8")
        buffer = ctypes.create_string_buffer(256)
        result = self.lib.limparNomeArquivo(caminho_bytes, buffer, 256)
        if result == 0:
            return buffer.value.decode("utf-8")
        return ""

