# agent/dataset_loader.py
import re
from typing import Dict, List

class TextBatchProcessor:
    """Procesa texto plano o JSON con conversaciones"""
    
    def parse_texto_plano(self, texto: str) -> List[Dict]:
        """
        Extrae conversaciones del formato:
        titulo1: ...
        contenido1: ...
        """
        conversaciones = []
        patron = r'titulo(\d+):\s*(.+?)\s*contenido\1:\s*(.+?)(?=titulo\d+:|$)'
        
        matches = re.finditer(patron, texto, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            titulo = match.group(2).strip()
            contenido = match.group(3).strip()
            
            if titulo and contenido:
                conversaciones.append({
                    'titulo': titulo,
                    'contenido': contenido,
                    'origen': 'texto_plano'
                })
        
        return conversaciones
    
    def parse_json_conversaciones(self, data: Dict) -> List[Dict]:
        """Procesa JSON con lista de conversaciones"""
        if 'conversaciones' in data:
            conversaciones_raw = data['conversaciones']
        elif isinstance(data, list):
            conversaciones_raw = data
        else:
            raise ValueError("JSON debe contener clave 'conversaciones' o ser un array")
        
        conversaciones = []
        for conv in conversaciones_raw:
            if 'titulo' not in conv or 'contenido' not in conv:
                raise ValueError("Cada conversación debe tener 'titulo' y 'contenido'")
            
            conversaciones.append({
                'titulo': conv['titulo'],
                'contenido': conv['contenido'],
                'fecha': conv.get('fecha'),
                'participantes': conv.get('participantes', []),
                'metadata': conv.get('metadata', {}),
                'origen': 'json'
            })
        
        return conversaciones
    
    def preparar_preview(self, conversaciones: List[Dict]) -> Dict:
        """Genera preview con estadísticas"""
        return {
            'total_conversaciones': len(conversaciones),
            'conversaciones': [
                {
                    'titulo': conv['titulo'],
                    'palabras_aproximadas': len(conv['contenido'].split()),
                    'lineas_aproximadas': len(conv['contenido'].split('\n')),
                    'tiene_fecha': bool(conv.get('fecha')),
                    'participantes': conv.get('participantes', []),
                    'origen': conv['origen']
                }
                for conv in conversaciones
            ]
        }