"""
Módulo de utilitários para DownloadNFCCE.

Contém funções de validação, parsing e formatação de dados.
"""

import re
from pathlib import Path
from typing import List


def parse_chaves(raw_text: str) -> List[str]:
    """
    Extrai e valida chaves NFC-e de 44 dígitos de um texto.
    
    Args:
        raw_text (str): Texto contendo chaves NFC-e
        
    Returns:
        List[str]: Lista de chaves válidas de 44 dígitos sem duplicatas
    """
    tokens = re.split(r"[\s,;]+", raw_text.strip())
    chaves = []
    vistos = set()
    
    for token in tokens:
        # Remove todos os caracteres não numéricos
        num = re.sub(r"\D", "", token)
        # Valida chave de 44 dígitos e evita duplicatas
        if len(num) == 44 and num not in vistos:
            chaves.append(num)
            vistos.add(num)
    
    return chaves


def format_elapsed_time(seconds: int) -> str:
    """
    Formata tempo em segundos para formato HH:MM:SS.
    
    Args:
        seconds (int): Tempo em segundos
        
    Returns:
        str: Tempo formatado em HH:MM:SS
    """
    h, rem = divmod(max(0, seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def validate_chave(chave: str) -> bool:
    """
    Valida se uma chave NFC-e tem formato correto.
    
    Args:
        chave (str): Chave NFC-e para validação
        
    Returns:
        bool: True se a chave é válida, False caso contrário
    """
    return bool(re.match(r"^\d{44}$", chave))


def ensure_directory(path: Path) -> Path:
    """
    Garante que um diretório exista, criando-o se necessário.
    
    Args:
        path (Path): Caminho do diretório
        
    Returns:
        Path: Caminho do diretório garantido
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_file_downloaded(out_dir: Path, chave: str) -> bool:
    """
    Verifica se um arquivo XML já foi baixado.
    
    Args:
        out_dir (Path): Diretório de saída
        chave (str): Chave NFC-e
        
    Returns:
        bool: True se o arquivo já foi baixado, False caso contrário
    """
    return (out_dir / f"{chave}.xml").is_file()