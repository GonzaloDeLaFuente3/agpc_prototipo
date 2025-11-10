# agent/visualizador_doble.py
from typing import Dict, List, Set
from collections import defaultdict
import networkx as nx
from datetime import datetime

class VisualizadorDobleNivel:
    """
    Genera visualizaciones de doble nivel:
    - Vista Macro: Conversaciones como nodos, relaciones agregadas
    - Vista Micro: Fragmentos individuales con conexiones precisas
    """
    def __init__(self, grafo_contextos, metadatos_contextos, conversaciones_metadata, fragmentos_metadata):
        self.grafo_contextos = grafo_contextos
        self.metadatos_contextos = metadatos_contextos
        self.conversaciones_metadata = conversaciones_metadata
        self.fragmentos_metadata = fragmentos_metadata
    
    def generar_vista_macro_conversaciones(self) -> Dict:
        """
        Vista MACRO: Nodos = conversaciones completas, aristas = relaciones calculadas desde fragmentos.
        """
        nodos_conversaciones = []
        edges_conversaciones = []
        
        # 1. Crear nodos de conversaciones
        for conv_id, conv_data in self.conversaciones_metadata.items():
            # Calcular estadísticas de la conversación
            fragmentos_ids = conv_data.get('fragmentos_ids', [])
            total_fragmentos = len(fragmentos_ids)
            
            # Contar fragmentos temporales
            fragmentos_temporales = sum(1 for frag_id in fragmentos_ids 
                                      if self.metadatos_contextos.get(frag_id, {}).get('es_temporal', False))
            
            # Obtener tipos de contexto predominantes
            tipos_fragmentos = [self.metadatos_contextos.get(frag_id, {}).get('tipo_contexto', 'general') 
                              for frag_id in fragmentos_ids]
            tipo_predominante = max(set(tipos_fragmentos), key=tipos_fragmentos.count) if tipos_fragmentos else 'general'
            
            # Icono por tipo de conversación
            iconos_tipo = {
                "reunion": "👥",
                "entrevista": "🎤", 
                "brainstorm": "💡",
                "planning": "📄",
                "general": "💬"
            }
            
            tipo_conv = conv_data.get('metadata', {}).get('tipo', 'general')
            icono = iconos_tipo.get(tipo_conv, "💬")
            
            # Información de participantes
            participantes = conv_data.get('participantes', [])
            participantes_str = f" | {len(participantes)}👤" if participantes else ""
            
            # Fecha de la conversación
            fecha_str = ""
            if conv_data.get('fecha'):
                try:
                    fecha = datetime.fromisoformat(conv_data['fecha'])
                    fecha_str = f" | {fecha.strftime('%d/%m')}"
                except:
                    pass
            
            # Label compacto
            titulo = conv_data.get('titulo', 'Sin título')
            titulo_corto = titulo[:30] + "..." if len(titulo) > 30 else titulo
            label = f"{icono} {titulo_corto}{participantes_str}{fecha_str}"
            
            # Tooltip detallado
            tooltip = f"""Conversación: {titulo}
Fragmentos: {total_fragmentos} ({fragmentos_temporales} temporales)
Tipo predominante: {tipo_predominante}
Participantes: {', '.join(participantes) if participantes else 'N/A'}
Fecha: {conv_data.get('fecha', 'N/A')}
Dominio: {conv_data.get('metadata', {}).get('dominio', 'N/A')}"""
            
            nodos_conversaciones.append({
                "id": conv_id,
                "label": label,
                "title": tooltip,
                "group": "conversacion",
                "tipo_conversacion": tipo_conv,
                "total_fragmentos": total_fragmentos,
                "fragmentos_temporales": fragmentos_temporales,
                "tipo_predominante": tipo_predominante,
                "shape": "box",
                "size": max(15, min(40, total_fragmentos * 3))  # Tamaño proporcional a fragmentos
            })
        
        # 2. Calcular relaciones entre conversaciones basadas en fragmentos internos
        relaciones_conversaciones = defaultdict(lambda: {
            'peso_total': 0.0,
            'conexiones_fragmentos': 0,
            'max_peso_individual': 0.0,
            'tipos_relacion': set(),
            'detalles_conexiones': []
        })
        
        # Iterar sobre todas las aristas de fragmentos
        for origen, destino, datos_arista in self.grafo_contextos.edges(data=True):
            # Obtener conversaciones origen de cada fragmento
            conv_origen = self.metadatos_contextos.get(origen, {}).get('conversacion_id')
            conv_destino = self.metadatos_contextos.get(destino, {}).get('conversacion_id')
            
            # Si ambos fragmentos pertenecen a conversaciones diferentes
            if conv_origen and conv_destino and conv_origen != conv_destino:
                # Crear clave única para el par de conversaciones
                par_conv = tuple(sorted([conv_origen, conv_destino]))
                
                peso_efectivo = datos_arista.get('peso_efectivo', 0)
                peso_estructural = datos_arista.get('peso_estructural', 0) 
                relevancia_temporal = datos_arista.get('relevancia_temporal', 0)
                
                # Acumular estadísticas de relación
                rel_data = relaciones_conversaciones[par_conv]
                rel_data['peso_total'] += peso_efectivo
                rel_data['conexiones_fragmentos'] += 1
                rel_data['max_peso_individual'] = max(rel_data['max_peso_individual'], peso_efectivo)
                
                # Clasificar tipo de relación
                if relevancia_temporal > 0.3:
                    rel_data['tipos_relacion'].add('temporal')
                else:
                    rel_data['tipos_relacion'].add('semantica')
                
                # Guardar detalles de conexión
                rel_data['detalles_conexiones'].append({
                    'fragmento_origen': origen,
                    'fragmento_destino': destino,
                    'peso_efectivo': peso_efectivo,
                    'peso_estructural': peso_estructural,
                    'relevancia_temporal': relevancia_temporal
                })
        
        # 3. Crear aristas entre conversaciones
        for (conv_a, conv_b), datos_relacion in relaciones_conversaciones.items():
            if datos_relacion['peso_total'] > 0.3:  # Umbral mínimo para mostrar relación
                # Peso promedio de conexiones
                peso_promedio = datos_relacion['peso_total'] / datos_relacion['conexiones_fragmentos']
                peso_normalizado = min(1.0, datos_relacion['peso_total'] / 2.0)  # Normalizar para visualización
                
                # Determinar color según tipo de relación predominante
                es_temporal = 'temporal' in datos_relacion['tipos_relacion']
                color_arista = "#4caf50" if es_temporal else "#2196f3"
                
                # Label con información agregada
                label = f"P:{peso_promedio:.2f}|C:{datos_relacion['conexiones_fragmentos']}"
                
                # Tooltip detallado
                tipos_str = ", ".join(datos_relacion['tipos_relacion'])
                tooltip = f"""Conexiones entre conversaciones:
Fragmentos conectados: {datos_relacion['conexiones_fragmentos']}
Peso total: {datos_relacion['peso_total']:.2f}
Peso promedio: {peso_promedio:.2f}
Peso máximo individual: {datos_relacion['max_peso_individual']:.2f}
Tipos: {tipos_str}"""
                
                edges_conversaciones.append({
                    "from": conv_a,
                    "to": conv_b,
                    "weight": peso_normalizado,
                    "label": label,
                    "title": tooltip,
                    "color": {"color": color_arista},
                    "width": max(1, peso_promedio * 5),
                    "conexiones_fragmentos": datos_relacion['conexiones_fragmentos'],
                    "peso_total": datos_relacion['peso_total'],
                    "es_temporal": es_temporal,
                    "arrows": {"to": {"enabled": True, "scaleFactor": 1.2}}
                })

        # Eliminar aristas duplicadas y convertir a bidireccionales
        edges_conversaciones = self._eliminar_aristas_duplicadas(edges_conversaciones)
        
        return {
            "nodes": nodos_conversaciones,
            "edges": edges_conversaciones,
            "meta": {
                "tipo_vista": "macro_conversaciones",
                "total_conversaciones": len(nodos_conversaciones),
                "total_relaciones": len(edges_conversaciones),
                "generado_en": datetime.now().isoformat()
            }
        }
    
    def generar_vista_micro_fragmentos(self, filtro_conversacion: str = None) -> Dict:
        """
        Vista MICRO: Nodos = fragmentos individuales, aristas = conexiones precisas.
        
        Args:
            filtro_conversacion: Si se especifica, solo muestra fragmentos de esa conversación
        """
        # Usar la función existente pero con filtros opcionales
        if filtro_conversacion:
            # Vista micro filtrada por conversación específica
            return self._generar_vista_micro_filtrada(filtro_conversacion)
        else:
            from agent.grafo import exportar_grafo_para_visualizacion
            # Vista micro completa (todos los fragmentos)
            grafo_base = exportar_grafo_para_visualizacion()
            
            # Enriquecer con información de conversación
            for nodo in grafo_base["nodes"]:
                nodo_id = nodo["id"]
                meta = self.metadatos_contextos.get(nodo_id, {})
                
                if meta.get("es_fragmento"):
                    conv_id = meta.get("conversacion_id")
                    conv_titulo = ""
                    
                    if conv_id and conv_id in self.conversaciones_metadata:
                        conv_data = self.conversaciones_metadata[conv_id]
                        conv_titulo = conv_data.get("titulo", "")
                    
                    # Actualizar tooltip con información de conversación
                    titulo_original = nodo.get("title", "")
                    nodo["title"] = f"{titulo_original}\n🗣️ Conversación: {conv_titulo}\n📍 Fragmento {meta.get('posicion_fragmento', '?')}/{meta.get('total_fragmentos_conversacion', '?')}"
                    
                    # Modificar label para indicar que es fragmento
                    label_original = nodo.get("label", "")
                    nodo["label"] = f"🧩 {label_original}"

            # Eliminar aristas duplicadas y convertir a bidireccionales
            grafo_base["edges"] = self._eliminar_aristas_duplicadas(grafo_base["edges"])
            
            grafo_base["meta"] = {
                "tipo_vista": "micro_fragmentos_completa",
                "total_fragmentos": len(grafo_base["nodes"]),
                "total_relaciones": len(grafo_base["edges"]),
                "generado_en": datetime.now().isoformat()
            }
            
            return grafo_base
    
    def _generar_vista_micro_filtrada(self, conversacion_id: str) -> Dict:
        """Vista micro filtrada para una conversación específica."""
        if conversacion_id not in self.conversaciones_metadata:
            return {
                "nodes": [],
                "edges": [], 
                "meta": {"error": f"Conversación {conversacion_id} no encontrada"}
            }
        
        conv_data = self.conversaciones_metadata[conversacion_id]
        fragmentos_ids = set(conv_data.get('fragmentos_ids', []))
        
        nodos_filtrados = []
        edges_filtrados = []
        
        # 1. Crear nodos para fragmentos de esta conversación
        for frag_id in fragmentos_ids:
            if frag_id in self.metadatos_contextos:
                meta = self.metadatos_contextos[frag_id]
                
                # Información del fragmento
                titulo = meta.get("titulo", "Sin título")
                texto = meta.get("texto", "")
                tipo_contexto = meta.get("tipo_contexto", "general")
                posicion = meta.get("posicion_fragmento", "?")
                total_frags = conv_data.get("total_fragmentos", "?")
                es_temporal = meta.get("es_temporal", False)
                
                # Detectar si es un fragmento de PDF
                es_pdf = meta.get("es_pdf", False)

                if es_pdf:
                    # 📄 FRAGMENTO DE PDF - Mostrar nombre del documento
                    source_doc = meta.get('source_document', 'documento.pdf')
                    posicion_pdf = meta.get('position_in_doc', posicion)
                    total_frags_pdf = meta.get('total_fragmentos_pdf', total_frags)
                    
                    icono = "📄"
                    label = f"{icono} {source_doc} ({posicion_pdf + 1}/{total_frags_pdf})"
                    
                    # Tooltip específico para PDF
                    tooltip = f"""Documento: {source_doc}
                Fragmento {posicion_pdf + 1} de {total_frags_pdf}
                Tipo: PDF
                Temporal: {'Sí' if es_temporal else 'No'}
                Texto: {texto[:100]}..."""
                    
                else:
                    # FRAGMENTO DE CONVERSACIÓN NORMAL
                    # Icono por tipo
                    iconos_tipo = {
                        "reunion": "👥", "tarea": "📄", "evento": "🎯",
                        "proyecto": "🚀", "conocimiento": "📚", "general": "📄",
                        "decision": "⚖️", "accion": "⚡", "pregunta": "❓",
                        "conclusion": "🎯", "problema": "🚨"
                    }
                    
                    icono = iconos_tipo.get(tipo_contexto, "📄")
                    
                    # Label compacto con posición
                    label = f"{icono} Frag {posicion}/{total_frags}"
                    
                    # Tooltip detallado para conversación
                    tooltip = f"""Fragmento {posicion} de {total_frags}
                Tipo: {tipo_contexto}
                Temporal: {'Sí' if es_temporal else 'No'}
                Palabras clave: {', '.join(meta.get('palabras_clave', [])[:5])}
                Texto: {texto[:100]}..."""
                
                nodos_filtrados.append({
                    "id": frag_id,
                    "label": label,
                    "title": tooltip,
                    "group": "temporal" if es_temporal else "atemporal",
                    "tipo_contexto": tipo_contexto,
                    "posicion": posicion,
                    "shape": "box"
                })
        
        # 2. Crear aristas entre fragmentos de esta conversación
        for origen, destino, datos in self.grafo_contextos.edges(data=True):
            if origen in fragmentos_ids and destino in fragmentos_ids:
                # Obtener datos de la arista
                peso_estructural = datos.get('peso_estructural', 0)
                relevancia_temporal = datos.get('relevancia_temporal', 0)
                peso_efectivo = datos.get('peso_efectivo', 0)
                
                # Color y grosor
                es_temporal = relevancia_temporal > 0.3
                color_arista = "#4caf50" if es_temporal else "#2196f3"
                width = max(2, peso_efectivo * 6)
                
                label = f"E:{peso_estructural:.2f}|T:{relevancia_temporal:.2f}|W:{peso_efectivo:.2f}"
                
                edges_filtrados.append({
                    "from": origen,
                    "to": destino,
                    "weight": peso_efectivo,
                    "label": label,
                    "title": f"Peso Estructural: {peso_estructural:.3f}\nRelevancia Temporal: {relevancia_temporal:.3f}\nPeso Efectivo: {peso_efectivo:.3f}",
                    "color": {"color": color_arista},
                    "width": width,
                    "peso_estructural": peso_estructural,
                    "relevancia_temporal": relevancia_temporal,
                    "peso_efectivo": peso_efectivo
                })

        # Eliminar aristas duplicadas y convertir a bidireccionales
        edges_filtrados = self._eliminar_aristas_duplicadas(edges_filtrados)
        
        return {
            "nodes": nodos_filtrados,
            "edges": edges_filtrados,
            "meta": {
                "tipo_vista": "micro_fragmentos_filtrada",
                "conversacion_id": conversacion_id,
                "conversacion_titulo": conv_data.get("titulo", ""),
                "total_fragmentos": len(nodos_filtrados),
                "total_relaciones": len(edges_filtrados),
                "generado_en": datetime.now().isoformat()
            }
        }
    
    def obtener_estadisticas_doble_nivel(self) -> Dict:
        """Estadísticas comparativas entre ambos niveles de visualización."""
        # Estadísticas de conversaciones (macro)
        total_conversaciones = len(self.conversaciones_metadata)
        conversaciones_con_multiples_fragmentos = sum(
            1 for conv_data in self.conversaciones_metadata.values()
            if conv_data.get('total_fragmentos', 0) > 1
        )
        
        # Estadísticas de fragmentos (micro)
        total_fragmentos = len(self.fragmentos_metadata)
        fragmentos_temporales = sum(
            1 for meta in self.metadatos_contextos.values()
            if meta.get('es_fragmento') and meta.get('es_temporal')
        )
        
        # Relaciones entre niveles
        relaciones_intra_conversacion = 0  # Entre fragmentos de misma conversación
        relaciones_inter_conversacion = 0  # Entre fragmentos de diferentes conversaciones
        
        for origen, destino, datos in self.grafo_contextos.edges(data=True):
            conv_origen = self.metadatos_contextos.get(origen, {}).get('conversacion_id')
            conv_destino = self.metadatos_contextos.get(destino, {}).get('conversacion_id')
            
            if conv_origen and conv_destino:
                if conv_origen == conv_destino:
                    relaciones_intra_conversacion += 1
                else:
                    relaciones_inter_conversacion += 1
        
        # Distribución por tipos
        tipos_conversaciones = {}
        tipos_fragmentos = {}
        
        for conv_data in self.conversaciones_metadata.values():
            tipo = conv_data.get('metadata', {}).get('tipo', 'general')
            tipos_conversaciones[tipo] = tipos_conversaciones.get(tipo, 0) + 1
        
        for meta in self.metadatos_contextos.values():
            if meta.get('es_fragmento'):
                tipo = meta.get('tipo_contexto', 'general')
                tipos_fragmentos[tipo] = tipos_fragmentos.get(tipo, 0) + 1
        
        return {
            "nivel_macro": {
                "total_conversaciones": total_conversaciones,
                "conversaciones_complejas": conversaciones_con_multiples_fragmentos,
                "tipos_conversaciones": tipos_conversaciones
            },
            "nivel_micro": {
                "total_fragmentos": total_fragmentos,
                "fragmentos_temporales": fragmentos_temporales,
                "fragmentos_atemporales": total_fragmentos - fragmentos_temporales,
                "tipos_fragmentos": tipos_fragmentos
            },
            "relaciones": {
                "intra_conversacion": relaciones_intra_conversacion,
                "inter_conversacion": relaciones_inter_conversacion,
                "total_relaciones": self.grafo_contextos.number_of_edges()
            },
            "metricas": {
                "promedio_fragmentos_por_conversacion": round(total_fragmentos / max(1, total_conversaciones), 2),
                "ratio_relaciones_internas": round(relaciones_intra_conversacion / max(1, self.grafo_contextos.number_of_edges()) * 100, 1),
                "ratio_temporal_micro": round(fragmentos_temporales / max(1, total_fragmentos) * 100, 1)
            }
        }
    
    def _eliminar_aristas_duplicadas(self, edges: List[Dict]) -> List[Dict]:
        """
        Elimina aristas duplicadas manteniendo solo una por par de nodos.
        Si existen A→B y B→A, las convierte en una sola arista bidireccional,
        promediando los pesos.
        """
        aristas_unicas = {}
        
        for edge in edges:
            nodo_a, nodo_b = edge['from'], edge['to']
            # Crear clave ordenada para detectar duplicados
            clave = tuple(sorted([nodo_a, nodo_b]))
            
            if clave in aristas_unicas:
                # Ya existe, promediar pesos
                edge_existente = aristas_unicas[clave]
                
                # Promediar peso_efectivo
                peso_actual = edge.get('peso_efectivo', edge.get('weight', 0))
                peso_existente = edge_existente.get('peso_efectivo', edge_existente.get('weight', 0))
                peso_promedio = (peso_actual + peso_existente) / 2
                
                # Promediar peso_estructural si existe
                if 'peso_estructural' in edge or 'peso_estructural' in edge_existente:
                    peso_est_actual = edge.get('peso_estructural', 0)
                    peso_est_existente = edge_existente.get('peso_estructural', 0)
                    peso_est_promedio = (peso_est_actual + peso_est_existente) / 2
                    edge_existente['peso_estructural'] = peso_est_promedio
                
                # Promediar relevancia_temporal si existe
                if 'relevancia_temporal' in edge or 'relevancia_temporal' in edge_existente:
                    rel_temp_actual = edge.get('relevancia_temporal', 0)
                    rel_temp_existente = edge_existente.get('relevancia_temporal', 0)
                    rel_temp_promedio = (rel_temp_actual + rel_temp_existente) / 2
                    edge_existente['relevancia_temporal'] = rel_temp_promedio
                
                # Promediar peso_total si existe (para vista macro)
                if 'peso_total' in edge or 'peso_total' in edge_existente:
                    peso_total_actual = edge.get('peso_total', 0)
                    peso_total_existente = edge_existente.get('peso_total', 0)
                    peso_total_promedio = (peso_total_actual + peso_total_existente) / 2
                    edge_existente['peso_total'] = peso_total_promedio
                
                # Promediar conexiones_fragmentos si existe (para vista macro)
                if 'conexiones_fragmentos' in edge or 'conexiones_fragmentos' in edge_existente:
                    conex_actual = edge.get('conexiones_fragmentos', 0)
                    conex_existente = edge_existente.get('conexiones_fragmentos', 0)
                    conex_promedio = int((conex_actual + conex_existente) / 2)
                    edge_existente['conexiones_fragmentos'] = conex_promedio
                
                # Actualizar weight y width
                edge_existente['peso_efectivo'] = peso_promedio
                edge_existente['weight'] = peso_promedio
                
                if 'width' in edge_existente:
                    edge_existente['width'] = max(1, peso_promedio * 5)
                
            else:
                # Primera vez que vemos este par, agregarlo
                aristas_unicas[clave] = edge.copy()
        
        # Convertir a bidireccionales (sin flechas)
        resultado = []
        for edge in aristas_unicas.values():
            # Remover direccionalidad visual
            edge['arrows'] = {'to': {'enabled': False}, 'from': {'enabled': False}}
            resultado.append(edge)
        
        return resultado