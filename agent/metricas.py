# agent/metricas.py
import time
from datetime import datetime
from typing import Dict, List
import json
import os

# Archivo para almacenar historial
ARCHIVO_METRICAS = "data/metricas_performance.json"

class MetricasPerformance:
    """Registra y gestiona métricas de performance del sistema"""
    
    def __init__(self):
        self.historial = self._cargar_historial()
    
    def _cargar_historial(self) -> List[Dict]:
        """Carga historial de métricas desde disco"""
        if os.path.exists(ARCHIVO_METRICAS):
            try:
                with open(ARCHIVO_METRICAS, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _guardar_historial(self):
        """Guarda historial en disco"""
        os.makedirs("data", exist_ok=True)
        with open(ARCHIVO_METRICAS, 'w', encoding='utf-8') as f:
            json.dump(self.historial, f, ensure_ascii=False, indent=2)
    
    def registrar_carga_dataset(self, tipo: str, cantidad: int, tiempo_ms: float, detalles: Dict = None):
        """
        Registra métricas de carga de dataset
            tipo: 'conversaciones' o 'pdf'
            cantidad: número de items cargados
            tiempo_ms: duración en milisegundos
        """
        metrica = {
            "tipo_operacion": "carga_dataset",
            "tipo_dataset": tipo,
            "cantidad_items": cantidad,
            "tiempo_ms": round(tiempo_ms, 2),
            "tiempo_segundos": round(tiempo_ms / 1000, 2),
            "timestamp": datetime.now().isoformat(),
            "detalles": detalles or {}
        }
        
        self.historial.append(metrica)
        self._guardar_historial()
        
        return metrica
    
    def registrar_consulta(self, pregunta: str, tiempo_ms: float, 
                          contextos_utilizados: int, usa_propagacion: bool):
        """
        Registra métricas de consulta del usuario
            pregunta: texto de la consulta
            tiempo_ms: duración total de procesamiento
            contextos_utilizados: número de contextos recuperados
            usa_propagacion: si se usó propagación
        """
        metrica = {
            "tipo_operacion": "consulta",
            "pregunta_length": len(pregunta),
            "tiempo_ms": round(tiempo_ms, 2),
            "tiempo_segundos": round(tiempo_ms / 1000, 2),
            "contextos_utilizados": contextos_utilizados,
            "usa_propagacion": usa_propagacion,
            "timestamp": datetime.now().isoformat()
        }
        
        self.historial.append(metrica)
        self._guardar_historial()
        
        return metrica
    
    def obtener_estadisticas(self) -> Dict:
        """Calcula estadísticas agregadas de performance"""
        if not self.historial:
            return {
                "total_operaciones": 0,
                "mensaje": "No hay métricas registradas"
            }
        
        # Separar por tipo
        cargas = [m for m in self.historial if m["tipo_operacion"] == "carga_dataset"]
        consultas = [m for m in self.historial if m["tipo_operacion"] == "consulta"]
        
        stats = {
            "total_operaciones": len(self.historial),
            "cargas_dataset": {
                "total": len(cargas),
                "tiempo_promedio_ms": round(sum(c["tiempo_ms"] for c in cargas) / len(cargas), 2) if cargas else 0,
                "tiempo_total_segundos": round(sum(c["tiempo_ms"] for c in cargas) / 1000, 2) if cargas else 0
            },
            "consultas": {
                "total": len(consultas),
                "tiempo_promedio_ms": round(sum(c["tiempo_ms"] for c in consultas) / len(consultas), 2) if consultas else 0,
                "tiempo_min_ms": min((c["tiempo_ms"] for c in consultas), default=0),
                "tiempo_max_ms": max((c["tiempo_ms"] for c in consultas), default=0),
                "contextos_promedio": round(sum(c["contextos_utilizados"] for c in consultas) / len(consultas), 2) if consultas else 0
            }
        }
        
        return stats

# Instancia global
metricas_sistema = MetricasPerformance()