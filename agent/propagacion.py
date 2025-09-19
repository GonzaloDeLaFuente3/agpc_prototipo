import networkx as nx
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict, deque
import math

class PropagadorActivacion:
    """
    Implementa propagación de activación para descubrir relaciones indirectas
    en el Grafo Contextual Probabilístico.
    Permite explorar caminos de múltiples saltos para encontrar contextos
    relacionados que no están directamente conectados.
    """
    
    def __init__(self, grafo: nx.DiGraph, metadatos_contextos: Dict):
        self.grafo = grafo
        self.metadatos_contextos = metadatos_contextos
        self.factor_decaimiento = 0.8  # Factor de decaimiento por salto
        self.umbral_activacion = 0.1   # Umbral mínimo de activación
        
    def propagar_desde_nodo(self, nodo_inicial: str, activacion_inicial: float = 1.0, 
                           max_pasos: int = 3, incluir_temporales: bool = True) -> Dict[str, float]:
        """
        Propaga activación desde un nodo inicial hacia nodos conectados.
        Args:
            nodo_inicial: ID del nodo desde donde propagar
            activacion_inicial: Nivel inicial de activación (0.0-1.0)
            max_pasos: Máximo número de saltos a explorar
            incluir_temporales: Si incluir conexiones temporales en la propagación
            
        Returns:
            Dict[nodo_id, activacion_final] para todos los nodos alcanzados
        """
        if nodo_inicial not in self.grafo:
            return {}
        
        # Inicializar activaciones
        activaciones = {nodo_inicial: activacion_inicial}
        activaciones_por_paso = [activaciones.copy()]
        
        # Propagación iterativa
        for paso in range(max_pasos):
            nuevas_activaciones = {}
            
            # Para cada nodo con activación en el paso anterior
            for nodo_origen, activacion_origen in activaciones.items():
                if activacion_origen < self.umbral_activacion:
                    continue
                
                # Explorar vecinos
                vecinos = self._obtener_vecinos_validos(nodo_origen, incluir_temporales)
                
                for nodo_vecino, peso_conexion in vecinos:
                    if nodo_vecino == nodo_inicial:  # Evitar loops al origen
                        continue
                    
                    # Calcular activación propagada
                    activacion_propagada = self._calcular_activacion_propagada(
                        activacion_origen, peso_conexion, paso
                    )
                    
                    # Acumular activación en el nodo vecino
                    if nodo_vecino in nuevas_activaciones:
                        nuevas_activaciones[nodo_vecino] = max(
                            nuevas_activaciones[nodo_vecino], 
                            activacion_propagada
                        )
                    else:
                        nuevas_activaciones[nodo_vecino] = activacion_propagada
            
            # Actualizar activaciones para siguiente paso
            activaciones.update({
                nodo: act for nodo, act in nuevas_activaciones.items()
                if act >= self.umbral_activacion
            })
            
            activaciones_por_paso.append(activaciones.copy())
            
            # Terminar si no hay más propagación
            if not nuevas_activaciones:
                break
        
        # Remover el nodo inicial del resultado
        resultado = activaciones.copy()
        resultado.pop(nodo_inicial, None)
        
        return resultado
    
    def propagar_desde_consulta(self, palabras_clave: List[str], texto_consulta: str,
                               nodos_iniciales: List[str] = None, 
                               max_pasos: int = 2) -> Dict[str, Dict]:
        """
        Propaga activación desde una consulta, usando múltiples nodos como fuentes.
        Args:
            palabras_clave: Palabras clave de la consulta
            texto_consulta: Texto completo de la consulta
            nodos_iniciales: Nodos específicos como fuentes (opcional)
            max_pasos: Pasos de propagación
        Returns:
            Dict con nodos alcanzados y su información de activación
        """
        # Si no se proporcionan nodos iniciales, usar búsqueda semántica
        if not nodos_iniciales:
            from agent.semantica import buscar_similares
            try:
                nodos_iniciales = buscar_similares(texto_consulta, k=5)
            except Exception:
                nodos_iniciales = []
        
        if not nodos_iniciales:
            return {}
        
        # Propagar desde cada nodo inicial
        todos_resultados = {}
        palabras_clave_set = set(palabra.lower() for palabra in palabras_clave)
        
        for nodo_inicial in nodos_iniciales:
            if nodo_inicial not in self.metadatos_contextos:
                continue
            
            # Calcular activación inicial basada en similitud con consulta
            activacion_inicial = self._calcular_activacion_inicial(
                nodo_inicial, palabras_clave_set, texto_consulta
            )
            
            if activacion_inicial < self.umbral_activacion:
                continue
            
            # Propagar desde este nodo
            resultados_nodo = self.propagar_desde_nodo(
                nodo_inicial, activacion_inicial, max_pasos
            )
            
            # Combinar resultados
            for nodo_id, activacion in resultados_nodo.items():
                if nodo_id in todos_resultados:
                    # Tomar la máxima activación
                    todos_resultados[nodo_id]['activacion'] = max(
                        todos_resultados[nodo_id]['activacion'], 
                        activacion
                    )
                    todos_resultados[nodo_id]['fuentes'].append(nodo_inicial)
                else:
                    todos_resultados[nodo_id] = {
                        'activacion': activacion,
                        'fuentes': [nodo_inicial],
                        'metadatos': self.metadatos_contextos.get(nodo_id, {})
                    }
        
        return todos_resultados
    
    def encontrar_caminos_indirectos(self, nodo_origen: str, nodo_destino: str,
                                   max_longitud: int = 3) -> List[List[str]]:
        """
        Encuentra todos los caminos indirectos entre dos nodos.
        Args:
            nodo_origen: Nodo de inicio
            nodo_destino: Nodo de destino
            max_longitud: Máxima longitud del camino
        Returns:
            Lista de caminos (cada camino es una lista de nodos)
        """
        if nodo_origen not in self.grafo or nodo_destino not in self.grafo:
            return []
        
        # Usar BFS para encontrar caminos
        caminos = []
        cola = deque([(nodo_origen, [nodo_origen])])
        visitados_por_camino = set()
        
        while cola:
            nodo_actual, camino_actual = cola.popleft()
            
            # Si llegamos al destino y no es directo
            if nodo_actual == nodo_destino and len(camino_actual) > 2:
                caminos.append(camino_actual)
                continue
            
            # Si el camino es muy largo, saltar
            if len(camino_actual) >= max_longitud:
                continue
            
            # Explorar vecinos
            for vecino in self.grafo.neighbors(nodo_actual):
                if vecino not in camino_actual:  # Evitar ciclos
                    nuevo_camino = camino_actual + [vecino]
                    camino_key = tuple(nuevo_camino)
                    
                    if camino_key not in visitados_por_camino:
                        visitados_por_camino.add(camino_key)
                        cola.append((vecino, nuevo_camino))
        
        return caminos
    
    def analizar_centralidad_propagacion(self, max_pasos: int = 2) -> Dict[str, float]:
        """
        Analiza qué nodos son más centrales usando propagación de activación.
        Returns:
            Dict[nodo_id, score_centralidad] ordenado por centralidad
        """
        scores_centralidad = {}
        
        for nodo in self.grafo.nodes():
            if nodo not in self.metadatos_contextos:
                continue
            
            # Propagar desde este nodo
            activaciones = self.propagar_desde_nodo(nodo, 1.0, max_pasos)
            
            # Score = suma de activaciones alcanzadas
            score = sum(activaciones.values())
            scores_centralidad[nodo] = score
        
        # Ordenar por score descendente
        return dict(sorted(scores_centralidad.items(), 
                          key=lambda x: x[1], reverse=True))
    
    def _obtener_vecinos_validos(self, nodo: str, incluir_temporales: bool = True) -> List[Tuple[str, float]]:
        """Obtiene vecinos válidos con sus pesos de conexión."""
        vecinos = []
        
        for vecino in self.grafo.neighbors(nodo):
            if nodo == vecino:  # Evitar auto-loops
                continue
            
            # Obtener datos de la arista
            datos_arista = self.grafo[nodo][vecino]
            peso_efectivo = datos_arista.get('peso_efectivo', 0)
            relevancia_temporal = datos_arista.get('relevancia_temporal', 0)
            
            # Filtrar conexiones temporales si no se desean
            if not incluir_temporales and relevancia_temporal > 0.1:
                continue
            
            # Solo incluir conexiones con peso mínimo
            if peso_efectivo >= self.umbral_activacion:
                vecinos.append((vecino, peso_efectivo))
        
        return vecinos
    
    def _calcular_activacion_propagada(self, activacion_origen: float, 
                                     peso_conexion: float, paso: int) -> float:
        """Calcula la activación que se propaga a través de una conexión."""
        # Decaimiento por distancia
        factor_distancia = self.factor_decaimiento ** paso
        
        # Activación propagada = activación_origen * peso_conexion * decaimiento
        activacion_propagada = activacion_origen * peso_conexion * factor_distancia
        
        return max(0.0, min(1.0, activacion_propagada))
    
    def _calcular_activacion_inicial(self, nodo_id: str, palabras_clave: Set[str], 
                                   texto_consulta: str) -> float:
        """Calcula activación inicial basada en similitud con consulta."""
        metadatos = self.metadatos_contextos.get(nodo_id, {})
        
        # Similitud por palabras clave
        palabras_nodo = set(palabra.lower() for palabra in metadatos.get('palabras_clave', []))
        interseccion = len(palabras_clave & palabras_nodo)
        union = len(palabras_clave | palabras_nodo)
        
        similitud_jaccard = interseccion / union if union > 0 else 0.0
        
        # Similitud semántica básica por longitud de texto común
        texto_nodo = metadatos.get('texto', '').lower()
        palabras_consulta_texto = texto_consulta.lower().split()
        palabras_nodo_texto = texto_nodo.split()
        
        interseccion_texto = len(set(palabras_consulta_texto) & set(palabras_nodo_texto))
        similitud_textual = interseccion_texto / max(len(palabras_consulta_texto), 1)
        
        # Combinear similitudes
        activacion = (similitud_jaccard + similitud_textual) / 2
        
        return min(1.0, max(0.0, activacion))

    def configurar_parametros(self, factor_decaimiento: float = None, 
                            umbral_activacion: float = None):
        """Permite configurar parámetros del algoritmo."""
        if factor_decaimiento is not None:
            self.factor_decaimiento = max(0.1, min(1.0, factor_decaimiento))
        
        if umbral_activacion is not None:
            self.umbral_activacion = max(0.01, min(0.5, umbral_activacion))


# Funciones de integración con el sistema existente
def crear_propagador(grafo, metadatos_contextos):
    """Factory para crear instancia del propagador."""
    return PropagadorActivacion(grafo, metadatos_contextos)


def propagar_desde_consulta_integrado(pregunta: str, grafo, metadatos_contextos, 
                                    max_pasos: int = 2) -> Dict:
    """
    Función de integración que usa propagación para enriquecer consultas.
    Returns:
        Dict con contextos encontrados por propagación
    """
    from agent.extractor import extraer_palabras_clave
    
    # Crear propagador
    propagador = crear_propagador(grafo, metadatos_contextos)
    
    # Extraer palabras clave de la consulta
    palabras_clave = extraer_palabras_clave(pregunta)
    
    # Propagar desde la consulta
    resultados_propagacion = propagador.propagar_desde_consulta(
        palabras_clave, pregunta, max_pasos=max_pasos
    )
    
    # Convertir a formato compatible con el sistema existente
    contextos_propagados = {}
    caminos_indirectos = {}
    
    for nodo_id, datos in resultados_propagacion.items():
        contextos_propagados[nodo_id] = {
            'activacion': datos['activacion'],
            'fuentes': datos['fuentes'],
            'es_indirecto': True,
            **datos['metadatos']
        }
        
        # Encontrar caminos indirectos desde las fuentes
        for fuente in datos['fuentes']:
            caminos = propagador.encontrar_caminos_indirectos(fuente, nodo_id)
            if caminos:
                caminos_indirectos[f"{fuente}->{nodo_id}"] = caminos
    
    return {
        'contextos_propagados': contextos_propagados,
        'caminos_indirectos': caminos_indirectos,
        'total_nodos_alcanzados': len(contextos_propagados)
    }