import os
import logging
import shutil
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

# Imports corrigidos - usar imports absolutos em vez de relativos
from downloader import SourceDownloader
from xml_handler import XmlTimeAdjuster
from utils import load_config, save_config, validate_config, create_processing_report, ensure_directories

logger = logging.getLogger(__name__)

class ScheduleProcessor:
    def __init__(self, config_path: str = "config/channel-offsets.json", default_offset: int = 30):
        self.config_path = config_path
        self.default_offset = default_offset
        self.config = None
        self.downloader = None
        self.xml_adjuster = None
        
        # Diretórios
        self.data_dir = "data"
        self.raw_dir = os.path.join(self.data_dir, "raw")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        self.logs_dir = "logs"
        self.config_dir = "config"
        
        # Garantir que diretórios existem
        ensure_directories([self.raw_dir, self.processed_dir, self.logs_dir, self.config_dir])
        
    def load_configuration(self):
        """Carrega e valida configuração"""
        logger.info("Carregando configuração...")
        
        try:
            # Verificar se arquivo existe
            if not os.path.exists(self.config_path):
                logger.warning(f"Arquivo de configuração não encontrado: {self.config_path}")
                self.create_default_config()
            
            self.config = load_config(self.config_path)
            
            # Aplicar offset padrão se não estiver na configuração
            if 'default_offset' not in self.config:
                self.config['default_offset'] = self.default_offset
                save_config(self.config, self.config_path)
                logger.info(f"Offset padrão definido: {self.default_offset}s")
            
            if not validate_config(self.config):
                raise ValueError("Configuração inválida")
            
            logger.info(f"Configuração carregada: {len(self.config.get('channels', {}))} canais configurados")
            logger.info(f"Offset padrão: {self.config['default_offset']}s")
            
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            raise
    
    def create_default_config(self):
        """Cria arquivo de configuração padrão"""
        logger.info("Criando configuração padrão...")
        
        default_config = {
            "default_offset": self.default_offset,
            "source_url": "https://epgshare01.online/epgshare01/epg_ripper_PT1.xml.gz",
            "output_file": "adjusted_schedule.xml.gz",
            "channels": {
                "example_channel": {
                    "offset": 0,
                    "enabled": True,
                    "description": "Exemplo de configuração de canal"
                }
            },
            "processing": {
                "check_source_changes": True,
                "backup_original": True,
                "compress_output": True,
                "cleanup_old_files": True,
                "max_backup_files": 5
            }
        }
        
        # Garantir que diretório existe
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        save_config(default_config, self.config_path)
        logger.info(f"Configuração padrão criada: {self.config_path}")
    
    def initialize_components(self):
        """Inicializa componentes do processador"""
        if not self.config:
            raise ValueError("Configuração não carregada")
        
        # URL da fonte da configuração ou padrão
        source_url = self.config.get('source_url', 'https://epgshare01.online/epgshare01/epg_ripper_PT1.xml.gz')
        
        # Inicializar downloader
        self.downloader = SourceDownloader(source_url, self.raw_dir)
        
        # Inicializar ajustador XML
        self.xml_adjuster = XmlTimeAdjuster()
        
        logger.info("Componentes inicializados")
    
    def download_source(self, force: bool = False) -> Tuple[bool, str]:
        """
        Baixa arquivo fonte
        
        Returns:
            Tuple[bool, str]: (foi_atualizado, caminho_arquivo)
        """
        logger.info("Verificando atualizações da fonte...")
        
        try:
            updated, file_path = self.downloader.download_and_extract(force=force)
            
            if updated:
                logger.info("Nova versão da fonte baixada")
            else:
                logger.info("Fonte já está atualizada")
            
            return updated, file_path
            
        except Exception as e:
            logger.error(f"Erro no download: {e}")
            raise
    
    def cleanup_old_files(self):
        """Remove arquivos antigos do diretório processed"""
        try:
            if not self.config.get('processing', {}).get('cleanup_old_files', False):
                return
                
            max_files = self.config.get('processing', {}).get('max_backup_files', 5)
            
            # Listar arquivos XML no diretório processed
            processed_files = []
            for file in os.listdir(self.processed_dir):
                if file.startswith('schedule_adjusted_') and file.endswith('.xml'):
                    file_path = os.path.join(self.processed_dir, file)
                    processed_files.append((file_path, os.path.getmtime(file_path)))
            
            # Ordenar por data de modificação (mais recente primeiro)
            processed_files.sort(key=lambda x: x[1], reverse=True)
            
            # Remover arquivos antigos
            for file_path, _ in processed_files[max_files:]:
                try:
                    os.remove(file_path)
                    # Remover também a versão comprimida se existir
                    gz_path = file_path + '.gz'
                    if os.path.exists(gz_path):
                        os.remove(gz_path)
                    logger.info(f"Arquivo antigo removido: {file_path}")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo {file_path}: {e}")
                    
        except Exception as e:
            logger.warning(f"Erro na limpeza de arquivos antigos: {e}")
    
    def process_schedules(self, input_path: str) -> str:
        """
        Processa arquivo XML aplicando ajustes de tempo
        
        Args:
            input_path: Caminho do arquivo de entrada
            
        Returns:
            str: Caminho do arquivo processado
        """
        logger.info("Iniciando processamento de horários...")
        
        try:
            # Gerar nome do arquivo de saída
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"schedule_adjusted_{timestamp}.xml"
            output_path = os.path.join(self.processed_dir, output_filename)
            
            # Extrair configurações de offset
            channel_offsets = {}
            channels_config = self.config.get('channels', {})
            
            for channel_id, config in channels_config.items():
                if config.get('enabled', True):  # Só processar canais habilitados
                    channel_offsets[channel_id] = config.get('offset', 0)
            
            default_offset = self.config.get('default_offset', self.default_offset)
            
            logger.info(f"Processando com offset padrão: {default_offset}s")
            logger.info(f"Canais com offset personalizado: {len(channel_offsets)}")
            
            # Processar XML
            self.xml_adjuster.process_xml(
                input_path=input_path,
                output_path=output_path,
                channel_offsets=channel_offsets,
                default_offset=default_offset
            )
            
            # Criar versão comprimida se habilitado
            if self.config.get('processing', {}).get('compress_output', True):
                compressed_path = output_path + ".gz"
                self.xml_adjuster.create_compressed_output(output_path, compressed_path)
                logger.info(f"Versão comprimida criada: {compressed_path}")
            
            logger.info(f"Processamento concluído: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            raise
    
    def create_output_files(self, processed_path: str):
        """
        Cria arquivos de saída na pasta raiz e symlinks
        """
        try:
            # Arquivo comprimido na pasta raiz
            output_filename = self.config.get('output_file', 'adjusted_schedule.xml.gz')
            root_gz_path = output_filename
            compressed_source = processed_path + ".gz"
            
            if os.path.exists(compressed_source):
                # Copiar para pasta raiz
                shutil.copy2(compressed_source, root_gz_path)
                logger.info(f"Arquivo principal criado: {root_gz_path}")
                
                # Verificar tamanho do arquivo
                size = os.path.getsize(root_gz_path)
                logger.info(f"Tamanho do arquivo: {size:,} bytes ({size/1024/1024:.2f} MB)")
            else:
                logger.warning(f"Arquivo comprimido não encontrado: {compressed_source}")
            
            # Symlink para XML na pasta processed
            latest_xml = os.path.join(self.processed_dir, "latest.xml")
            if os.path.exists(latest_xml) or os.path.islink(latest_xml):
                os.remove(latest_xml)
            
            # Usar caminho relativo para symlink
            rel_path = os.path.relpath(processed_path, self.processed_dir)
            os.symlink(rel_path, latest_xml)
            
            # Symlink para XML comprimido na pasta processed
            latest_gz = os.path.join(self.processed_dir, "latest.xml.gz")
            if os.path.exists(latest_gz) or os.path.islink(latest_gz):
                os.remove(latest_gz)
            
            # Usar caminho relativo para symlink
            rel_path_gz = os.path.relpath(processed_path + ".gz", self.processed_dir)
            os.symlink(rel_path_gz, latest_gz)
            
            logger.info("Arquivos de saída e symlinks criados")
            
        except Exception as e:
            logger.warning(f"Erro ao criar arquivos de saída: {e}")
    
    def generate_report(self, output_path: str):
        """Gera relatório de processamento"""
        try:
            stats = self.xml_adjuster.get_processing_stats()
            
            # Adicionar informações do arquivo
            if os.path.exists(output_path):
                stats['output_file'] = output_path
                stats['output_size_mb'] = os.path.getsize(output_path) / (1024 * 1024)
            
            # Informações da fonte
            file_info = self.downloader.get_file_info()
            stats['source_info'] = file_info
            
            # Informações de configuração
            stats['config_info'] = {
                'default_offset': self.config.get('default_offset'),
                'channels_count': len(self.config.get('channels', {})),
                'enabled_channels': sum(1 for c in self.config.get('channels', {}).values() if c.get('enabled', True))
            }
            
            # Salvar relatório
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(self.logs_dir, f"processing_report_{timestamp}.json")
            create_processing_report(stats, report_path)
            
            logger.info(f"Relatório gerado: {report_path}")
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")
    
    def run(self, force_download: bool = False) -> bool:
        """
        Executa processo completo
        
        Args:
            force_download: Força download mesmo sem alterações
            
        Returns:
            bool: True se processamento foi executado com sucesso
        """
        try:
            logger.info("=== Iniciando processamento de horários ===")
            
            # Carregar configuração
            self.load_configuration()
            
            # Inicializar componentes
            self.initialize_components()
            
            # Baixar fonte
            updated, source_path = self.download_source(force=force_download)
            
            # Processar se houve atualização ou forçado
            if updated or force_download:
                logger.info("Processando horários...")
                
                # Processar XML
                output_path = self.process_schedules(source_path)
                
                # Criar arquivos de saída na raiz e symlinks
                self.create_output_files(output_path)
                
                # Gerar relatório
                self.generate_report(output_path)
                
                # Limpeza de arquivos antigos
                self.cleanup_old_files()
                
                logger.info("=== Processamento concluído com sucesso ===")
                return True
            else:
                logger.info("Nenhum processamento necessário - fonte não foi atualizada")
                return False
                
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            raise
