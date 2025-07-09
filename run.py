#!/usr/bin/env python3
"""
Script principal para processamento de horários XML
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    parser = argparse.ArgumentParser(description="Processador de Horários XML")
    parser.add_argument('--force', action='store_true', 
                       help='Força processamento mesmo sem alterações na fonte')
    parser.add_argument('--config', default='config/channel-offsets.json',
                       help='Caminho para arquivo de configuração')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Nível de log')
    parser.add_argument('--log-file', 
                       help='Arquivo de log (opcional)')
    parser.add_argument('--offset', type=int, default=30,
                       help='Offset padrão em segundos (padrão: 30)')
    
    args = parser.parse_args()
    
    try:
        # Criar diretórios necessários
        Path("logs").mkdir(exist_ok=True)
        Path("data/raw").mkdir(parents=True, exist_ok=True)
        Path("data/processed").mkdir(parents=True, exist_ok=True)
        Path("config").mkdir(exist_ok=True)
        
        # Configurar logging
        if not args.log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            args.log_file = f"logs/processing_{timestamp}.log"
        
        # Importar módulos após verificar diretórios
        from processor import ScheduleProcessor
        from utils import setup_logging
        
        setup_logging(args.log_level, args.log_file)
        logger = logging.getLogger(__name__)
        
        logger.info("=== Iniciando processamento de horários XML ===")
        logger.info(f"Configurações: force={args.force}, offset={args.offset}s")
        
        # Verificar se arquivo de config existe, criar se necessário
        config_path = Path(args.config)
        if not config_path.exists():
            logger.warning(f"Arquivo de configuração não encontrado: {config_path}")
            logger.info("Criando arquivo de configuração padrão...")
            
            # Criar configuração padrão
            import json
            default_config = {
                "default_offset": args.offset,
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
                    "compress_output": True
                }
            }
            
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Arquivo de configuração criado: {config_path}")
        
        # Criar e executar processador
        processor = ScheduleProcessor(config_path=args.config, default_offset=args.offset)
        success = processor.run(force_download=args.force)
        
        if success:
            logger.info("Processamento concluído com sucesso!")
            print("✅ Processamento concluído com sucesso!")
            
            # Verificar se arquivo foi gerado
            output_file = Path("adjusted_schedule.xml.gz")
            if output_file.exists():
                size = output_file.stat().st_size
                print(f"📁 Arquivo gerado: {output_file} ({size:,} bytes)")
                logger.info(f"Arquivo gerado: {output_file} ({size:,} bytes)")
            else:
                logger.warning("Arquivo de saída não encontrado")
                
            sys.exit(0)
        else:
            logger.info("Nenhum processamento necessário")
            print("ℹ️  Nenhum processamento necessário")
            sys.exit(0)
            
    except ImportError as e:
        error_msg = f"Erro ao importar módulos: {e}"
        print(f"❌ {error_msg}")
        if 'logger' in locals():
            logger.error(error_msg)
        sys.exit(1)
        
    except FileNotFoundError as e:
        error_msg = f"Arquivo não encontrado: {e}"
        print(f"❌ {error_msg}")
        if 'logger' in locals():
            logger.error(error_msg)
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"Erro no processamento: {e}"
        print(f"❌ {error_msg}")
        if 'logger' in locals():
            logger.error(error_msg, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
