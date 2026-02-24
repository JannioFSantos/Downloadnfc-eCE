# DownloadNFCCE

download de XML de NFC-e no portal SVRS (Secretaria da Fazenda do Rio Grande do Sul).



### Módulos Principais

- **`downloadnfcce/`** - Pacote principal do sistema
  - **`__init__.py`** - Definições do pacote
  - **`utils.py`** - Funções de utilitários (validação, parsing, formatação)
  - **`web_automation.py`** - Automação do portal SVRS com Playwright
  - **`downloader.py`** - Lógica de gerenciamento de downloads
  - **`gui.py`** - Interface gráfica do usuário
  

### Estrutura de Diretórios

```
downloadnfcce/
├── __init__.py          # Definições do pacote
├── utils.py            # Utilitários e validações
├── web_automation.py   # Automação web (Playwright)
├── downloader.py       # Gerenciamento de downloads
├── gui.py              # Interface gráfica (Tkinter)
            

app.py                  # Ponto de entrada principal
requirements.txt        # Dependências
README.md              # Documentação
downloads/             # Pasta de saída padrão
```

## 🚀 Requisitos

- Python 3.10+
- Playwright (para automação web)
- Tkinter (para interface gráfica)

## ⚙️ Instalação

```bash
# Instalar dependências
python -m pip install -r requirements.txt

# Instalar navegador Chromium para Playwright
python -m playwright install chromium
```

## 💻 Modo de Uso

### Interface Gráfica (Padrão)

```bash
python app.py
```



# Downloadnfc-eCE
