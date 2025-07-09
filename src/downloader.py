
import os
import gzip
import hashlib
import requests
from datetime import datetime
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SourceDownloader:
    def __init__(self, source_url: str, data_dir: str = "data/raw"):
        self.source_url = source_url
        self.data_dir = data_dir
        self.raw_filename = "source_data.xml.gz"
        self.extracted_filename = "source_data.xml"
        self.hash_filename = "source_hash.txt"
        
        # Criar diretório se não existir
        os.makedirs(data_dir, exist_ok=True)
        
    def _calculate_hash(self, filepath: str) -> str:
        """Calcula hash SHA256 do arquivo"""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _get_stored_hash(self) -> Optional[str]:
        """Obtém hash armazenado do último download"""
        hash_path = os.path.join(self.data_dir, self.hash_filename)
        if os.path.exists(hash_path):
            with open(hash_path, 'r') as f:
                return f.read().strip()
        return None
    
    def _store_hash(self, file_hash: str):
        """Armazena hash do arquivo atual"""
        hash_path = os.path.join(self.data_dir, self.hash_filename)
        with open(hash_path, 'w') as f:
            f.write(file_hash)
    
    def download_and_extract(self, force: bool = False) -> Tuple[bool, str]:
        """
        Baixa e extrai o arquivo XML
        
        Args:
            force: Força download mesmo se não houver alterações
            
        Returns:
            Tuple[bool, str]: (foi_atualizado, caminho_arquivo_extraido)
        """
        raw_path = os.path.join(self.data_dir, self.raw_filename)
        extracted_path = os.path.join(self.data_dir, self.extracted_filename)
        
        logger.info(f"Iniciando download de {self.source_url}")
        
        try:
            # Download do arquivo
            response = requests.get(self.source_url, timeout=30)
            response.raise_for_status()
            
            # Salvar arquivo comprimido
            with open(raw_path, 'wb') as f:
                f.write(response.content)
            
            # Calcular hash do arquivo baixado
            current_hash = self._calculate_hash(raw_path)
            stored_hash = self._get_stored_hash()
            
            # Verificar se houve mudança
            if not force and current_hash == stored_hash:
                logger.info("Arquivo não foi modificado desde o último download")
                if os.path.exists(extracted_path):
                    return False, extracted_path
            
            # Extrair arquivo gzip
            logger.info("Extraindo arquivo comprimido")
            with gzip.open(raw_path, 'rb') as f_in:
                with open(extracted_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            # Armazenar hash
            self._store_hash(current_hash)
            
            logger.info(f"Download e extração concluídos: {extracted_path}")
            return True, extracted_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro no download: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            raise
    
    def get_file_info(self) -> dict:
        """Retorna informações sobre o arquivo atual"""
        raw_path = os.path.join(self.data_dir, self.raw_filename)
        extracted_path = os.path.join(self.data_dir, self.extracted_filename)
        
        info = {
            "raw_exists": os.path.exists(raw_path),
            "extracted_exists": os.path.exists(extracted_path),
            "raw_size": os.path.getsize(raw_path) if os.path.exists(raw_path) else 0,
            "extracted_size": os.path.getsize(extracted_path) if os.path.exists(extracted_path) else 0,
            "last_modified": None
        }
        
        if os.path.exists(extracted_path):
            info["last_modified"] = datetime.fromtimestamp(
                os.path.getmtime(extracted_path)
            ).isoformat()
        
        return info
