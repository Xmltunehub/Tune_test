#!/usr/bin/env python3
"""
EPG XML Processor - Script Principal
Interface de linha de comando para processar EPG XML com seleção de canais
"""

import argparse
import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Assumindo que as outras classes estão em src/
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from processor import ScheduleProcessor
    from utils import setup_logging, load_channel_offsets
except ImportError:
    print("❌ Erro: Módulos não encontrados. Certifique-se de que os arquivos em src/ existem.")
    sys.exit(1)

class EPGProcessor:
    def __init__(self, epg_url: str = "https://www.tdtchannels.com/epg/TV.xml"):
        self.epg_url = epg_url
        self.processor = ScheduleProcessor()
        self.logger = None
        
    def setup_logging(self, verbose: bool = False) -> None:
        """Configura o sistema de logging"""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('processing.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def list_channels(self) -> List[Dict[str, str]]:
        """Lista todos os canais disponíveis"""
        print("🔄 Obtendo lista de canais...")
        try:
            channels = self.processor.get_available_channels(self.epg_url)
            if not channels:
                print("❌ Nenhum canal encontrado no EPG!")
                return []
            
            print(f"\n📺 CANAIS DISPONÍVEIS ({len(channels)} total):")
            print("=" * 60)
            
            for i, channel in enumerate(channels, 1):
                print(f"{i:3d}. {channel['id']:<25} - {channel['name']}")
            
            print("=" * 60)
            return channels
            
        except Exception as e:
            print(f"❌ Erro ao listar canais: {e}")
            return []
    
    def find_channel(self, search_term: str, channels: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Busca inteligente de canal"""
        if not channels:
            return None
            
        search_lower = search_term.lower()
        
        # 1. Busca exata por ID
        for channel in channels:
            if channel['id'].lower() == search_lower:
                return channel
        
        # 2. Busca exata por nome
        for channel in channels:
            if channel['name'].lower() == search_lower:
                return channel
        
        # 3. Busca parcial por ID
        for channel in channels:
            if search_lower in channel['id'].lower():
                return channel
        
        # 4. Busca parcial por nome
        for channel in channels:
            if search_lower in channel['name'].lower():
                return channel
        
        return None
    
    def suggest_channels(self, search_term: str, channels: List[Dict[str, str]], limit: int = 5) -> List[Dict[str, str]]:
        """Sugere canais similares"""
        if not channels:
            return []
            
        search_lower = search_term.lower()
        suggestions = []
        
        # Buscar por similaridade
        for channel in channels:
            score = 0
            
            # Pontuação por ID
            if search_lower in channel['id'].lower():
                score += 10
            
            # Pontuação por nome
            if search_lower in channel['name'].lower():
                score += 5
            
            # Pontuação por início
            if channel['id'].lower().startswith(search_lower):
                score += 15
            if channel['name'].lower().startswith(search_lower):
                score += 8
            
            if score > 0:
                suggestions.append((channel, score))
        
        # Ordenar por pontuação e retornar top N
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in suggestions[:limit]]
    
    def show_stats(self) -> None:
        """Mostra estatísticas detalhadas"""
        print("📊 Obtendo estatísticas do EPG...")
        try:
            channels = self.processor.get_available_channels(self.epg_url)
            if not channels:
                print("❌ Nenhum canal encontrado!")
                return
            
            # Estatísticas básicas
            print(f"\n📈 ESTATÍSTICAS DO EPG:")
            print("=" * 50)
            print(f"🔢 Total de canais: {len(channels)}")
            print(f"🌐 Fonte: {self.epg_url}")
            print(f"⏰ Atualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Análise por prefixos
            prefixes = {}
            for channel in channels:
                prefix = channel['id'].split('_')[0] if '_' in channel['id'] else channel['id'][:3]
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
            
            print(f"\n🏷️  TOP 10 PREFIXOS:")
            for prefix, count in sorted(prefixes.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   {prefix:<10}: {count:3d} canais")
            
            # Verificar offsets configurados
            try:
                offsets = load_channel_offsets()
                if offsets:
                    print(f"\n⚙️  OFFSETS CONFIGURADOS:")
                    for channel_id, config in offsets.items():
                        offset_hours = config.get('offset', 0) / 3600
                        print(f"   {channel_id:<20}: {offset_hours:+.1f}h")
            except:
                pass
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Erro ao obter estatísticas: {e}")
    
    def validate_channel(self, channel_id: str) -> bool:
        """Valida se um canal existe"""
        try:
            channels = self.processor.get_available_channels(self.epg_url)
            found = self.find_channel(channel_id, channels)
            
            if found:
                print(f"✅ Canal encontrado: {found['id']} - {found['name']}")
                return True
            else:
                print(f"❌ Canal '{channel_id}' não encontrado!")
                suggestions = self.suggest_channels(channel_id, channels)
                if suggestions:
                    print("\n💡 Sugestões:")
                    for suggestion in suggestions:
                        print(f"   • {suggestion['id']} - {suggestion['name']}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao validar canal: {e}")
            return False
    
    def process_channel(self, channel_id: str, offset: Optional[int] = None, force_download: bool = False) -> bool:
        """Processa um canal específico"""
        try:
            print(f"🎯 Processando canal: {channel_id}")
            
            # Validar canal primeiro
            channels = self.processor.get_available_channels(self.epg_url)
            channel = self.find_channel(channel_id, channels)
            
            if not channel:
                print(f"❌ Canal '{channel_id}' não encontrado!")
                suggestions = self.suggest_channels(channel_id, channels)
                if suggestions:
                    print("\n💡 Sugestões:")
                    for suggestion in suggestions:
                        print(f"   • {suggestion['id']} - {suggestion['name']}")
                return False
            
            print(f"✅ Canal encontrado: {channel['id']} - {channel['name']}")
            
            # Processar
            result = self.processor.process_single_channel(
                channel['id'], 
                self.epg_url, 
                offset=offset, 
                force_download=force_download
            )
            
            if result:
                print(f"✅ Canal {channel['id']} processado com sucesso!")
                return True
            else:
                print(f"❌ Erro ao processar canal {channel['id']}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao processar canal: {e}")
            self.logger.error(f"Erro ao processar canal {channel_id}: {e}")
            return False
    
    def process_all_channels(self, offset: Optional[int] = None, force_download: bool = False) -> bool:
        """Processa todos os canais"""
        try:
            print("🚀 Processando todos os canais...")
            
            result = self.processor.process_all_channels(
                self.epg_url, 
                offset=offset, 
                force_download=force_download
            )
            
            if result:
                print("✅ Todos os canais processados com sucesso!")
                return True
            else:
                print("❌ Erro ao processar canais")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao processar canais: {e}")
            self.logger.error(f"Erro ao processar todos os canais: {e}")
            return False

def create_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos"""
    parser = argparse.ArgumentParser(
        description="EPG XML Processor - Processamento de EPG com seleção de canais",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python run.py                           # Processar todos os canais
  python run.py --channel "RTP1"          # Processar canal específico
  python run.py --channel "sport" --offset -3600  # Canal com offset
  python run.py --list-channels            # Listar canais disponíveis
  python run.py --stats                    # Mostrar estatísticas
  python run.py --validate "SIC"          # Validar se canal existe
        """
    )
    
    # Argumentos principais
    parser.add_argument(
        '--channel', '-c',
        help='Canal específico para processar (ID ou nome parcial)'
    )
    
    parser.add_argument(
        '--offset', '-o',
        type=int,
        help='Offset em segundos para ajuste de tempo'
    )
    
    parser.add_argument(
        '--force-download', '-f',
        action='store_true',
        help='Forçar download do XML mesmo se já existir'
    )
    
    # Comandos informativos
    parser.add_argument(
        '--list-channels', '-l',
        action='store_true',
        help='Listar todos os canais disponíveis'
    )
    
    parser.add_argument(
        '--stats', '-s',
        action='store_true',
        help='Mostrar estatísticas detalhadas'
    )
    
    parser.add_argument(
        '--validate', '-v',
        help='Validar se um canal específico existe'
    )
    
    # Opções gerais
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Modo verbose (mais detalhes no log)'
    )
    
    parser.add_argument(
        '--epg-url',
        default="https://www.tdtchannels.com/epg/TV.xml",
        help='URL do EPG XML (padrão: tdtchannels.com)'
    )
    
    return parser

def main():
    """Função principal"""
    print("🎬 EPG XML Processor")
    print("=" * 30)
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Criar processador
    processor = EPGProcessor(args.epg_url)
    processor.setup_logging(args.verbose)
    
    try:
        # Comandos informativos
        if args.list_channels:
            processor.list_channels()
            return
        
        if args.stats:
            processor.show_stats()
            return
        
        if args.validate:
            processor.validate_channel(args.validate)
            return
        
        # Processamento
        if args.channel:
            success = processor.process_channel(
                args.channel,
                offset=args.offset,
                force_download=args.force_download
            )
        else:
            success = processor.process_all_channels(
                offset=args.offset,
                force_download=args.force_download
            )
        
        if success:
            print("\n🎉 Processamento concluído com sucesso!")
            sys.exit(0)
        else:
            print("\n❌ Processamento falhou!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Processamento interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
