import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import gzip
import os

logger = logging.getLogger(__name__)

class XmlTimeAdjuster:
    def __init__(self):
        self.channels_processed = 0
        self.programs_processed = 0
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
    
    def adjust_program_times(self, program: ET.Element, offset_seconds: int):
        """
        Ajusta horários de um programa específico
        """
        try:
            # Ajustar horário de início
            start_attr = program.get('start')
            if start_attr:
                start_dt = self.parse_datetime(start_attr)
                if start_dt:
                    new_start = start_dt + timedelta(seconds=offset_seconds)
                    program.set('start', self.format_datetime(new_start))
            
            # Ajustar horário de fim
            stop_attr = program.get('stop')
            if stop_attr:
                stop_dt = self.parse_datetime(stop_attr)
                if stop_dt:
                    new_stop = stop_dt + timedelta(seconds=offset_seconds)
                    program.set('stop', self.format_datetime(new_stop))
            
            self.programs_processed += 1
            
        except Exception as e:
            error_msg = f"Erro ao ajustar programa: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
    
    def process_xml(self, input_path: str, output_path: str, channel_offsets: Dict[str, int], default_offset: int = 30):
        """
        Processa o arquivo XML aplicando ajustes de tempo
        
        Args:
            input_path: Caminho do arquivo XML de entrada
            output_path: Caminho do arquivo XML de saída
            channel_offsets: Dicionário com ajustes por canal
            default_offset: Ajuste padrão em segundos
        """
        logger.info(f"Iniciando processamento: {input_path}")
        
        try:
            # Carregar XML
            tree = ET.parse(input_path)
            root = tree.getroot()
            
            # Processar cada canal
            for channel in root.findall('channel'):
                channel_id = channel.get('id', 'unknown')
                
                # Determinar offset para este canal
                offset = channel_offsets.get(channel_id, default_offset)
                
                logger.debug(f"Processando canal {channel_id} com offset {offset}s")
                
                # Processar programas do canal
                programs = root.findall(f"programme[@channel='{channel_id}']")
                for program in programs:
                    self.adjust_program_times(program, offset)
                
                self.channels_processed += 1
            
            # Adicionar comentário com informações do processamento
            comment_text = f" Processado em {datetime.now().isoformat()} - {self.programs_processed} programas ajustados "
            comment = ET.Comment(comment_text)
            root.insert(0, comment)
            
            # Salvar arquivo processado
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"Processamento concluído: {self.channels_processed} canais, {self.programs_processed} programas")
            
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
            "channels_processed": self.channels_processed,
            "programs_processed": self.programs_processed,
            "errors_count": len(self.errors),
            "errors": self.errors
        }
