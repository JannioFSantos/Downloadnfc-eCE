"""
Módulo de interface gráfica para DownloadNFCCE.

Contém a classe App que implementa a interface gráfica do usuário.
"""

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .downloader import DownloadWorker, download_nfce
from .utils import parse_chaves, format_elapsed_time


class App(tk.Tk):
    """Aplicação GUI para download de NFC-e."""
    
    def __init__(self):
        """Inicializa a aplicação GUI."""
        super().__init__()
        self.title("Download XML NFC-e (Portal SVRS)")
        self.geometry("980x720")
        
        # Componentes de controle
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: DownloadWorker | None = None
        self.operation_start_ts: float | None = None
        
        # Variáveis de controle
        self.var_out = tk.StringVar(value=str(Path.cwd() / "downloads"))
        self.var_profile = tk.StringVar(value=str(Path.cwd() / ".playwright-profile"))
        self.var_timeout = tk.StringVar(value="45000")
        self.var_wait_pre_consulta = tk.StringVar(value="60000")
        self.var_wait_pos_download = tk.StringVar(value="2000")
        self.var_wait_rodadas = tk.StringVar(value="5")
        self.var_elapsed = tk.StringVar(value="00:00:00")
        
        # Constrói a interface
        self._build_ui()
        
        # Inicia processos de atualização
        self._drain_logs()
        self._update_elapsed_label()
    
    def _build_ui(self) -> None:
        """Constrói a interface gráfica."""
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        
        # Área de entrada de chaves
        ttk.Label(root, text="Cole as chaves NFC-e (uma por linha, espaço, vírgula ou ';')").pack(anchor="w")
        self.txt_chaves = tk.Text(root, height=12)
        self.txt_chaves.pack(fill="x", pady=(4, 10))
        
        # Configuração de diretórios
        self._create_directory_frame(root)
        
        # Configuração de timeouts
        self._create_timeout_frame(root)
        
        # Configuração de tempos
        self._create_timing_frame(root)
        
        # Botões de controle
        self._create_control_frame(root)
        
        # Área de log
        ttk.Label(root, text="Log").pack(anchor="w")
        self.txt_log = tk.Text(root, height=18, state="disabled")
        self.txt_log.pack(fill="both", expand=True, pady=(4, 0))
    
    def _create_directory_frame(self, parent: ttk.Frame) -> None:
        """Cria o frame de configuração de diretórios."""
        frm_out = ttk.Frame(parent)
        frm_out.pack(fill="x", pady=4)
        
        ttk.Label(frm_out, text="Pasta de saída:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_out, textvariable=self.var_out).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(frm_out, text="Selecionar", command=self._select_output_dir).grid(row=0, column=2)
        frm_out.columnconfigure(1, weight=1)
        
        frm_prof = ttk.Frame(parent)
        frm_prof.pack(fill="x", pady=4)
        
        ttk.Label(frm_prof, text="Perfil do navegador:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_prof, textvariable=self.var_profile).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(frm_prof, text="Selecionar", command=self._select_profile_dir).grid(row=0, column=2)
        frm_prof.columnconfigure(1, weight=1)
    
    def _create_timeout_frame(self, parent: ttk.Frame) -> None:
        """Cria o frame de configuração de timeout."""
        frm_timeout = ttk.Frame(parent)
        frm_timeout.pack(fill="x", pady=4)
        
        ttk.Label(frm_timeout, text="Timeout operação (ms):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_timeout, textvariable=self.var_timeout, width=16).grid(row=0, column=1, sticky="w", padx=6)
    
    def _create_timing_frame(self, parent: ttk.Frame) -> None:
        """Cria o frame de configuração de tempos."""
        frm_timing = ttk.Frame(parent)
        frm_timing.pack(fill="x", pady=4)
        
        ttk.Label(frm_timing, text="Espera antes consulta (ms):").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm_timing, textvariable=self.var_wait_pre_consulta, width=10).grid(row=0, column=1, sticky="w", padx=6)
        
        ttk.Label(frm_timing, text="Espera após download (ms):").grid(row=0, column=2, sticky="w")
        ttk.Entry(frm_timing, textvariable=self.var_wait_pos_download, width=10).grid(row=0, column=3, sticky="w", padx=6)
        
        ttk.Label(frm_timing, text="Intervalo rodadas (s):").grid(row=0, column=4, sticky="w")
        ttk.Entry(frm_timing, textvariable=self.var_wait_rodadas, width=8).grid(row=0, column=5, sticky="w", padx=6)
    
    def _create_control_frame(self, parent: ttk.Frame) -> None:
        """Cria o frame de controles e botões."""
        frm_btn = ttk.Frame(parent)
        frm_btn.pack(fill="x", pady=(8, 10))
        
        self.btn_start = ttk.Button(frm_btn, text="Iniciar Download", command=self._start_download)
        self.btn_start.pack(side="left")
        
        ttk.Label(frm_btn, text="Tempo da operação:").pack(side="left", padx=(16, 4))
        ttk.Label(frm_btn, textvariable=self.var_elapsed).pack(side="left")
    
    def _log(self, msg: str) -> None:
        """Adiciona mensagem ao log."""
        self.log_queue.put(msg)
    
    def _drain_logs(self) -> None:
        """Processa mensagens do log em segundo plano."""
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", msg + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.after(120, self._drain_logs)
    
    def _update_elapsed_label(self) -> None:
        """Atualiza o rótulo de tempo decorrido."""
        if self.operation_start_ts is None:
            self.var_elapsed.set("00:00:00")
        else:
            elapsed = int(time.time() - self.operation_start_ts)
            self.var_elapsed.set(format_elapsed_time(elapsed))
        self.after(1000, self._update_elapsed_label)
    
    def _select_output_dir(self) -> None:
        """Seleciona o diretório de saída."""
        d = filedialog.askdirectory()
        if d:
            self.var_out.set(d)
    
    def _select_profile_dir(self) -> None:
        """Seleciona o diretório do perfil."""
        d = filedialog.askdirectory()
        if d:
            self.var_profile.set(d)
    
    def _start_download(self) -> None:
        """Inicia o processo de download."""
        # Verifica se já está em execução
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("Em execução", "Já existe um processamento em andamento.")
            return
        
        # Verifica dependências
        if not self._check_dependencies():
            return
        
        # Processa chaves
        chaves = parse_chaves(self.txt_chaves.get("1.0", "end"))
        if not chaves:
            messagebox.showerror("Erro", "Nenhuma chave válida de 44 dígitos encontrada.")
            return
        
        # Valida parâmetros
        if not self._validate_parameters():
            return
        
        # Configura parâmetros
        out_dir = Path(self.var_out.get().strip() or "downloads")
        profile_dir = Path(self.var_profile.get().strip() or ".playwright-profile")
        timeout_ms = int(self.var_timeout.get().strip())
        pre_consulta_wait_ms = int(self.var_wait_pre_consulta.get().strip())
        pos_download_wait_ms = int(self.var_wait_pos_download.get().strip())
        espera_entre_rodadas_s = int(self.var_wait_rodadas.get().strip())
        
        # Inicia download
        self.operation_start_ts = time.time()
        self.btn_start.configure(state="disabled")
        
        self.worker = DownloadWorker(
            download_nfce,
            chaves,
            out_dir,
            profile_dir,
            timeout_ms,
            pre_consulta_wait_ms,
            pos_download_wait_ms,
            espera_entre_rodadas_s,
            self._log,
        )
        self.worker.start()
        
        # Monitora conclusão
        self.after(1000, self._check_worker_status)
    
    def _check_dependencies(self) -> bool:
        """Verifica se as dependências estão disponíveis."""
        try:
            from .web_automation import check_playwright_availability
            if not check_playwright_availability():
                messagebox.showerror(
                    "Dependência ausente",
                    "Playwright não instalado.\n\nExecute:\npython -m pip install playwright\npython -m playwright install chromium",
                )
                return False
        except ImportError:
            messagebox.showerror(
                "Dependência ausente",
                "Playwright não instalado.\n\nExecute:\npython -m pip install playwright\npython -m playwright install chromium",
            )
            return False
        return True
    
    def _validate_parameters(self) -> bool:
        """Valida os parâmetros de configuração."""
        try:
            timeout_ms = int(self.var_timeout.get().strip())
            if timeout_ms <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Timeout inválido.")
            return False
        
        try:
            pre_consulta_wait_ms = int(self.var_wait_pre_consulta.get().strip())
            pos_download_wait_ms = int(self.var_wait_pos_download.get().strip())
            espera_entre_rodadas_s = int(self.var_wait_rodadas.get().strip())
            if min(pre_consulta_wait_ms, pos_download_wait_ms, espera_entre_rodadas_s) < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Tempos inválidos.")
            return False
        
        return True
    
    def _check_worker_status(self) -> None:
        """Verifica o status do worker e trata conclusão."""
        if self.worker and not self.worker.is_alive():
            self._handle_completion()
        else:
            self.after(1000, self._check_worker_status)
    
    def _handle_completion(self) -> None:
        """Trata a conclusão do download."""
        started_at = self.operation_start_ts or time.time()
        
        if self.worker and self.worker.exception:
            self._log(f"[FALHA] {self.worker.exception}")
            self.after(0, lambda: messagebox.showerror("Falha", str(self.worker.exception)))
        elif self.worker and self.worker.result:
            ok, erro, faltantes = self.worker.result
            self._log(f"[FIM] Total={len(parse_chaves(self.txt_chaves.get('1.0', 'end')))} | OK={ok} | ERRO={erro}")
            
            if not faltantes:
                self._log("[SUCESSO] Todas as chaves estão na pasta de saída.")
            else:
                self._log(f"[PENDENTE] {len(faltantes)} chave(s) não foram baixadas.")
                self._log("[PENDENTE] " + ", ".join(faltantes))
        
        total_s = int(time.time() - started_at)
        self._log(f"[TEMPO] Duração total: {format_elapsed_time(total_s)}")
        
        self.operation_start_ts = None
        self.btn_start.configure(state="normal")