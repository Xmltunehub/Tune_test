import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
import sys

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Configura sistema de logging
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configurar nível de log
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configurar handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    # Configurar logging
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers,
        force=True
    )

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Carrega arquivo de configuração JSON
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Arquivo de configuração não encontrado: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao ler configuração JSON: {e}")
        raise

def save_config(config: Dict[str, Any], config_path: str):
    """
    Salva arquivo de configuração JSON
    """
    try:
        # Atualizar timestamp
        if 'metadata' in config:
            config['metadata']['last_updated'] = datetime.now().isoformat()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Configuração salva: {config_path}")
        
    except Exception as e:
        logging.error(f"Erro ao salvar configuração: {e}")
        raise

def ensure_directories(paths: list):
    """
    Garante que os diretórios existem
    """
    for path in paths:
        os.makedirs(path, exist_ok=True)

def get_file_size_mb(filepath: str) -> float:
    """
    Retorna tamanho do arquivo em MB
    """
    if os.path.exists(filepath):
        return os.path.getsize(filepath) / (1024 * 1024)
    return 0.0

def create_processing_report(stats: Dict[str, Any], output_path: str):
    """
    Cria relatório de processamento
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "processing_stats": stats,
        "success": stats.get("errors_count", 0) == 0
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Relatório salvo: {output_path}")
        
    except Exception as e:
        logging.error(f"Erro ao salvar relatório: {e}")

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Valida estrutura da configuração
    """
    required_keys = ['default_offset', 'channels']
    
    for key in required_keys:
        if key not in config:
            logging.error(f"Chave obrigatória ausente na configuração: {key}")
            return False
    
    # Validar tipo do offset padrão
    if not isinstance(config['default_offset'], int):
        logging.error("default_offset deve ser um inteiro")
        return False
    
    # Validar estrutura dos canais
    if not isinstance(config['channels'], dict):
        logging.error("channels deve ser um dicionário")
        return False
    
    # Validar cada canal
    for channel_id, channel_config in config['channels'].items():
        if not isinstance(channel_config, dict):
            logging.error(f"Configuração do canal {channel_id} deve ser um dicionário")
            return False
        
        if 'offset' not in channel_config:
            logging.error(f"Canal {channel_id} deve ter propriedade 'offset'")
            return False
        
        if not isinstance(channel_config['offset'], int):
            logging.error(f"Offset do canal {channel_id} deve ser um inteiro")
            return False
    
    logging.info("Configuração validada com sucesso")
    return True

def format_duration(seconds: int) -> str:
    """
    Formata duração em segundos para formato legível
    """
    if seconds == 0:
        return "0s"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0:
        parts.append(f"{secs}s")
    
    return " ".join(parts)
