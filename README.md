# Sistema de Gerenciamento de Logs

Sistema híbrido de gerenciamento de logs de impressoras/plotters com interface gráfica moderna em Python e processamento de alto desempenho em Zig.

## 📋 Descrição

Este sistema permite processar arquivos HTML de logs de impressoras, extrair informações relevantes (nome do arquivo, dimensões, data de impressão, quantidade de cópias) e calcular métricas como metros de material utilizado. A interface gráfica permite visualizar, buscar e somar dados de forma intuitiva.

## 🏗️ Arquitetura

O sistema utiliza uma arquitetura híbrida:

- **Frontend (GUI)**: Python 3.12 com CustomTkinter para interface moderna e responsiva
- **Backend (processamento)**: Zig 0.15.2 compilado como shared library (.so/.dll)
- **Comunicação**: FFI (Foreign Function Interface) via ctypes - Python carrega a biblioteca e chama funções diretamente

```
┌─────────────┐
│   Python    │  ──ctypes──>  ┌─────────────┐
│  (GUI App)  │               │ Zig Library │
│             │  <──FFI──────  │  (.so/.dll) │
└─────────────┘               └─────────────┘
```

**Por que Zig + Python?**
- Zig oferece performance e segurança de memória para processamento pesado
- Python oferece facilidade de desenvolvimento e bibliotecas ricas para GUI
- FFI permite integração direta sem overhead de subprocess

## 📦 Requisitos

### Zig
- **Versão**: 0.15.2
- **Instalação**: 
  ```bash
  # Linux (via package manager)
  # Arch Linux
  sudo pacman -S zig
  
  # Ubuntu/Debian
  # Baixar de: https://ziglang.org/download/
  
  # Verificar instalação
  zig version
  ```

### Python
- **Versão**: 3.12
- **Dependências**: CustomTkinter
  ```bash
  pip install -r frontend-python/requirements.txt
  ```

## 📁 Estrutura do Projeto

```
log-manager/
├── backend-zig/
│   ├── src/
│   │   └── main.zig          # Backend com funções exportadas para FFI
│   ├── build.zig             # Build script do Zig
│   └── build.zig.zon         # Dependências (se necessário)
├── frontend-python/
│   ├── gui_app.py            # Interface CustomTkinter
│   ├── zig_bridge.py         # Bridge Python ↔ Zig via ctypes
│   └── requirements.txt      # customtkinter
├── dist/                     # Binários compilados
│   ├── liblogparser.so       # Linux
│   └── logparser.dll         # Windows
├── build.sh                  # Script de build
└── README.md
```

## 🔨 Compilação

### Linux (Desenvolvimento)

```bash
cd backend-zig
zig build -Dtarget=native -Doptimize=ReleaseFast
mkdir -p ../dist
cp zig-out/lib/liblogparser.so ../dist/
```

### Cross-compilação para Windows

```bash
cd backend-zig
zig build -Dtarget=x86_64-windows -Doptimize=ReleaseFast
cp zig-out/lib/logparser.dll ../dist/
```

### Script Automatizado

Use o script `build.sh` para compilar ambas as plataformas:

```bash
./build.sh
```

Este script:
1. Compila para Linux nativo
2. Cross-compila para Windows
3. Copia os binários para `dist/`

## 🚀 Como Executar

1. **Compile o backend Zig** (se ainda não compilou):
   ```bash
   ./build.sh
   ```

2. **Instale as dependências Python**:
   ```bash
   cd frontend-python
   pip install -r requirements.txt
   ```

3. **Execute a aplicação**:
   ```bash
   python frontend-python/gui_app.py
   ```

## 🎯 Funcionalidades

### Interface Gráfica

- **Carregar Tabela**: Carrega dados de um arquivo JSON e exibe na tabela
- **Limpar Tabela**: Remove todos os dados da tabela
- **Buscar**: Busca arquivos por nome (busca em tempo real)
- **Somar Linhas**: Calcula a soma de metros das linhas selecionadas
- **Processar Logs**: Processa diretório de arquivos HTML e gera JSON

### Backend Zig

O backend expõe as seguintes funções via FFI:

1. **`processarHtml`**: Processa um arquivo HTML individual
   - Entrada: caminho do HTML, caminho de saída JSON
   - Saída: 0 (sucesso) ou -1 (erro)

2. **`processarCsv`**: Processa um arquivo CSV individual
   - Entrada: caminho do CSV, caminho de saída JSON
   - Saída: 0 (sucesso) ou -1 (erro)

3. **`processarDiretorio`**: Processa todos os arquivos HTML e CSV de um diretório
   - Entrada: diretório origem, diretório destino
   - Saída: JSON consolidado em `resultado.json`
   - Detecta automaticamente HTML e CSV pela extensão

4. **`calcularMetros`**: Calcula metros baseado em dimensão e cópias
   - Fórmula: `(altura_cm × quantidade_cópias) / 100`

5. **`limparNomeArquivo`**: Remove caminho completo, retorna apenas nome

## Formatos Suportados

O sistema processa dois formatos de log:

### HTML

- **Máquinas**: DX-1602, DX-1604
- **Estrutura**: Tabelas HTML com pares `<TH>` / `<TD>`
- **Encoding**: latin-1 ou UTF-8
- **Extensões**: `.html`, `.HTML`

O parser espera HTML com estrutura de tabela:

```html
<table>
  <tr><th>INICIAR TRABALHO DE RIP</th></tr>
  <tr><th>ARQUIVO:</th><td>C:\caminho\arquivo.pdf</td></tr>
  <tr><th>DIMENSÃO:</th><td>100 x 150 cm</td></tr>
  <tr><th>INÍCIO, DATA E HORA DO RIP:</th><td>2024-09-15 14:30:00</td></tr>
  <tr><th>QUANTIDADE DE CÓPIAS:</th><td>2</td></tr>
</table>
```

### CSV

- **Máquinas**: [A definir conforme máquinas que geram CSV]
- **Estrutura**: Colunas separadas por vírgula
- **Encoding**: UTF-8
- **Extensões**: `.csv`, `.CSV`
- **Formato**: 
  ```csv
  Data,Hora,Arquivo,Largura,Altura,Unidade,Copias
  03/01/2024,07:47:47,PAINEL PATRULHA CANINA 11.tif,158.0,158.0,cm,1
  03/01/2024,12:45:36,GIRAFA malha 158x210.tif,158.0,210.4,cm,1
  ```

**Campos CSV:**
- `Data`: Data no formato DD/MM/YYYY
- `Hora`: Hora no formato HH:MM:SS
- `Arquivo`: Nome do arquivo (pode incluir caminho)
- `Largura`: Largura em cm ou polegadas
- `Altura`: Altura em cm ou polegadas
- `Unidade`: Unidade de medida (`cm` ou `in`/`inch`/`inches`)
- `Copias`: Quantidade de cópias (número inteiro)

**Conversão de Unidades:**
- Se a unidade for `in`, `IN`, `inch` ou `inches`, a altura é convertida para cm (multiplicando por 2.54)
- O cálculo de metros sempre usa cm: `metros = (altura_cm × quantidade_cópias) / 100`

O sistema detecta automaticamente o formato pela extensão do arquivo.

### Formato de Saída (JSON)

```json
[
  {
    "nome_arquivo": "arquivo.pdf",
    "metros": 3.0,
    "data_impressao": "2024-09-15 14:30:00"
  }
]
```

## 💻 Exemplo de Uso

### Via Python (GUI)

1. Abra a aplicação: `python frontend-python/gui_app.py`
2. Clique em "Processar Logs"
3. Selecione o diretório com arquivos HTML e/ou CSV
4. Selecione o diretório de destino
5. Aguarde o processamento (o sistema detecta automaticamente HTML e CSV)
6. Clique em "Carregar Tabela" para visualizar os resultados

### Via Python (Programático)

```python
from zig_bridge import ZigBackend

# Carregar backend
backend = ZigBackend()

# Processar diretório
sucesso = backend.processar_diretorio(
    "/caminho/html",
    "/caminho/json"
)

if sucesso:
    print("Processamento concluído!")
```

## 🔧 Detalhes Técnicos

### Encoding

- Os arquivos HTML são assumidos como UTF-8 ou latin-1 compatível
- O parser é simples e busca padrões específicos no HTML

### Cálculo de Metros

- Extrai altura da dimensão (formato: "largura x altura cm")
- Fórmula: `metros = (altura_cm × quantidade_cópias) / 100`

### Tratamento de Erros

- Funções retornam `0` para sucesso, `-1` para erro
- Arquivos com erro são pulados durante processamento de diretório
- Mensagens de erro são exibidas na interface gráfica

## 🐛 Troubleshooting

### Biblioteca não encontrada

**Erro**: `FileNotFoundError: Biblioteca não encontrada: ./dist/liblogparser.so`

**Solução**:
1. Verifique se compilou o backend: `./build.sh`
2. Verifique se o arquivo existe: `ls -lh dist/`
3. Certifique-se de executar a partir do diretório raiz do projeto

### Erros de encoding

**Erro**: Caracteres estranhos no JSON gerado

**Solução**:
- O parser assume UTF-8. Se seus HTMLs estão em latin-1, pode ser necessário converter antes do processamento

### Cross-compilação falha

**Erro**: Erro ao compilar para Windows

**Solução**:
1. Verifique se o Zig está atualizado: `zig version` (deve ser 0.15.2)
2. Tente compilar manualmente:
   ```bash
   cd backend-zig
   zig build -Dtarget=x86_64-windows -Doptimize=ReleaseFast
   ```

### Interface não abre

**Erro**: Erro ao importar CustomTkinter

**Solução**:
```bash
pip install --upgrade customtkinter
```

### Backend não disponível

**Aviso**: "Backend Zig não disponível"

**Solução**:
1. Compile o backend primeiro
2. Certifique-se de que está executando do diretório raiz
3. Verifique permissões do arquivo .so/.dll

## 📝 Notas de Desenvolvimento

### Parser HTML

O parser é **intencionalmente simples** e busca padrões específicos:
- Usa `std.mem.indexOf` para encontrar tags
- Não usa bibliotecas externas de parsing
- Específico para o formato dos logs de impressora

### Gerenciamento de Memória

- Zig usa `GeneralPurposeAllocator` para alocação
- Memória é liberada automaticamente com `defer`
- Strings C são null-terminated para compatibilidade FFI

### Build System

- `build.zig` configura a compilação como shared library
- Suporta diferentes targets (native, x86_64-windows)
- Otimização: `ReleaseFast` para performance máxima

## 📄 Licença

Este projeto é de código aberto. Sinta-se livre para usar e modificar conforme necessário.

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:
1. Faça fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Abra um Pull Request

## 📧 Suporte

Para problemas ou dúvidas:
- Abra uma issue no repositório
- Verifique a seção de Troubleshooting acima

---

**Desenvolvido com ❤️ usando Zig e Python**
