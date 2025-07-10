# ADICIONAR este método à sua classe ScheduleProcessor existente

def process_single_channel(self, channel_id: str):
    """Processa apenas um canal específico"""
    logger.info(f"Processando canal específico: {channel_id}")
    
    try:
        # Carregar XML source
        tree = ET.parse(self.source_xml_path)
        root = tree.getroot()
        
        # Encontrar programas do canal
        programmes = root.findall(f".//programme[@channel='{channel_id}']")
        
        if not programmes:
            logger.warning(f"Nenhum programa encontrado para canal: {channel_id}")
            return
        
        # Obter offset para o canal
        channel_config = self.config['channels'].get(channel_id, {})
        offset = channel_config.get('offset', self.config['default_offset'])
        
        logger.info(f"Aplicando offset de {offset}s para {len(programmes)} programas")
        
        # Criar ajustador
        adjuster = XmlTimeAdjuster(
            channel_offsets=self.config['channels'],
            default_offset=self.config['default_offset']
        )
        
        # Processar apenas este canal
        adjusted_tree = adjuster.adjust_times(tree, specific_channel=channel_id)
        
        # Salvar resultado
        output_path = f"data/processed/epg_{channel_id}_adjusted.xml"
        adjusted_tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        # Atualizar estatísticas
        self.stats['processed_channels'] = 1
        self.stats['processed_programmes'] = len(programmes)
        self.stats['channels_processed'].append({
            'channel_id': channel_id,
            'programmes_count': len(programmes),
            'offset_applied': offset
        })
        
        logger.info(f"Canal {channel_id} processado. Arquivo salvo: {output_path}")
        
    except Exception as e:
        logger.error(f"Erro no processamento do canal {channel_id}: {e}")
        self.stats['errors_count'] += 1
        raise
