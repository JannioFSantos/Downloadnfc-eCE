"""
Módulo de automação web para DownloadNFCCE.

Contém funções para interação com o portal SVRS usando Playwright.
"""

import time
from pathlib import Path
from typing import Tuple

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .utils import is_file_downloaded


# URLs do portal SVRS
PORTAL_URL = "https://dfe-portal.svrs.rs.gov.br/nfc"
DOWNLOAD_PAGE_URL = "https://dfe-portal.svrs.rs.gov.br/NfceSSL/DownloadXmlDfe"
BLOCKED_H4_XPATH = "//*[@id='bodyPricipal']/div[1]/div/div/div[1]/div/div/div/article/div[2]/div/div/div[2]/h4"


class PortalSVRS:
    """Classe para automação do portal SVRS."""
    
    def __init__(self, profile_dir: Path, timeout_ms: int = 45000):
        """
        Inicializa o automator do portal SVRS.
        
        Args:
            profile_dir (Path): Diretório do perfil do navegador
            timeout_ms (int): Timeout para operações em milissegundos
        """
        self.profile_dir = profile_dir
        self.timeout_ms = timeout_ms
        self.context = None
        self.page = None
        self.playwright = None
    
    def __enter__(self):
        """Context manager entry."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright não está instalado")
        
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir.resolve()),
            headless=False,
            accept_downloads=True,
            args=["--start-maximized"],
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
    
    def wait_for_authentication(self, log_func) -> None:
        """
        Aguarda autenticação no portal SVRS.
        
        Args:
            log_func (callable): Função para registrar mensagens de log
        """
        self.page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        log_func("[INFO] Portal aberto. Tentando acessar página de download...")
        self.page.goto(DOWNLOAD_PAGE_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        
        try:
            self.page.wait_for_selector("#ChaveAcessoDfe", timeout=self.timeout_ms)
            return
        except PlaywrightTimeoutError:
            log_func("[INFO] Selecione o certificado no navegador. Aguardando autenticação...")
        
        self.page.wait_for_selector("#ChaveAcessoDfe", timeout=180000)
    
    def refresh_page_double(self) -> None:
        """Realiza refresh duplo na página para garantir carregamento."""
        for _ in range(2):
            self.page.keyboard.press("F5")
            self.page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
            self.page.wait_for_selector("#ChaveAcessoDfe", timeout=self.timeout_ms)
    
    def download_xml_by_key(
        self,
        chave: str,
        out_dir: Path,
        pre_consulta_wait_ms: int = 60000,
        pos_download_wait_ms: int = 2000,
        apply_pre_wait: bool = True,
    ) -> Tuple[bool, str]:
        """
        Realiza download de XML por chave NFC-e.
        
        Args:
            chave (str): Chave NFC-e de 44 dígitos
            out_dir (Path): Diretório de saída para o download
            pre_consulta_wait_ms (int): Tempo de espera antes da consulta
            pos_download_wait_ms (int): Tempo de espera após o download
            apply_pre_wait (bool): Aplicar espera antes da consulta
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem/detalhe)
        """
        self.page.fill("#ChaveAcessoDfe", chave)
        self.refresh_page_double()
        self.page.fill("#ChaveAcessoDfe", chave)
        
        if apply_pre_wait:
            self.page.wait_for_timeout(max(0, pre_consulta_wait_ms))
        
        self.page.click("#frmDownloadXmlDfe button[type='submit']")
        
        # Aguarda resultado com prioridade para detectar tela de bloqueio/erro
        deadline = time.monotonic() + (self.timeout_ms / 1000.0)
        while time.monotonic() < deadline:
            if self.page.locator(f"xpath={BLOCKED_H4_XPATH}").count() > 0:
                texto_bloqueio = self.page.locator(f"xpath={BLOCKED_H4_XPATH}").first.inner_text().strip()
                if "bloqueio" in texto_bloqueio.lower() or "ip" in texto_bloqueio.lower():
                    try:
                        self.page.goto(DOWNLOAD_PAGE_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
                        self.page.wait_for_selector("#ChaveAcessoDfe", timeout=self.timeout_ms)
                    except Exception:
                        self.refresh_page_double()
                return False, f"{chave}: página de bloqueio/erro detectada ({texto_bloqueio})"
            
            if self.page.locator("#btnExportar").count() > 0:
                break
            self.page.wait_for_timeout(300)
        
        if self.page.locator("#btnExportar").count() == 0:
            return False, f"{chave}: botão de download não apareceu"
        
        if self.page.get_attribute("#btnExportar", "disabled") is not None:
            texto = self.page.locator("body").inner_text()
            resumo = " ".join(texto.split())[:220]
            return False, f"{chave}: download indisponível | {resumo}"
        
        with self.page.expect_download(timeout=self.timeout_ms) as info:
            self.page.click("#btnExportar")
            self.page.wait_for_timeout(max(0, pos_download_wait_ms))
        
        destino = out_dir / f"{chave}.xml"
        info.value.save_as(str(destino))
        return True, str(destino)
    
    def return_to_form(self, log_func) -> None:
        """
        Retorna para o formulário de download.
        
        Args:
            log_func (callable): Função para registrar mensagens de log
        """
        try:
            self.page.goto(DOWNLOAD_PAGE_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.page.wait_for_selector("#ChaveAcessoDfe", timeout=self.timeout_ms)
        except Exception as exc:
            log_func(f"[WARN] Não foi possível retornar automaticamente ao formulário: {exc}")


def check_playwright_availability() -> bool:
    """Verifica se o Playwright está disponível."""
    return PLAYWRIGHT_AVAILABLE