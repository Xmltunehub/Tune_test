import argparse
import sys
import logging
from src.processor import ScheduleProcessor
from src.utils import setup_logging, load_config, save_config, validate_config
from src.downloader import SourceDownloader

def main():
    parser = argparse.ArgumentParser(description='Processador de EPG com ajustes por canal')
    parser.add_argument('--offset', type=int, default=None, 
                       help='Offset padrão global em segundos')
    parser.add_argument('--channel', type=str, default=None,
                       help='Canal específico para ajustar')
    parser.add_argument('--channel-offset', type=int, default=None,
                       help='Offset específico para o canal (usado com --channel)')
    parser.add_argument('--save-config', action='store_true',
                       help='Salva ajustes na configuração permanente')
    parser.add_argument('--force-download', action='store_true',
                       help='Força download mesmo se não houver alterações')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--config', default='config/channel-offsets.json',
                       help='Caminho para arquivo de configuração')
    parser.add_argument('--source-url', 
                       default='https://raw.githubusercontent.com/LITUATUI/M3UPT/main/EPG/epg.xml.gz',
                       help='URL do arquivo EPG')
    
    args = parser.parse_args()
    
    # Configurar logging
    setup_logging(args.log_level, "logs/epg_processing.log")
    logger = logging.getLogger(__name__)
    
    try:
        # Carregar configuração
        config = load_config(args.config)
        
        # Validar configuração
        if not validate_config(config):
            logger.error("Configuração inválida")
            sys.exit(1)
        
        # Processar argumentos de linha de comando
        config_updated = False
        
        # Ajuste global via --offset
        if args.offset is not None:
            logger.info(f"Aplicando offset global: {args.offset}s")
            config['default_offset'] = args.offset
            config_updated = True
        
        # Ajuste específico de canal
        if args.channel and args.channel_offset is not None:
            logger.info(f"Aplicando offset para canal {args.channel}: {args.channel_offset}s")
            
            # Criar entrada do canal se não existir
            if args.channel not in config['channels']:
                config['channels'][args.channel] = {}
            
            # Atualizar offset do canal
            config['channels'][args.channel]['offset'] = args.channel_offset
            config['channels'][args.channel]['description'] = f"Ajuste personalizado via CLI"
            config_updated = True
        
        # Salvar configuração se solicitado ou se houve mudanças
        if (args.save_config or config_updated) and config_updated:
            save_config(config, args.config)
            logger.info("Configuração atualizada e salva")
        
        # Download e extração
        downloader = SourceDownloader(args.source_url)
        was_updated, xml_path = downloader.download_and_extract(args.force_download)
        
        if was_updated:
            logger.info("Arquivo EPG atualizado")
        else:
            logger.info("Usando arquivo EPG existente")
        
        # Processar EPG
        processor = ScheduleProcessor(
            config_path=args.config,
            source_xml_path=xml_path
        )
        
        # Executar processamento
        if args.channel:
            # Processamento específico para um canal
            logger.info(f"Processando apenas canal: {args.channel}")
            processor.process_single_channel(args.channel)
        else:
            # Processamento completo
            logger.info("Processando todos os canais")
            processor.process_all()
        
        logger.info("Processamento concluído com sucesso")
        
    except Exception as e:
        logger.error(f"Erro durante processamento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
