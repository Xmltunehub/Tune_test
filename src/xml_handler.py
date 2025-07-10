import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import gzip
import os

logger = logging.getLogger(__name__)

class XmlTimeAdjuster:
    def __init__(self, channel_offsets: Dict[str, Dict] = None, default_offset: int = 30):
        """
        Inicializa o ajustador de horários XML
        
        Args:
            channel_offsets: Dicionário com configurações por canal
            default_offset: Offset padrão em segundos
        """
        self.channel_offsets = channel_offsets or {}
        self.default_offset = default_offset
        self.processed_programmes = 0
        self.processed_channels = set()
        self.errors = []
        
    def parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """
        Converte string de data/hora do formato XML para datetime
        Formatos suportados: YYYYMMDDHHMMSS +TZTZ
        """
        try:
            # Remover timezone se presente
            if ' ' in dt_str:
                dt_part = dt_str.split(' ')[0]
            else:
                dt_part = dt_str
            
            # Converter para datetime
            return datetime.strptime(dt_part, "%Y%m%d%H%M%S")
        except ValueError as e:
            logger.warning(f"Erro ao converter data/hora '{dt_str}': {e}")
            return None
    
    def format_datetime(self, dt: datetime) -> str:
        """
        Converte datetime para formato XML
        """
        return dt.strftime("%Y%m%d%H%M%S +0000")
    
    def _adjust_time(self, time_str: str, offset_seconds: int) -> Optional[str]:
        """
        Ajusta uma string de tempo específica
        
        Args:
            time_str: String de tempo no formato XML
            offset_seconds: Segundos para ajustar
            
        Returns:
            String de tempo ajustada ou None se erro
        """
        try:
            dt = self.parse_datetime(time_str)
            if dt:
                adjusted_dt = dt + timedelta(seconds=offset_seconds)
                return self.format_datetime(adjusted_dt)
            return None
        except Exception as e:
            logger.warning(f"Erro ao ajustar tempo '{time_str}': {e}")
            return None
    
    def adjust_times(self, tree: ET.ElementTree, specific_channel: Optional[str] = None) -> ET.ElementTree:
        """
        Ajusta horários no XML EPG
        
        Args:
            tree: Árvore XML para processar
            specific_channel: Se especificado, processa apenas este canal
            
        Returns:
            Árvore XML com horários ajustados
        """
        root = tree.getroot()
        
        # Encontrar todos os programas
        if specific_channel:
            programmes = root.findall(f".//programme[@channel='{specific_channel}']")
            logger.info(f"Processando {len(programmes)} programas do canal {specific_channel}")
        else:
            programmes = root.findall('.//programme')
            logger.info(f"Processando {len(programmes)} programas total")
        
        for programme in programmes:
            channel_id = programme.get('channel')
            if not channel_id:
                continue
            
            # Obter offset para o canal
            channel_config = self.channel_offsets.get(channel_id, {})
            offset_seconds = channel_config.get('offset', self.default_offset)
            
            # Ajustar horário de início
            start_time = programme.get('start')
            if start_time:
                new_start = self._adjust_time(start_time, offset_seconds)
                if new_start:
                    programme.set('start', new_start)
            
            # Ajustar horário de fim
            stop_time = programme.get('stop')
            if stop_time:
                new_stop = self._adjust_time(stop_time, offset_seconds)
                if new_stop:
                    programme.set('stop', new_stop)
            
            self.processed_programmes += 1
            self.processed_channels.add(channel_id)
        
        logger.info(f"Processados {self.processed_programmes} programas de {len(self.processed_channels)} canais")
        return tree
    
    def adjust_program_times(self, program: ET.Element, offset_seconds: int):
        """
        Ajusta horários de um programa específico (método legado mantido para compatibilidade)
        """
        try:
            # Ajustar horário de início
            start_attr = program.get('start')
            if start_attr:
                new_start = self._adjust_time(start_attr, offset_seconds)
                if new_start:
                    program.set('start', new_start)
            
            # Ajustar horário de fim
            stop_attr = program.get('stop')
            if stop_attr:
                new_stop = self._adjust_time(stop_attr, offset_seconds)
                if new_stop:
                    program.set('stop', new_stop)
            
            self.processed_programmes += 1
            
        except Exception as e:
            error_msg = f"Erro ao ajustar programa: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
    
    def process_xml(self, input_path: str, output_path: str, channel_offsets: Dict[str, int] = None, default_offset: int = 30):
        """
        Processa o arquivo XML aplicando ajustes de tempo
        
        Args:
            input_path: Caminho do arquivo XML de entrada
            output_path: Caminho do arquivo XML de saída
            channel_offsets: Dicionário com ajustes por canal
            default_offset: Ajuste padrão em segundos
        """
        logger.info(f"Iniciando processamento: {input_path}")
        
        # Atualizar configurações se fornecidas
        if channel_offsets:
            self.channel_offsets = {
                channel_id: {'offset': offset} 
                for channel_id, offset in channel_offsets.items()
            }
        self.default_offset = default_offset
        
        try:
            # Carregar XML
            tree = ET.parse(input_path)
            
            # Processar com o novo método
            processed_tree = self.adjust_times(tree)
            
            # Adicionar comentário com informações do processamento
            root = processed_tree.getroot()
            comment_text = f" Processado em {datetime.now().isoformat()} - {self.processed_programmes} programas ajustados "
            comment = ET.Comment(comment_text)
            root.insert(0, comment)
            
            # Salvar arquivo processado
            processed_tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"Processamento concluído: {len(self.processed_channels)} canais, {self.processed_programmes} programas")
            
        except Exception as e:
            error_msg = f"Erro no processamento XML: {e}"
            logger.error(error_msg)
            raise
    
    def create_compressed_output(self, xml_path: str, output_path: str):
        """
        Cria versão comprimida do arquivo XML
        """
        logger.info(f"Criando arquivo comprimido: {output_path}")
        
        try:
            with open(xml_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            
            logger.info("Arquivo comprimido criado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao criar arquivo comprimido: {e}")
            raise
    
    def get_processing_stats(self) -> dict:
        """
        Retorna estatísticas do processamento
        """
        return {
            "channels_processed": len(self.processed_channels),
            "programs_processed": self.processed_programmes,
            "errors_count": len(self.errors),
            "errors": self.errors
        }
