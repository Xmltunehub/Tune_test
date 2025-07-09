import unittest
import os
import sys
import tempfile
import json
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from xml_handler import XmlTimeAdjuster
from utils import validate_config, format_duration

class TestXmlTimeAdjuster(unittest.TestCase):
    def setUp(self):
        self.adjuster = XmlTimeAdjuster()
    
    def test_parse_datetime(self):
        """Teste parsing de data/hora"""
        # Formato padrão
        result = self.adjuster.parse_datetime("20250101120000")
        expected = datetime(2025, 1, 1, 12, 0, 0)
        self.assertEqual(result, expected)
        
        # Com timezone
        result = self.adjuster.parse_datetime("20250101120000 +0100")
        expected = datetime(2025, 1, 1, 12, 0, 0)
        self.assertEqual(result, expected)
    
    def test_format_datetime(self):
        """Teste formatação de data/hora"""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = self.adjuster.format_datetime(dt)
        expected = "20250101120000 +0000"
        self.assertEqual(result, expected)

class TestConfigValidation(unittest.TestCase):
    def test_valid_config(self):
        """Teste configuração válida"""
        config = {
            "default_offset": 30,
            "channels": {
                "test.pt": {
                    "offset": 45,
                    "description": "Test channel"
                }
            }
        }
        self.assertTrue(validate_config(config))
    
    def test_invalid_config_missing_key(self):
        """Teste configuração inválida - chave ausente"""
        config = {
            "channels": {
                "test.pt": {
                    "offset": 45
                }
            }
        }
        self.assertFalse(validate_config(config))
    
    def test_invalid_config_wrong_type(self):
        """Teste configuração inválida - tipo incorreto"""
        config = {
            "default_offset": "30",  # String em vez de int
            "channels": {
                "test.pt": {
                    "offset": 45
                }
            }
        }
        self.assertFalse(validate_config(config))

class TestUtils(unittest.TestCase):
    def test_format_duration(self):
        """Teste formatação de duração"""
        self.assertEqual(format_duration(0), "0s")
        self.assertEqual(format_duration(30), "30s")
        self.assertEqual(format_duration(60), "1m")
        self.assertEqual(format_duration(90), "1m 30s")
        self.assertEqual(format_duration(3600), "1h")
        self.assertEqual(format_duration(3690), "1h 1m 30s")

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
    <channel id="test.pt">
        <display-name>Test Channel</display-name>
    </channel>
    <programme start="20250101120000 +0000" stop="20250101130000 +0000" channel="test.pt">
        <title>Test Program</title>
    </programme>
</tv>"""
    
    def test_xml_processing(self):
        """Teste processamento completo de XML"""
        # Criar arquivo XML temporário
        input_path = os.path.join(self.temp_dir, "input.xml")
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(self.sample_xml)
        
        # Processar
        adjuster = XmlTimeAdjuster()
        output_path = os.path.join(self.temp_dir, "output.xml")
        
        channel_offsets = {"test.pt": 30}
        adjuster.process_xml(input_path, output_path, channel_offsets, 0)
        
        # Verificar resultado
        self.assertTrue(os.path.exists(output_path))
        
        # Verificar conteúdo
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Deve conter horário ajustado
            self.assertIn("20250101120030", content)
            self.assertIn("20250101130030", content)
        
        # Verificar estatísticas
        stats = adjuster.get_processing_stats()
        self.assertEqual(stats['programs_processed'], 1)
        self.assertEqual(stats['channels_processed'], 1)

if __name__ == '__main__':
    unittest.main()
