# agent/dataset_loader.py
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class DatasetLoader:
    """Cargador de datasets JSON para testing y demos masivos."""
    
    FORMATO_ESPERADO = {
        "dominio": "nombre_del_dominio",
        "metadata": {
            "descripcion": "Descripción del dataset",
            "fecha_creacion": "ISO timestamp", 
            "autor": "Autor del dataset",
            "version": "1.0",
            "tags": ["tag1", "tag2"]
        },
        "conversaciones": [
            {
                "titulo": "Nombre conversación",
                "contenido": "Texto completo...",
                "fecha": "ISO timestamp",
                "participantes": ["lista"],
                "metadata": {
                    "tipo": "reunion|entrevista|brainstorm|planning|general",
                    "duracion": "30min",
                    "proyecto": "Nombre proyecto",
                    "prioridad": "alta|media|baja"
                }
            }
        ]
    }
    
    def __init__(self):
        self.estadisticas = {
            'conversaciones_procesadas': 0,
            'fragmentos_generados': 0,
            'errores': [],
            'tiempo_inicio': None,
            'tiempo_fin': None
        }
    
    def validar_formato(self, dataset: Dict) -> Tuple[bool, List[str]]:
        """Valida que el dataset tenga el formato correcto."""
        errores = []
        
        # Validar campos obligatorios del dataset
        if 'dominio' not in dataset:
            errores.append("Falta campo obligatorio: 'dominio'")
        
        if 'conversaciones' not in dataset:
            errores.append("Falta campo obligatorio: 'conversaciones'")
        elif not isinstance(dataset['conversaciones'], list):
            errores.append("El campo 'conversaciones' debe ser una lista")
        elif len(dataset['conversaciones']) == 0:
            errores.append("La lista de conversaciones está vacía")
        
        # Validar cada conversación
        for i, conv in enumerate(dataset.get('conversaciones', [])):
            if not isinstance(conv, dict):
                errores.append(f"Conversación {i+1}: debe ser un objeto")
                continue
            
            if 'titulo' not in conv:
                errores.append(f"Conversación {i+1}: falta campo 'titulo'")
            
            if 'contenido' not in conv:
                errores.append(f"Conversación {i+1}: falta campo 'contenido'")
            elif not conv['contenido'].strip():
                errores.append(f"Conversación {i+1}: contenido vacío")
            
            # Validar formato de fecha si existe
            if 'fecha' in conv and conv['fecha']:
                try:
                    datetime.fromisoformat(conv['fecha'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    errores.append(f"Conversación {i+1}: formato de fecha inválido (usar ISO 8601)")
            
            # Validar participantes
            if 'participantes' in conv and not isinstance(conv['participantes'], list):
                errores.append(f"Conversación {i+1}: 'participantes' debe ser una lista")
        
        return len(errores) == 0, errores
    
    def procesar_dataset(self, dataset: Dict, sobrescribir: bool = False) -> Dict:
        """
        Procesa un dataset completo y carga todas las conversaciones.
        
        Args:
            dataset: Diccionario con el formato esperado
            sobrescribir: Si True, permite sobreescribir datos existentes
            
        Returns:
            Estadísticas del procesamiento
        """
        self.estadisticas = {
            'conversaciones_procesadas': 0,
            'fragmentos_generados': 0,
            'errores': [],
            'tiempo_inicio': datetime.now(),
            'tiempo_fin': None,
            'dominio': dataset.get('dominio', 'desconocido'),
            'conversaciones_fallidas': []
        }
        
        # Validar formato
        es_valido, errores_validacion = self.validar_formato(dataset)
        if not es_valido:
            self.estadisticas['errores'].extend(errores_validacion)
            self.estadisticas['tiempo_fin'] = datetime.now()
            return self.estadisticas
        
        print(f"Iniciando carga masiva del dominio: {dataset['dominio']}")
        print(f"Conversaciones a procesar: {len(dataset['conversaciones'])}")
        
        # Procesar cada conversación
        from agent.grafo import agregar_conversacion
        
        for i, conversacion_data in enumerate(dataset['conversaciones'], 1):
            try:
                print(f"Procesando {i}/{len(dataset['conversaciones'])}: {conversacion_data['titulo'][:50]}...")
                
                # Preparar metadatos enriquecidos
                metadata = conversacion_data.get('metadata', {}).copy()
                metadata.update({
                    'dominio': dataset['dominio'],
                    'dataset_metadata': dataset.get('metadata', {}),
                    'posicion_en_dataset': i,
                    'cargado_masivamente': True
                })
                
                # Agregar conversación usando el sistema existente
                resultado = agregar_conversacion(
                    titulo=conversacion_data['titulo'],
                    contenido=conversacion_data['contenido'],
                    fecha=conversacion_data.get('fecha'),
                    participantes=conversacion_data.get('participantes', []),
                    metadata=metadata
                )
                
                self.estadisticas['conversaciones_procesadas'] += 1
                self.estadisticas['fragmentos_generados'] += resultado['total_fragmentos']
                
                if i % 5 == 0:  # Progress cada 5 conversaciones
                    print(f"    ✅ Progreso: {i}/{len(dataset['conversaciones'])} conversaciones procesadas")
                
            except Exception as e:
                error_msg = f"Error procesando conversación {i} '{conversacion_data.get('titulo', 'Sin título')}': {str(e)}"
                print(f"    ❌ {error_msg}")
                self.estadisticas['errores'].append(error_msg)
                self.estadisticas['conversaciones_fallidas'].append({
                    'posicion': i,
                    'titulo': conversacion_data.get('titulo', 'Sin título'),
                    'error': str(e)
                })
        
        self.estadisticas['tiempo_fin'] = datetime.now()
        duracion = (self.estadisticas['tiempo_fin'] - self.estadisticas['tiempo_inicio']).total_seconds()
        
        print(f"\nCarga masiva completada:")
        print(f"Conversaciones procesadas: {self.estadisticas['conversaciones_procesadas']}")
        print(f"Fragmentos generados: {self.estadisticas['fragmentos_generados']}")
        print(f"Errores: {len(self.estadisticas['errores'])}")
        print(f"Tiempo total: {duracion:.2f} segundos")
        
        if self.estadisticas['errores']:
            print(f"Errores encontrados:")
            for error in self.estadisticas['errores'][:3]:  # Mostrar primeros 3
                print(f"- {error}")
            if len(self.estadisticas['errores']) > 3:
                print(f"... y {len(self.estadisticas['errores'])-3} errores más")
        
        return self.estadisticas
    
    def cargar_desde_archivo(self, ruta_archivo: str, sobrescribir: bool = False) -> Dict:
        """Carga un dataset desde archivo JSON."""
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
            
            return self.procesar_dataset(dataset, sobrescribir)
            
        except FileNotFoundError:
            return {
                'errores': [f"Archivo no encontrado: {ruta_archivo}"],
                'conversaciones_procesadas': 0,
                'fragmentos_generados': 0
            }
        except json.JSONDecodeError as e:
            return {
                'errores': [f"Error parseando JSON: {str(e)}"],
                'conversaciones_procesadas': 0,
                'fragmentos_generados': 0
            }
        except Exception as e:
            return {
                'errores': [f"Error inesperado: {str(e)}"],
                'conversaciones_procesadas': 0,
                'fragmentos_generados': 0
            }