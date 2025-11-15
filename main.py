# main.py
import json
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Optional, Union
import os
from agent import grafo, responder
from agent.semantica import indexar_documento, buscar_similares
from agent.temporal_llm_parser import analizar_temporalidad_con_llm
from datetime import datetime
from agent.text_batch_processor import TextBatchProcessor
from agent.utils import parse_iso_datetime_safe
from agent.utils import normalizar_timestamp_para_guardar
import re 
from fastapi import File, UploadFile, Form
from agent.pdf_processor import guardar_pdf_en_storage, crear_attachment_pdf
import shutil
from agent import grafo as modulo_grafo
import networkx as nx
from agent.metricas import metricas_sistema
import time
import traceback
from agent.semantica import coleccion

# Inicialización
grafo.cargar_desde_disco()

# Reindexar contextos existentes
for id, datos in grafo.obtener_todos().items():
    indexar_documento(id, datos["texto"])

app = FastAPI()

# Variables globales para los parámetros configurables
parametros_sistema = {
    'umbral_similitud': 0.5,
    'factor_refuerzo_temporal': 1.5,
    'k_resultados': 5,
}

class EntradaContexto(BaseModel):
    titulo: str
    texto: str
    es_temporal: Optional[bool] = None
    referencia_temporal: Optional[str] = None

class ConfiguracionParametros(BaseModel):
    umbral_similitud: Optional[float] = None
    factor_refuerzo_temporal: Optional[float] = None
    k_resultados: Optional[int] = None 

class EntradaTextoPlano(BaseModel):
    texto: str

class EntradaJSON(BaseModel):
    json_data: dict

class ProcesarConMetadata(BaseModel):
    conversaciones: List[Dict]
    metadata_global: Optional[Dict] = None

@app.post("/contexto/")
def agregar_contexto(entrada: EntradaContexto):
    """Agrega un nuevo contexto al grafo con prevención de duplicados."""
    nuevo_id = grafo.agregar_contexto(
        entrada.titulo, 
        entrada.texto, 
        entrada.es_temporal,
        entrada.referencia_temporal
    )
    
    contexto_creado = grafo.metadatos_contextos[nuevo_id]
    
    return {
        "status": "agregado", 
        "id": nuevo_id,
        "es_temporal": contexto_creado.get("es_temporal", False)
    }

@app.get("/contexto/")
def obtener_contextos():
    """Obtiene todos los contextos."""
    return grafo.obtener_todos()

@app.get("/preguntar/")
def preguntar(pregunta: str):
    """Responde a una pregunta considerando momento de consulta."""
    pregunta = pregunta.strip()
    momento_consulta = datetime.now()  # Capturar momento exacto
    todos_contextos = grafo.obtener_todos()

    if not todos_contextos:
        return {
            "respuesta": "[ERROR] No hay contextos almacenados en el sistema",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}},
            "momento_consulta": momento_consulta.isoformat()
        }

    try:
        # Análisis completo con momento de consulta
        analisis_completo = grafo.analizar_consulta_completa(pregunta, momento_consulta)
        analisis_intencion = analisis_completo["analisis_intencion"]
        ids_similares = analisis_completo["contextos_recuperados"]
        arbol = analisis_completo["arbol_consulta"]
        estrategia = analisis_completo["estrategia_aplicada"]
        
    except Exception as e:
        print(f"Error en análisis: {e}")
        # Fallback a búsqueda básica
        ids_similares = buscar_similares(pregunta, k=5)
        analisis_intencion = {"error": f"Error en análisis: {str(e)}"}
        estrategia = {"error": "Estrategia fallback aplicada"}
        arbol = {"nodes": [], "edges": [], "meta": {"error": "Error en construcción"}}

    # Recopilar contextos relevantes
    contextos_relevantes = {}
    contextos_utilizados_info = []
    
    for id_ctx in ids_similares:
        if id_ctx in todos_contextos:
            contextos_relevantes[id_ctx] = todos_contextos[id_ctx]
            ctx = todos_contextos[id_ctx]
            
            # Información extendida del contexto
            info_ctx = {
                "titulo": ctx["titulo"],
                "id": id_ctx,
                "es_temporal": ctx.get("es_temporal", False),
                "tipo_contexto": ctx.get("tipo_contexto", "general")
            }

            # Agregar información temporal si existe
            if ctx.get("timestamp"):
                fecha_ctx = parse_iso_datetime_safe(ctx["timestamp"])
                if not fecha_ctx:
                    # Si no se puede parsear la fecha, skip el cálculo temporal
                    continue
                info_ctx["fecha_contexto"] = fecha_ctx.isoformat()
                
                # Diferencia temporal con momento consulta
                diff_seconds = (momento_consulta - fecha_ctx).total_seconds()
                diff_hours = diff_seconds / 3600
                
                if abs(diff_hours) < 24:
                    info_ctx["diferencia_temporal"] = f"{diff_hours:+.1f} horas"
                else:
                    diff_days = diff_hours / 24
                    info_ctx["diferencia_temporal"] = f"{diff_days:+.1f} días"
            
            contextos_utilizados_info.append(info_ctx)

    if not contextos_relevantes:
        return {
            "respuesta": "[ERROR] No se encontraron contextos relevantes",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "Sin contextos relevantes"}},
            "analisis_intencion": analisis_intencion,
            "momento_consulta": momento_consulta.isoformat()
        }

    # Generar respuesta con IA
    respuesta = responder.responder_con_ia(pregunta, contextos_relevantes)

    # Información adicional mejorada
    titulos_utilizados = [c["titulo"] for c in contextos_utilizados_info]
    temporales = [c for c in contextos_utilizados_info if c.get("es_temporal")]
    
    # Información de estrategia aplicada
    info_estrategia = ""
    if estrategia.get("ventana_temporal_aplicada"):
        info_estrategia += " [Filtro temporal aplicado]"
    if estrategia.get("contextos_filtrados_temporalmente", 0) > 0:
        info_estrategia += f" ({estrategia['contextos_filtrados_temporalmente']} contextos filtrados por tiempo)"
    
    # Agregar contexto usado a la respuesta
    info_temporal = f" ({len(temporales)} temporales)" if temporales else ""
    momento_str = momento_consulta.strftime("%d/%m %H:%M")
    respuesta_completa = f"{respuesta}\n\n📚 Contextos: {', '.join(titulos_utilizados)}{info_temporal}\n🕐 Consultado: {momento_str}{info_estrategia}"

    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info,
        "subgrafo": arbol,
        "analisis_intencion": analisis_intencion,
        "estrategia_aplicada": estrategia,
        "momento_consulta": momento_consulta.isoformat()
    }

@app.get("/preguntar-con-propagacion/")
def preguntar_con_propagacion(pregunta: str, usar_propagacion: bool = True, max_pasos: int = 2,
                             factor_decaimiento: float = None, umbral_activacion: float = None,k_inicial: int = None):
    """Responde a una pregunta usando propagación de activación."""
    # INICIAR MEDICIÓN DE TIEMPO
    tiempo_inicio = time.time()

    # VALIDACIÓN DE ENTRADA
    if not pregunta or len(pregunta.strip()) < 2:
        return {
            "respuesta": "[ERROR] Pregunta demasiado corta o vacía",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "Entrada inválida"}},
            "momento_consulta": datetime.now().isoformat()
        }
    
    # Limpiar pregunta manteniendo caracteres esenciales
    pregunta = re.sub(r'[^\w\sáéíóúñ¿?¡!]', ' ', pregunta.strip())
    pregunta = re.sub(r'\s+', ' ', pregunta).strip()
    
    if len(pregunta) < 3:
        return {
            "respuesta": "[ERROR] Pregunta demasiado corta después de limpieza",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "Entrada inválida"}},
            "momento_consulta": datetime.now().isoformat()
        }
    momento_consulta = datetime.now()
    todos_contextos = grafo.obtener_todos()

    if not todos_contextos:
        return {
            "respuesta": "[ERROR] No hay contextos almacenados en el sistema",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}},
            "momento_consulta": momento_consulta.isoformat(),
            "propagacion": {"error": "Sin contextos base"}
        }

    try:
        # Usar k_inicial del parámetro o el valor configurado en el sistema
        k_busqueda = k_inicial if k_inicial is not None else parametros_sistema.get('k_resultados', 5)
        # Obtener factor base configurado
        factor_base = parametros_sistema.get('factor_refuerzo_temporal', 1.5)
        print(f"⚙️ Factor base configurado: {factor_base}")
        print(f"⚙️ k_inicial: {k_busqueda}") 
        
        # Análisis con propagación
        analisis_completo = grafo.analizar_consulta_con_propagacion(
            pregunta, momento_consulta, usar_propagacion, max_pasos,
            factor_decaimiento, umbral_activacion,
            k_inicial=k_busqueda,
            factor_refuerzo_temporal_custom=factor_base
        )
        # VERIFICAR que se aplicó en la respuesta
        if 'estrategia_aplicada' in analisis_completo:
            analisis_completo['estrategia_aplicada']['factor_refuerzo_configurado'] = factor_base
                
        analisis_intencion = analisis_completo["analisis_intencion"]
        ids_similares = analisis_completo["contextos_recuperados"]
        arbol = analisis_completo["arbol_consulta"]
        estrategia = analisis_completo["estrategia_aplicada"]
        info_propagacion = analisis_completo.get("propagacion", {})
        
    except Exception as e:
        print(f"Error en análisis con propagación: {e}")
        # Fallback a método básico
        ids_similares = buscar_similares(pregunta, k=5)
        analisis_intencion = {"error": f"Error en análisis: {str(e)}"}
        estrategia = {"error": "Estrategia fallback aplicada"}
        arbol = {"nodes": [], "edges": [], "meta": {"error": "Error en construcción"}}
        info_propagacion = {"error": str(e)}

    # Recopilar contextos relevantes
    contextos_relevantes = {}
    contextos_utilizados_info = []
    
    for id_ctx in ids_similares:
        if id_ctx in todos_contextos:
            contextos_relevantes[id_ctx] = todos_contextos[id_ctx]
            ctx = todos_contextos[id_ctx]
            
            # Información extendida del contexto
            info_ctx = {
                "titulo": ctx["titulo"],
                "id": id_ctx,
                "es_temporal": ctx.get("es_temporal", False),
                "tipo_contexto": ctx.get("tipo_contexto", "general")
            }

            # NUEVO: Agregar información de profundidad si viene de propagación
            if analisis_completo.get('propagacion'):
                profundidades = analisis_completo['propagacion'].get('profundidades', {})
                contextos_directos = analisis_completo['propagacion'].get('contextos_directos', [])
                
                if id_ctx in profundidades:
                    info_ctx["profundidad_propagacion"] = profundidades[id_ctx]
                    info_ctx["encontrado_por"] = "propagacion"
                elif id_ctx in contextos_directos:
                    info_ctx["profundidad_propagacion"] = 0
                    info_ctx["encontrado_por"] = "busqueda_directa"
            
            # Marcar si fue encontrado por propagación
            encontrado_por = None
            if info_propagacion.get('solo_por_propagacion') and id_ctx in info_propagacion['solo_por_propagacion']:
                encontrado_por = 'propagacion'
                info_ctx['activacion'] = 'encontrado por propagación'
            elif info_propagacion.get('contextos_directos') and id_ctx in info_propagacion['contextos_directos']:
                encontrado_por = 'busqueda_directa'
            
            if encontrado_por:
                info_ctx['encontrado_por'] = encontrado_por
            
            # Agregar información temporal si existe
            if ctx.get("timestamp"):
                fecha_ctx = parse_iso_datetime_safe(ctx["timestamp"])
                if not fecha_ctx:
                    # Si no se puede parsear la fecha, skip el cálculo temporal
                    continue
                info_ctx["fecha_contexto"] = fecha_ctx.isoformat()
                
                # Diferencia temporal con momento consulta
                diff_seconds = (momento_consulta - fecha_ctx).total_seconds()
                diff_hours = diff_seconds / 3600
                
                if abs(diff_hours) < 24:
                    info_ctx["diferencia_temporal"] = f"{diff_hours:+.1f} horas"
                else:
                    diff_days = diff_hours / 24
                    info_ctx["diferencia_temporal"] = f"{diff_days:+.1f} días"
            
            contextos_utilizados_info.append(info_ctx)

    if not contextos_relevantes:
        return {
            "respuesta": "[ERROR] No se encontraron contextos relevantes",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "Sin contextos relevantes"}},
            "analisis_intencion": analisis_intencion,
            "momento_consulta": momento_consulta.isoformat(),
            "propagacion": info_propagacion
        }

    # Generar respuesta con IA
    respuesta = responder.responder_con_ia(pregunta, contextos_relevantes)

    # Información adicional mejorada
    titulos_utilizados = [c["titulo"] for c in contextos_utilizados_info]
    temporales = [c for c in contextos_utilizados_info if c.get("es_temporal")]
    por_propagacion = [c for c in contextos_utilizados_info if c.get("encontrado_por") == "propagacion"]
    
    # Información de estrategia aplicada
    info_estrategia = ""
    if estrategia.get("ventana_temporal_aplicada"):
        info_estrategia += " [Filtro temporal aplicado]"
    if estrategia.get("contextos_filtrados_temporalmente", 0) > 0:
        info_estrategia += f" ({estrategia['contextos_filtrados_temporalmente']} contextos filtrados por tiempo)"
    
    if usar_propagacion and info_propagacion.get('total_nodos_alcanzados', 0) > 0:
        info_estrategia += f" [Propagación: +{len(por_propagacion)} contextos indirectos]"
    
    # Agregar contexto usado a la respuesta
    info_temporal = f" ({len(temporales)} temporales)" if temporales else ""
    info_propagacion_resp = f" (+{len(por_propagacion)} por propagación)" if por_propagacion else ""
    momento_str = momento_consulta.strftime("%d/%m %H:%M")
    
    respuesta_completa = f"{respuesta}\n\n📚 Contextos: {', '.join(titulos_utilizados)}{info_temporal}{info_propagacion_resp}\n🕐 Consultado: {momento_str}{info_estrategia}"

    # CALCULAR TIEMPO TRANSCURRIDO
    tiempo_fin = time.time()
    tiempo_ms = (tiempo_fin - tiempo_inicio) * 1000
    
    # REGISTRAR MÉTRICA
    metricas_sistema.registrar_consulta(
        pregunta=pregunta,
        tiempo_ms=tiempo_ms,
        contextos_utilizados=len(contextos_utilizados_info),
        usa_propagacion=usar_propagacion
    )

    # ============ NUEVO: LOGGING DE MÉTRICAS DE PROFUNDIDAD ============
    
    # Solo mostrar si hay propagación activa
    if usar_propagacion and info_propagacion.get('profundidades'):
        print("\n" + "=" * 80)
        print("📊 MÉTRICAS DE PROFUNDIDAD DE PROPAGACIÓN")
        print("=" * 80)
        
        profundidades = info_propagacion['profundidades']
        
        # Calcular métricas
        valores_profundidad = list(profundidades.values())
        PP = sum(valores_profundidad) / len(valores_profundidad) if valores_profundidad else 0
        
        total_contextos = len(contextos_utilizados_info)
        contextos_propagados = len(profundidades)
        contextos_directos = total_contextos - contextos_propagados
        CIR = (contextos_propagados / total_contextos * 100) if total_contextos > 0 else 0
        
        # Mostrar métricas principales
        print(f"\n✅ Profundidad de Propagación (PP): {PP:.2f} saltos")
        print(f"   └─ Promedio de saltos desde nodos semilla hasta nodos objetivo")
        
        print(f"\n✅ Contextos Indirectos Recuperados (CIR): {CIR:.1f}%")
        print(f"   ├─ Por propagación: {contextos_propagados}")
        print(f"   ├─ Por búsqueda directa: {contextos_directos}")
        print(f"   └─ Total contextos: {total_contextos}")
        
        # Distribución de profundidades
        from collections import Counter
        distribucion = Counter(valores_profundidad)
        print(f"\n📊 Distribución de profundidades:")
        for profundidad in sorted(distribucion.keys()):
            cantidad = distribucion[profundidad]
            barra = "█" * cantidad
            print(f"   {profundidad} saltos: {barra} ({cantidad} contextos)")
        
        # Detalle de contextos con profundidad
        print(f"\n📋 DETALLE DE CONTEXTOS RECUPERADOS:")
        print("-" * 80)
        
        for i, ctx_info in enumerate(contextos_utilizados_info, 1):
            titulo = ctx_info['titulo'][:60]
            profundidad = ctx_info.get('profundidad_propagacion', 'N/A')
            encontrado_por = ctx_info.get('encontrado_por', 'desconocido')
            
            # Emoji según origen
            if encontrado_por == 'busqueda_directa':
                emoji = "🎯"
                tipo_str = "DIRECTO"
            else:
                emoji = "🔄"
                tipo_str = "PROPAGACIÓN"
            
            print(f"{i:2d}. {emoji} {titulo}")
            print(f"    └─ Profundidad: {profundidad} saltos | Origen: {tipo_str}")
        
        print("\n" + "=" * 80 + "\n")
    
    # ============ FIN LOGGING ============
    
    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info,
        "subgrafo": arbol,
        "analisis_intencion": analisis_intencion,
        "estrategia_aplicada": estrategia,
        "momento_consulta": momento_consulta.isoformat(),
        "propagacion": info_propagacion,
        "tiempo_respuesta_ms": round(tiempo_ms, 2),  
        "tiempo_respuesta_segundos": round(tiempo_ms / 1000, 2)  
    }

@app.post("/configurar-propagacion/")
def configurar_parametros_propagacion_endpoint(factor_decaimiento: float = None, umbral_activacion: float = None):
    """Configura parámetros del algoritmo de propagación."""
    resultado = grafo.configurar_parametros_propagacion(factor_decaimiento, umbral_activacion)
    return resultado

# TAMBIÉN MANTENER el endpoint de estado:
@app.get("/estado-propagacion/")
def obtener_estado_propagacion_endpoint():
    """Obtiene el estado actual del sistema de propagación."""
    return grafo.obtener_estado_propagacion()

@app.post("ic")
def reiniciar_chromadb_endpoint():
    """
    ⚠️ ENDPOINT PELIGROSO: Elimina TODOS los embeddings de ChromaDB.
    Usar solo cuando se necesita recargar el dataset completamente desde cero.
    """
    from agent.semantica import reiniciar_coleccion
    resultado = reiniciar_coleccion()
    return resultado

@app.get("/verificar-chromadb/")
def verificar_chromadb_endpoint():
    """
    Verifica el estado actual de ChromaDB (cuántos documentos hay indexados).
    """
    from agent.semantica import verificar_estado_coleccion
    count = verificar_estado_coleccion()
    return {
        "total_documentos": count,
        "mensaje": f"ChromaDB contiene {count} documentos indexados"
    }
    
@app.get("/buscar/")
def buscar_por_texto(texto: str):
    """Busca contextos por similitud semántica."""
    texto = texto.strip()
    ids_similares = buscar_similares(texto)
    todos = grafo.obtener_todos()
    return {id: todos[id] for id in ids_similares if id in todos}

@app.get("/query/analizar/")
def analizar_query(pregunta: str):
    """Analiza la intención temporal de una pregunta."""
    momento_consulta = datetime.now()
    factor_base = parametros_sistema.get('factor_refuerzo_temporal', 1.5)
    return analizar_temporalidad_con_llm(pregunta, momento_consulta, factor_base)

# ENDPOINTS PARA CONVERSACIONES
class EntradaConversacion(BaseModel):
    titulo: str
    contenido: str
    fecha: Optional[str] = None
    participantes: Optional[List[str]] = None
    metadata: Optional[dict] = None
    
@app.post("/agregar_conversacion_con_pdf")
async def agregar_conversacion_con_pdf(
    titulo: str = Form(...),
    contenido: str = Form(...),
    fecha: Optional[str] = Form(None),
    participantes: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None)
):
    """
    Agrega una nueva conversación con opción de adjuntar un PDF.
    """
    # INICIAR MEDICIÓN
    tiempo_inicio = time.time()

    try:
        # Generar ID de conversación
        conversacion_id = f"conv_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Procesar participantes
        lista_participantes = []
        if participantes:
            lista_participantes = [p.strip() for p in participantes.split(',') if p.strip()]
        
        # Procesar fecha
        fecha_procesada = None

        if fecha:
            # CASO 1: Verificar si es atemporal explícito
            if fecha == 'ATEMPORAL':
                fecha_procesada = None
                print(f"⚪ Conversación ATEMPORAL (sin fecha)")
            
            # CASO 2: Conversación con fecha específica
            else:
                fecha_procesada = normalizar_timestamp_para_guardar(fecha)
                if not fecha_procesada:
                    return {
                        "status": "error",
                        "mensaje": f"Formato de fecha inválido: {fecha}"
                    }
                print(f"📅 Conversación con fecha: {fecha_procesada}")

        # CASO 3: No se especificó fecha Y no se marcó como atemporal
        # → Usar fecha actual (comportamiento por defecto para conversaciones)
        else:
            fecha_procesada = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            print(f"📅 Conversación sin fecha explícita - usando fecha actual: {fecha_procesada}")
        
        # Procesar PDF si existe
        attachments = []
        if pdf_file and pdf_file.filename:
            print(f"📎 Procesando PDF: {pdf_file.filename}")
            
            # Validar que sea PDF
            if not pdf_file.filename.lower().endswith('.pdf'):
                return {
                    "status": "error",
                    "mensaje": "Solo se permiten archivos PDF"
                }
            
            # Validar tamaño (máximo 10MB)
            contenido_pdf = await pdf_file.read()
            tamaño_mb = len(contenido_pdf) / (1024 * 1024)
            
            if tamaño_mb > 10:
                return {
                    "status": "error",
                    "mensaje": f"El archivo es demasiado grande ({tamaño_mb:.1f}MB). Máximo 10MB."
                }
            
            # Guardar PDF en storage
            ruta_pdf = guardar_pdf_en_storage(
                contenido_pdf,
                pdf_file.filename,
                conversacion_id
            )
            
            if not ruta_pdf:
                return {
                    "status": "error",
                    "mensaje": "Error al guardar el archivo PDF"
                }
            
            # Crear estructura de attachment
            attachment = crear_attachment_pdf(
                ruta_pdf,
                pdf_file.filename,
                conversacion_id
            )
            
            if not attachment:
                return {
                    "status": "error",
                    "mensaje": "Error al procesar el contenido del PDF"
                }
            
            attachments.append(attachment)
            print(f"PDF procesado: {pdf_file.filename}")
        
        # Agregar conversación al grafo
        resultado = grafo.agregar_conversacion(
            titulo=titulo,
            contenido=contenido,
            fecha=fecha_procesada,
            participantes=lista_participantes,
            attachments=attachments
        )

        # ⏱️ CALCULAR TIEMPO
        tiempo_fin = time.time()
        tiempo_ms = (tiempo_fin - tiempo_inicio) * 1000
        
        # 📊 REGISTRAR MÉTRICA
        total_fragmentos = resultado.get('total_fragmentos', 0)
        metricas_sistema.registrar_carga_dataset(
            tipo='conversacion_individual',
            cantidad=1,
            tiempo_ms=tiempo_ms,
            detalles={
                "titulo": titulo,
                "total_fragmentos": total_fragmentos,
                "tiene_pdf": bool(attachments)
            }
        )
        
        mensaje = f"Conversación '{titulo}' agregada correctamente"
        if attachments:
            mensaje += f" con PDF adjunto"
        
        return {
            "status": "éxito",
            "mensaje": mensaje,
            "conversacion_id": conversacion_id,
            "tiempo_procesamiento_ms": round(tiempo_ms, 2),  
            "tiempo_procesamiento_segundos": round(tiempo_ms / 1000, 2),  
            **resultado
        }
    
    except Exception as e:
        print(f"❌ Error al agregar conversación: {e}")
        traceback.print_exc()
        return {"status": "error", "mensaje": str(e)}

@app.get("/conversaciones/")
def obtener_conversaciones():
    """Obtiene todas las conversaciones."""
    return grafo.obtener_conversaciones()

@app.get("/conversacion/{conversacion_id}/fragmentos")
def obtener_fragmentos_conversacion(conversacion_id: str):
    """Obtiene fragmentos de una conversación específica."""
    return grafo.obtener_fragmentos_de_conversacion(conversacion_id)

# ENDPOINTS PARA CARGA MASIVA DE DATASETS
class DatasetUpload(BaseModel):
    dataset: dict
    sobrescribir: bool = False
    
#ENDPOINTS PARA VISUALIZACIÓN DOBLE NIVEL
@app.get("/grafo/macro/conversaciones/")
def exportar_grafo_macro():
    """Vista macro: conversaciones como nodos, relaciones agregadas."""
    return grafo.exportar_grafo_macro_conversaciones()

@app.get("/grafo/micro/fragmentos/")
def exportar_grafo_micro_completo():
    """Vista micro: todos los fragmentos individuales."""
    return grafo.exportar_grafo_micro_fragmentos()

@app.get("/grafo/micro/conversacion/{conversacion_id}")
def exportar_grafo_micro_conversacion(conversacion_id: str):
    """Vista micro filtrada: solo fragmentos de una conversación específica."""
    return grafo.exportar_grafo_micro_fragmentos(conversacion_id)

@app.get("/estadisticas/doble-nivel/")
def obtener_estadisticas_doble_nivel():
    """Estadísticas comparativas entre vista macro y micro."""
    return grafo.obtener_estadisticas_doble_nivel()

@app.get("/estadisticas-actualizacion/")
def obtener_estadisticas_actualizacion():
    """Obtiene estadísticas básicas del sistema de actualización incremental."""
    try:
        stats = grafo.obtener_estadisticas()
        
        return {
            "status": "success",
            "estadisticas": {
                "total_nodos": stats["total_contextos"],
                "total_relaciones": stats["total_relaciones"],
                "relaciones_bidireccionales": stats["relaciones_bidireccionales"],
                "contextos_temporales": stats.get("contextos_temporales", 0),
                "contextos_atemporales": stats.get("contextos_atemporales", 0),
                "tipos_contexto": stats.get("tipos_contexto", {}),
                "actualizacion_incremental": "habilitada",
                "umbral_similitud": parametros_sistema['umbral_similitud'],
                "mensaje": f"Sistema funcionando con {stats['total_contextos']} nodos y {stats['total_relaciones']} relaciones"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/configurar-parametros/")
def configurar_parametros_sistema(config: ConfiguracionParametros):
    """Configura los parámetros principales del sistema."""
    global parametros_sistema
    
    try:
        recalcular_relaciones = False
        
        # Actualizar parámetros si se proporcionan
        if config.umbral_similitud is not None:
            if 0.1 <= config.umbral_similitud <= 0.9:
                # Si cambió el umbral, marcar para recálculo
                if parametros_sistema['umbral_similitud'] != config.umbral_similitud:
                    recalcular_relaciones = True
                
                parametros_sistema['umbral_similitud'] = config.umbral_similitud
                # Actualizar umbral en grafo.py
                grafo.UMBRAL_SIMILITUD = config.umbral_similitud
            else:
                return {"status": "error", "mensaje": "Umbral de similitud debe estar entre 0.1 y 0.9"}
        
        if config.factor_refuerzo_temporal is not None:
            if 0.5 <= config.factor_refuerzo_temporal <= 3.0:
                parametros_sistema['factor_refuerzo_temporal'] = config.factor_refuerzo_temporal
            else:
                return {"status": "error", "mensaje": "Factor de refuerzo temporal debe estar entre 0.5 y 3.0"}
            
        #  VALIDACIÓN DE K_RESULTADOS
        if config.k_resultados is not None:
            if 3 <= config.k_resultados <= 15:
                parametros_sistema['k_resultados'] = config.k_resultados
            else:
                return {"status": "error", "mensaje": "k_resultados debe estar entre 3 y 15"}
        
        # RECALCULAR RELACIONES SI CAMBIÓ EL UMBRAL
        mensaje_recalculo = ""
        if recalcular_relaciones:
            print(f"🔄 Recalculando relaciones con nuevo umbral: {config.umbral_similitud}")
            stats_antes = grafo.obtener_estadisticas()
            grafo._recalcular_relaciones()
            grafo._guardar_grafo()
            stats_despues = grafo.obtener_estadisticas()
            
            mensaje_recalculo = f" | Relaciones recalculadas: {stats_antes['total_relaciones']} → {stats_despues['total_relaciones']}"
        
        return {
            "status": "success",
            "mensaje": f"Parámetros actualizados correctamente{mensaje_recalculo}",
            "parametros": parametros_sistema,
            "relaciones_recalculadas": recalcular_relaciones
        }
        
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

# Nuevo endpoint para forzar recálculo
def forzar_recalculo_relaciones():
    """Fuerza el recálculo de todas las relaciones con los parámetros actuales."""
    try:
        inicio = time.time()
        stats_antes = grafo.obtener_estadisticas()
        print(f"🔄 Iniciando recálculo de relaciones con umbral: {parametros_sistema['umbral_similitud']}")
        
        # Usar la versión optimizada
        resultado_recalculo = grafo._recalcular_relaciones()
        grafo._guardar_grafo_con_propagador()  # Usar versión con propagador
        
        stats_despues = grafo.obtener_estadisticas()
        tiempo_total = time.time() - inicio
        
        return {
            "status": "success",
            "mensaje": "Relaciones recalculadas exitosamente",
            "antes": {
                "nodos": stats_antes["total_contextos"],
                "relaciones": stats_antes["total_relaciones"]
            },
            "despues": {
                "nodos": stats_despues["total_contextos"], 
                "relaciones": stats_despues["total_relaciones"]
            },
            "umbral_aplicado": parametros_sistema['umbral_similitud'],
            "tiempo": f"{tiempo_total:.2f}s",
            "detalles": resultado_recalculo
        }
        
    except Exception as e:
        traceback.print_exc()
        return {"status": "error", "mensaje": str(e)}
    
@app.get("/estado-parametros/")
def obtener_estado_parametros():
    """Obtiene el estado actual de los parámetros del sistema."""
    return {
        "status": "success",
        "parametros": parametros_sistema,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/debug-temporal/")
def debug_analisis_temporal(pregunta: str):
    """Endpoint para debuggear análisis temporal."""
    momento_consulta = datetime.now()
    factor_base = parametros_sistema.get('factor_refuerzo_temporal', 1.5)
    analisis = analizar_temporalidad_con_llm(
        pregunta, 
        momento_consulta, 
        factor_base
    )
    
    return {
        "pregunta": pregunta,
        "momento_consulta": momento_consulta.isoformat(),
        "analisis": analisis,
        "debug": True
    }

@app.post("/conversacion/parse-preview/")
def parsear_conversaciones_preview(entrada: Union[EntradaTextoPlano, EntradaJSON]):
    """Parsea entrada (texto o JSON) y devuelve preview"""
    try:
        processor = TextBatchProcessor()
        
        # Detectar tipo de entrada
        if hasattr(entrada, 'texto') and entrada.texto:
            conversaciones = processor.parse_texto_plano(entrada.texto)
        elif hasattr(entrada, 'json_data') and entrada.json_data:
            conversaciones = processor.parse_json_conversaciones(entrada.json_data)
        else:
            return {"status": "error", "mensaje": "Entrada inválida"}
        
        if not conversaciones:
            return {"status": "error", "mensaje": "No se encontraron conversaciones válidas"}
        
        preview = processor.preparar_preview(conversaciones)
        
        return {
            "status": "preview_listo",
            "preview": preview,
            "conversaciones_parseadas": conversaciones
        }
        
    except ValueError as e:
        return {"status": "error", "mensaje": f"Error de formato: {str(e)}"}
    except Exception as e:
        return {"status": "error", "mensaje": f"Error inesperado: {str(e)}"}

@app.post("/conversacion/procesar-con-metadata/")
def procesar_conversaciones_con_metadata(entrada: ProcesarConMetadata):
    """Procesa y guarda conversaciones con metadatos (detección automática)"""
    # INICIAR MEDICIÓN
    tiempo_inicio = time.time()

    try:
        resultados = {'conversaciones_procesadas': [], 'errores': []}
        metadata_global = entrada.metadata_global or {}
        
        for conv in entrada.conversaciones:
            try:
                # Obtener fecha (global o individual)
                fecha_raw = metadata_global.get('fecha') or conv.get('fecha')
                fecha = None
                if fecha_raw:
                    fecha = normalizar_timestamp_para_guardar(fecha_raw)
                    if not fecha:
                        # Si falla normalización, usar None (conversación atemporal)
                        print(f"⚠️ Fecha inválida para '{conv['titulo']}': {fecha_raw}")
                
                # Detectar participantes del contenido si no están en metadata
                participantes = conv.get('participantes', [])
                if not participantes:
                    # Detección automática básica de participantes
                    # Busca patrones como "Nombre:" al inicio de líneas
                    patron_participantes = r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s]+):'
                    matches = re.findall(patron_participantes, conv['contenido'], re.MULTILINE)
                    participantes = list(set(matches))  # Eliminar duplicados
                
                # Detectar tipo de conversación del contenido
                contenido_lower = conv['contenido'].lower()
                tipo_detectado = 'general'
                
                palabras_clave = {
                    'reunion': ['reunión', 'meeting', 'junta', 'agenda'],
                    'brainstorm': ['brainstorm', 'ideas', 'propuestas', 'creatividad'],
                    'planning': ['planning', 'planificación', 'sprint', 'tareas', 'objetivos'],
                    'entrevista': ['entrevista', 'interview', 'candidato']
                }
                
                for tipo, keywords in palabras_clave.items():
                    if any(kw in contenido_lower for kw in keywords):
                        tipo_detectado = tipo
                        break
                
                # Crear metadata final con detecciones
                metadata_final = {
                    'tipo': tipo_detectado,
                    'participantes_detectados': len(participantes),
                    'origen': conv.get('origen', 'desconocido')
                }
                
                # Agregar conversación
                resultado = grafo.agregar_conversacion(
                    titulo=conv['titulo'],
                    contenido=conv['contenido'],
                    fecha=fecha,
                    participantes=participantes,
                    metadata=metadata_final
                )
                
                resultados['conversaciones_procesadas'].append({
                    'titulo': conv['titulo'],
                    'fragmentos_creados': resultado['total_fragmentos'],
                    'conversacion_id': resultado['conversacion_id'],
                    'tipo_detectado': tipo_detectado,
                    'participantes_detectados': len(participantes)
                })
                
            except Exception as e:
                resultados['errores'].append({
                    'titulo': conv.get('titulo', 'Sin título'),
                    'error': str(e)
                })

        #CALCULAR TIEMPO
        tiempo_fin = time.time()
        tiempo_ms = (tiempo_fin - tiempo_inicio) * 1000
        
        #REGISTRAR MÉTRICA
        total_procesados = len(resultados['conversaciones_procesadas'])
        metricas_sistema.registrar_carga_dataset(
            tipo='conversaciones',
            cantidad=total_procesados,
            tiempo_ms=tiempo_ms,
            detalles={
                "total_fragmentos": sum(c['fragmentos_creados'] for c in resultados['conversaciones_procesadas'])
            }
        )
        
        # Agregar tiempo al response
        resultados['tiempo_procesamiento_ms'] = round(tiempo_ms, 2)
        resultados['tiempo_procesamiento_segundos'] = round(tiempo_ms / 1000, 2)
        
        return {
            "status": "procesado",
            "total_procesadas": len(resultados['conversaciones_procesadas']),
            "total_errores": len(resultados['errores']),
            **resultados
        }
        
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

@app.get("/grafo.html")
async def pagina_grafo():
    """Sirve la página dedicada de visualización de grafos."""
    return FileResponse('static/grafo.html')

@app.get("/grafo.js")
async def script_grafo():
    """Sirve el script JavaScript para la página de grafos."""
    return FileResponse('static/grafo.js')

@app.delete("/api/borrar-todos-datos")
async def borrar_todos_datos():
    """
    Endpoint para borrar todos los datos del sistema:
    """
    try:
        # 1. Reinicializar estructuras globales del grafo
        # Reinicializar grafo y metadatos globales
        modulo_grafo.grafo_contextos = nx.DiGraph()
        modulo_grafo.metadatos_contextos = {}
        modulo_grafo.conversaciones_metadata = {}
        modulo_grafo.fragmentos_metadata = {}
        modulo_grafo.propagador_global = None
        
        # 2. Borrar archivos de datos persistentes
        archivos_a_borrar = [
            "data/grafo_contextos.pickle",
            "data/contexto.json",
            "data/conversaciones.json",
            "data/fragmentos.json",
            "contextos.db"
        ]
        
        for archivo in archivos_a_borrar:
            if os.path.exists(archivo):
                os.remove(archivo)
                print(f"Eliminado: {archivo}")
        
        # 3. Borrar directorio data completo y recrearlo
        if os.path.exists("data"):
            shutil.rmtree("data")
            print("Directorio data eliminado")
        os.makedirs("data", exist_ok=True)
        
        # 4. Limpiar directorio de storage (PDFs)
        storage_dir = os.path.join('static', 'storage')
        if os.path.exists(storage_dir):
            for item in os.listdir(storage_dir):
                item_path = os.path.join(storage_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"Error al borrar {item_path}: {e}")
            print(f"Storage limpiado: {storage_dir}")
        
        # 5. Limpiar colección de ChromaDB (embeddings)
        try:
            # Obtener todos los IDs y borrarlos
            todos_ids = coleccion.get()['ids']
            if todos_ids:
                coleccion.delete(ids=todos_ids)
                print(f"ChromaDB limpiado: {len(todos_ids)} documentos eliminados")
        except Exception as e:
            print(f"Error limpiando ChromaDB: {e}")
        
        # 6. Recrear directorios necesarios
        os.makedirs("data", exist_ok=True)
        os.makedirs(storage_dir, exist_ok=True)
        
        # 7. Reinicializar la variable global 'grafo' en main
        global grafo
        grafo = modulo_grafo  # Mantener referencia al módulo
        print("Sistema completamente reinicializado")
        
        return {
            "status": "success",
            "mensaje": "Todos los datos fueron eliminados exitosamente"
        }
        
    except Exception as e:
        print(f"Error al borrar datos: {str(e)}")
        traceback.print_exc()
        return {
            "status": "error",
            "mensaje": f"Error al borrar datos: {str(e)}"
        }
    
@app.get("/metricas/estadisticas/")
def obtener_estadisticas_performance():
    """Obtiene estadísticas agregadas de performance del sistema"""
    return metricas_sistema.obtener_estadisticas()

@app.get("/metricas/historial/")
def obtener_historial_completo(ultimos: int = 50):
    """Obtiene el historial de métricas (por defecto últimos 50)"""
    historial = metricas_sistema.historial[-ultimos:]
    return {
        "total_registros": len(metricas_sistema.historial),
        "mostrando_ultimos": len(historial),
        "historial": historial
    }

@app.delete("/metricas/limpiar/")
def limpiar_historial_metricas():
    """Limpia el historial de métricas (útil para testing)"""
    metricas_sistema.historial = []
    metricas_sistema._guardar_historial()
    return {"status": "success", "mensaje": "Historial de métricas limpiado"}

# Servir archivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")