#!/usr/bin/env python3
"""
Gerador de workflow do GitHub Actions com dropdown de canais reais
"""

import requests
import xml.etree.ElementTree as ET
import os
import json
from datetime import datetime
from typing import List, Dict, Tuple

class WorkflowGenerator:
    def __init__(self, epg_url: str = "https://www.tdtchannels.com/epg/TV.xml"):
        self.epg_url = epg_url
        self.channels = []
        self.workflow_path = ".github/workflows/daily-process.yml"
        self.reference_file = "channels_reference.txt"
        
    def download_epg(self) -> str:
        """Baixa o EPG XML atual"""
        print("🔄 Baixando EPG XML...")
        try:
            response = requests.get(self.epg_url, timeout=30)
            response.raise_for_status()
            print("✅ EPG baixado com sucesso!")
            return response.text
        except requests.RequestException as e:
            print(f"❌ Erro ao baixar EPG: {e}")
            raise
    
    def extract_channels(self, xml_content: str) -> List[Dict[str, str]]:
        """Extrai todos os canais do XML"""
        print("🔍 Extraindo canais do XML...")
        try:
            root = ET.fromstring(xml_content)
            channels = []
            
            for channel in root.findall('.//channel'):
                channel_id = channel.get('id')
                display_name = channel.find('display-name')
                
                if channel_id and display_name is not None:
                    channels.append({
                        'id': channel_id,
                        'name': display_name.text.strip() if display_name.text else channel_id
                    })
            
            # Ordenar por nome para facilitar a busca
            channels.sort(key=lambda x: x['name'].lower())
            
            print(f"✅ {len(channels)} canais extraídos!")
            return channels
            
        except ET.ParseError as e:
            print(f"❌ Erro ao processar XML: {e}")
            raise
    
    def generate_workflow_content(self, channels: List[Dict[str, str]]) -> str:
        """Gera o conteúdo do workflow com dropdown de canais"""
        print("📝 Gerando workflow YAML...")
        
        # Criar as opções do dropdown
        channel_options = []
        for channel in channels:
            # Formato: "ID - Nome do Canal"
            option = f'        - "{channel["id"]} - {channel["name"]}"'
            channel_options.append(option)
        
        # Adicionar opção para processar todos os canais
        all_channels_option = '        - "TODOS - Processar todos os canais"'
        channel_options.insert(0, all_channels_option)
        
        workflow_content = f"""name: Daily XML Processing

on:
  schedule:
    # Executa diariamente às 02:00 UTC
    - cron: '0 2 * * *'
  
  workflow_dispatch:
    inputs:
      selected_channel:
        description: 'Canal específico para processar'
        required: true
        type: choice
        default: 'TODOS - Processar todos os canais'
        options:
{chr(10).join(channel_options)}
      
      custom_offset:
        description: 'Offset específico em segundos (opcional)'
        required: false
        type: string
        default: ''
      
      force_download:
        description: 'Forçar download do XML'
        required: false
        type: boolean
        default: false

jobs:
  process-xml:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests lxml
    
    - name: Parse channel selection
      id: parse_channel
      run: |
        SELECTED="${{{{ github.event.inputs.selected_channel || 'TODOS - Processar todos os canais' }}}}"
        
        echo "Selected input: $SELECTED"
        
        if [[ "$SELECTED" == "TODOS - Processar todos os canais" ]]; then
          echo "channel_id=" >> $GITHUB_OUTPUT
          echo "channel_name=TODOS" >> $GITHUB_OUTPUT
          echo "Processing all channels"
        else
          # Extrair ID do canal (formato: "ID - Nome do Canal")
          CHANNEL_ID=$(echo "$SELECTED" | cut -d' ' -f1)
          CHANNEL_NAME=$(echo "$SELECTED" | cut -d' ' -f3-)
          echo "channel_id=$CHANNEL_ID" >> $GITHUB_OUTPUT
          echo "channel_name=$CHANNEL_NAME" >> $GITHUB_OUTPUT
          echo "Processing channel: $CHANNEL_ID ($CHANNEL_NAME)"
        fi
    
    - name: Run XML processing
      run: |
        # Configurar argumentos baseados na seleção
        ARGS=""
        
        # Canal específico
        if [[ -n "${{{{ steps.parse_channel.outputs.channel_id }}}}" ]]; then
          ARGS="$ARGS --channel ${{{{ steps.parse_channel.outputs.channel_id }}}}"
        fi
        
        # Offset personalizado
        if [[ -n "${{{{ github.event.inputs.custom_offset }}}}" ]]; then
          ARGS="$ARGS --offset ${{{{ github.event.inputs.custom_offset }}}}"
        fi
        
        # Forçar download
        if [[ "${{{{ github.event.inputs.force_download }}}}" == "true" ]]; then
          ARGS="$ARGS --force-download"
        fi
        
        echo "Executando: python run.py $ARGS"
        python run.py $ARGS
    
    - name: Upload processed files
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: processed-xml-${{{{ github.run_number }}}}
        path: |
          output/
          *.xml
          *.log
        retention-days: 7
    
    - name: Show processing summary
      run: |
        echo "## 📊 Resumo do Processamento" >> $GITHUB_STEP_SUMMARY
        echo "- **Canal selecionado:** ${{{{ steps.parse_channel.outputs.channel_name || 'TODOS' }}}}" >> $GITHUB_STEP_SUMMARY
        echo "- **Timestamp:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')" >> $GITHUB_STEP_SUMMARY
        echo "- **Workflow:** ${{{{ github.workflow }}}}" >> $GITHUB_STEP_SUMMARY
        echo "- **Run ID:** ${{{{ github.run_number }}}}" >> $GITHUB_STEP_SUMMARY
        
        if [[ -f "processing.log" ]]; then
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "### 📝 Log de Processamento" >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          tail -20 processing.log >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
        fi

# Workflow gerado automaticamente em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Total de canais disponíveis: {len(channels)}
# Fonte: {self.epg_url}
"""
        
        return workflow_content
    
    def save_workflow(self, content: str) -> None:
        """Salva o workflow no arquivo"""
        print("💾 Salvando workflow...")
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(self.workflow_path), exist_ok=True)
        
        with open(self.workflow_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Workflow salvo em: {self.workflow_path}")
    
    def save_reference(self, channels: List[Dict[str, str]]) -> None:
        """Salva lista de referência dos canais"""
        print("📋 Salvando referência de canais...")
        
        with open(self.reference_file, 'w', encoding='utf-8') as f:
            f.write(f"# Canais Disponíveis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(channels)} canais\n")
            f.write(f"# Fonte: {self.epg_url}\n\n")
            
            for i, channel in enumerate(channels, 1):
                f.write(f"{i:3d}. {channel['id']:<20} - {channel['name']}\n")
        
        print(f"✅ Referência salva em: {self.reference_file}")
    
    def generate_stats(self, channels: List[Dict[str, str]]) -> Dict:
        """Gera estatísticas dos canais"""
        stats = {
            'total_channels': len(channels),
            'timestamp': datetime.now().isoformat(),
            'epg_source': self.epg_url,
            'channels_by_prefix': {},
            'top_prefixes': []
        }
        
        # Contar prefixos
        prefix_count = {}
        for channel in channels:
            prefix = channel['id'].split('_')[0] if '_' in channel['id'] else channel['id'][:3]
            prefix_count[prefix] = prefix_count.get(prefix, 0) + 1
        
        # Top 10 prefixos
        stats['top_prefixes'] = sorted(prefix_count.items(), key=lambda x: x[1], reverse=True)[:10]
        stats['channels_by_prefix'] = prefix_count
        
        return stats
    
    def generate(self) -> None:
        """Gera o workflow completo"""
        print("🚀 Iniciando geração do workflow...")
        print("=" * 50)
        
        try:
            # 1. Baixar EPG
            xml_content = self.download_epg()
            
            # 2. Extrair canais
            self.channels = self.extract_channels(xml_content)
            
            if not self.channels:
                print("❌ Nenhum canal encontrado no EPG!")
                return
            
            # 3. Gerar workflow
            workflow_content = self.generate_workflow_content(self.channels)
            
            # 4. Salvar arquivos
            self.save_workflow(workflow_content)
            self.save_reference(self.channels)
            
            # 5. Gerar estatísticas
            stats = self.generate_stats(self.channels)
            
            # 6. Resumo final
            print("\n" + "=" * 50)
            print("🎉 WORKFLOW GERADO COM SUCESSO!")
            print("=" * 50)
            print(f"📊 Total de canais: {stats['total_channels']}")
            print(f"📁 Workflow: {self.workflow_path}")
            print(f"📋 Referência: {self.reference_file}")
            print("\n🔥 TOP 5 PREFIXOS:")
            for prefix, count in stats['top_prefixes'][:5]:
                print(f"   {prefix}: {count} canais")
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Commit e push das alterações")
            print("2. Ir para Actions → Daily XML Processing")
            print("3. Clicar em 'Run workflow'")
            print("4. Selecionar canal no dropdown")
            print("5. Executar!")
            
        except Exception as e:
            print(f"❌ Erro durante geração: {e}")
            raise

def main():
    """Função principal"""
    generator = WorkflowGenerator()
    generator.generate()

if __name__ == "__main__":
    main()
