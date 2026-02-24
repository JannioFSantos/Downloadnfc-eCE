"""
Módulo de lógica de download para DownloadNFCCE.

Contém a lógica principal de download e processamento de lote de NFC-e.
"""

import threading
import time
from pathlib import Path
from typing import List, Tuple

from .utils import parse_chaves, ensure_directory, is_file_downloaded
from .web_automation import PortalSVRS, check_playwright_availability


class DownloadManager:
    """Gerenciador de downloads de NFC-e."""
    
    def __init__(
        self,
        timeout_ms: int = 45000,
        pre_consulta_wait_ms: int = 60000,
        pos_download_wait_ms: int = 2000,
        espera_entre_rodadas_s: int = 5,
    ):
        """
        Inicializa o gerenciador de downloads.
        
        Args:
            timeout_ms (int): Timeout para operações em milissegundos
            pre_consulta_wait_ms (int): Tempo de espera antes da consulta
            pos_download_wait_ms (int): Tempo de espera após o download
            espera_entre_rodadas_s (int): Intervalo entre rodadas de download
        """
        self.timeout_ms = timeout_ms
        self.pre_consulta_wait_ms = pre_consulta_wait_ms
        self.pos_download_wait_ms = pos_download_wait_ms
        self.espera_entre_rodadas_s = espera_entre_rodadas_s
    
    def execute_download(
        self,
        chaves: List[str],
        out_dir: Path,
        profile_dir: Path,
        log_func,
    ) -> Tuple[int, int, List[str]]:
        """
        Executa o download de múltiplas NFC-e.
        
        Args:
            chaves (List[str]): Lista de chaves NFC-e
            out_dir (Path): Diretório de saída
            profile_dir (Path): Diretório do perfil do navegador
            log_func (callable): Função para registrar mensagens de log
            
        Returns:
            Tuple[int, int, List[str]]: (quantidade_ok, quantidade_erro, chaves_faltantes)
        """
        if not check_playwright_availability():
            raise ImportError("Playwright não está instalado")
        
        # Garante que os diretórios existam
        out_dir = ensure_directory(out_dir)
        profile_dir = ensure_directory(profile_dir)
        
        # Processa chaves
        total = len(chaves)
        chaves_unicas = list(dict.fromkeys(chaves))
        faltantes = [c for c in chaves_unicas if not is_file_downloaded(out_dir, c)]
        ja_baixadas = [c for c in chaves_unicas if c not in faltantes]
        
        if ja_baixadas:
            log_func(f"[INFO] {len(ja_baixadas)} chave(s) já estavam baixadas na pasta de saída.")
        
        # Executa downloads
        with PortalSVRS(profile_dir, self.timeout_ms) as portal:
            portal.wait_for_authentication(log_func)
            log_func("[INFO] Página de download pronta.")
            
            rodada = 0
            first_consulta_done = False
            
            while faltantes:
                rodada += 1
                log_func(f"[INFO] Rodada {rodada} - faltantes: {len(faltantes)}")
                rodada_alvo = list(faltantes)
                
                for i, chave in enumerate(rodada_alvo, start=1):
                    if is_file_downloaded(out_dir, chave):
                        continue
                    
                    log_func(f"[{i}/{len(rodada_alvo)}] Consultando {chave}...")
                    
                    try:
                        status, detalhe = portal.download_xml_by_key(
                            chave,
                            out_dir,
                            pre_consulta_wait_ms=self.pre_consulta_wait_ms,
                            pos_download_wait_ms=self.pos_download_wait_ms,
                            apply_pre_wait=first_consulta_done,
                        )
                        first_consulta_done = True
                        
                        if status and is_file_downloaded(out_dir, chave):
                            log_func(f"[OK] {chave} -> {detalhe}")
                        else:
                            log_func(f"[ERRO] {detalhe}")
                    except Exception as exc:
                        first_consulta_done = True
                        log_func(f"[ERRO] {chave}: {exc}")
                    finally:
                        log_func("[INFO] Reabrindo página para próxima chave...")
                        portal.return_to_form(log_func)
                
                faltantes = [c for c in chaves_unicas if not is_file_downloaded(out_dir, c)]
                
                if faltantes:
                    amostra = ", ".join(faltantes[:5])
                    log_func(
                        f"[WARN] Ainda faltam {len(faltantes)} chave(s). "
                        f"Nova rodada em {self.espera_entre_rodadas_s}s. Ex.: {amostra}"
                    )
                    portal.page.wait_for_timeout(max(0, self.espera_entre_rodadas_s) * 1000)
        
        # Contabiliza resultados
        ok = len([c for c in chaves_unicas if is_file_downloaded(out_dir, c)])
        erro = total - ok
        
        return ok, erro, faltantes


def download_nfce(
    chaves: List[str],
    out_dir: Path,
    profile_dir: Path,
    timeout_ms: int = 45000,
    pre_consulta_wait_ms: int = 60000,
    pos_download_wait_ms: int = 2000,
    espera_entre_rodadas_s: int = 5,
    log_func=None,
) -> Tuple[int, int, List[str]]:
    """
    Função principal para download de NFC-e.
    
    Args:
        chaves (List[str]): Lista de chaves NFC-e
        out_dir (Path): Diretório de saída
        profile_dir (Path): Diretório do perfil do navegador
        timeout_ms (int): Timeout para operações
        pre_consulta_wait_ms (int): Tempo de espera antes da consulta
        pos_download_wait_ms (int): Tempo de espera após o download
        espera_entre_rodadas_s (int): Intervalo entre rodadas
        log_func (callable): Função para registrar mensagens de log
        
    Returns:
        Tuple[int, int, List[str]]: Resultados do download
    """
    if log_func is None:
        def log_func(msg): print(msg)
    
    manager = DownloadManager(
        timeout_ms=timeout_ms,
        pre_consulta_wait_ms=pre_consulta_wait_ms,
        pos_download_wait_ms=pos_download_wait_ms,
        espera_entre_rodadas_s=espera_entre_rodadas_s,
    )
    
    return manager.execute_download(chaves, out_dir, profile_dir, log_func)


class DownloadWorker:
    """Worker para execução de download em thread separada."""
    
    def __init__(self, download_func, *args, **kwargs):
        """
        Inicializa o worker.
        
        Args:
            download_func (callable): Função de download a ser executada
            *args, **kwargs: Argumentos para a função de download
        """
        self.download_func = download_func
        self.args = args
        self.kwargs = kwargs
        self.thread = None
        self.result = None
        self.exception = None
    
    def start(self) -> None:
        """Inicia a execução em thread separada."""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def _run(self) -> None:
        """Executa a função de download."""
        try:
            self.result = self.download_func(*self.args, **self.kwargs)
        except Exception as exc:
            self.exception = exc
    
    def join(self, timeout=None) -> None:
        """Aguarda a conclusão da thread."""
        if self.thread:
            self.thread.join(timeout)
    
    def is_alive(self) -> bool:
        """Verifica se a thread ainda está em execução."""
        return self.thread and self.thread.is_alive()