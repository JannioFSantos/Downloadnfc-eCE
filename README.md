# DownloadNFCCE

download de XML de NFC-e no portal SVRS (Secretaria da Fazenda do Rio Grande do Sul).





### Estrutura de Diretórios

```
downloadnfcce/
├── __init__.py          # Definições do pacote
├── utils.py            # Utilitários e validações
├── web_automation.py   # Automação web (Playwright)
├── downloader.py       # Gerenciamento de downloads
├── gui.py              # Interface gráfica (Tkinter)
            
            
     
```

##  Requisitos

- Python 3.10+
- Playwright (para automação web)
- Tkinter (para interface gráfica)

##  Instalação

```bash
# Instalar dependências
python -m pip install -r requirements.txt

# Instalar navegador Chromium para Playwright
python -m playwright install chromium
```

## Modo de Uso

### Interface

```bash
python app.py
```



