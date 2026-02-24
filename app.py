"""
DownloadNFCCE - Sistema de Download de XML NFC-e do Portal SVRS

Aplicativo principal com interface gráfica.
"""

from downloadnfcce.gui import App


def main() -> int:
    try:
        app = App()
        app.mainloop()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Erro ao iniciar interface gráfica: {e}")
        return 1


if __name__ == "__main__":
    exit(main())