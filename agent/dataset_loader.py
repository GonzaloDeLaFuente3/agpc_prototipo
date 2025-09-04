# agent/dataset_loader.py
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from agent.fragmentador import fragmentar_conversacion

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
    
    def generar_dataset_ejemplo(self, nombre_dominio: str = "ejemplo_reuniones") -> Dict:
        """Genera un dataset de ejemplo para testing."""
        return {
            "dominio": nombre_dominio,
            "metadata": {
                "descripcion": "Dataset de ejemplo con reuniones de equipo",
                "fecha_creacion": datetime.now().isoformat(),
                "autor": "Sistema AGPC",
                "version": "1.0",
                "tags": ["ejemplo", "reuniones", "testing"]
            },
            "conversaciones": [
                {
                    "titulo": "Reunión Semanal de Producto - Sprint 23",
                    "contenido": """Juan: Buenos días equipo, empezamos la retrospectiva del Sprint 23.
                    
María: Hola Juan. Esta semana completé la implementación del login social. Todo está funcionando correctamente con Google y Facebook.

Pedro: Perfecto María. Por mi parte, tuve algunos problemas con la optimización de la base de datos. Las consultas siguen siendo lentas.

Juan: ¿Qué propones Pedro?

Pedro: Creo que necesitamos implementar indexación en las tablas principales y revisar las queries más complejas. Estimo que me tomará 2 días.

Ana: Yo terminé el diseño de la nueva landing page. Ya está lista para implementación. ¿Pedro, podrías ayudarme con la integración la próxima semana?

Pedro: Claro Ana, sin problema.

---

DECISIONES TOMADAS:
1. María continúa con testing del login social
2. Pedro se enfoca en optimización DB (2 días)
3. Ana e integration de landing page para la próxima semana
4. Próxima reunión: jueves 15:00""",
                    "fecha": "2025-01-22T09:00:00",
                    "participantes": ["Juan", "María", "Pedro", "Ana"],
                    "metadata": {
                        "tipo": "reunion",
                        "duracion": "45min",
                        "proyecto": "Plataforma Web",
                        "prioridad": "alta"
                    }
                },
                {
                    "titulo": "Brainstorm - Nuevas Funcionalidades Q2",
                    "contenido": """Facilitador: Bienvenidos al brainstorm de funcionalidades para Q2. Tenemos 1 hora para generar ideas.

Participante1: Propongo implementar un sistema de notificaciones push más inteligente, que aprenda de los hábitos del usuario.

Participante2: Me gusta esa idea. También creo que necesitamos un dashboard más personalizable, donde cada usuario pueda organizar sus widgets.

Participante3: ¿Qué tal si agregamos integración con herramientas de productividad como Slack y Trello?

Facilitador: Excelentes ideas. ¿Alguien más?

Participante1: También podríamos implementar un modo offline más robusto.

Participante2: Sí, y quizás un sistema de colaboración en tiempo real como Google Docs.

---

IDEAS PRIORIZADAS:
1. Notificaciones inteligentes (MVP)
2. Dashboard personalizable (MVP)  
3. Integración Slack/Trello (Nice to have)
4. Modo offline mejorado (Technical debt)
5. Colaboración tiempo real (Future)""",
                    "fecha": "2025-01-20T14:00:00",
                    "participantes": ["Facilitador", "Participante1", "Participante2", "Participante3"],
                    "metadata": {
                        "tipo": "brainstorm",
                        "duracion": "60min",
                        "proyecto": "Plataforma Web",
                        "prioridad": "media"
                    }
                },
                {
                    "titulo": "Entrevista Técnica - Desarrollador Senior",
                    "contenido": """Entrevistador: Hola, gracias por venir. Soy el Lead Developer del equipo. ¿Podrías contarme sobre tu experiencia con React?

Candidato: Hola, gracias. Tengo 4 años de experiencia con React. He trabajado principalmente con hooks, Redux para estado global, y recientemente con Next.js para SSR.

Entrevistador: Perfecto. ¿Cómo manejarías el estado en una aplicación compleja?

Candidato: Depende del caso. Para estado local uso useState o useReducer. Para estado global, prefiero Redux Toolkit con RTK Query para las API calls. También he usado Zustand para casos más simples.

Entrevistador: Interesante. ¿Qué opinas sobre la optimización de performance?

Candidato: Es crucial. Uso React.memo para componentes que no cambian frecuentemente, useMemo y useCallback para evitar re-renders innecesarios. También implemento lazy loading para componentes pesados.

Entrevistador: Muy bien. ¿Tienes preguntas sobre el puesto?

Candidato: Sí, ¿qué stack tecnológico usan actualmente? ¿Y cómo manejan el deployment?""",
                    "fecha": "2025-01-18T10:30:00",
                    "participantes": ["Entrevistador", "Candidato"],
                    "metadata": {
                        "tipo": "entrevista",
                        "duracion": "45min", 
                        "proyecto": "Recruitment",
                        "prioridad": "alta"
                    }
                }
            ]
        }

# Función de utilidad para testing
def test_dataset_loader():
    """Prueba el cargador de datasets."""
    loader = DatasetLoader()
    
    # Generar dataset de ejemplo
    dataset_ejemplo = loader.generar_dataset_ejemplo("testing_masivo")
    
    print("🧪 Testing Dataset Loader")
    print(f"📊 Dataset generado: {dataset_ejemplo['dominio']}")
    print(f"💬 Conversaciones: {len(dataset_ejemplo['conversaciones'])}")
    
    # Validar formato
    es_valido, errores = loader.validar_formato(dataset_ejemplo)
    print(f"✅ Formato válido: {es_valido}")
    
    if errores:
        print("❌ Errores encontrados:")
        for error in errores:
            print(f"  - {error}")
    
    # Guardar ejemplo para testing manual
    import os
    os.makedirs("data/datasets", exist_ok=True)
    
    with open("data/datasets/ejemplo_reuniones.json", 'w', encoding='utf-8') as f:
        import json
        json.dump(dataset_ejemplo, f, ensure_ascii=False, indent=2)
    
    print("💾 Dataset de ejemplo guardado en: data/datasets/ejemplo_reuniones.json")
    
    return dataset_ejemplo

if __name__ == "__main__":
    test_dataset_loader()