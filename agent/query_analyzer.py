# agent/query_analyzer.py 
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from agent.temporal_parser import extraer_referencias_del_texto, parsear_referencia_temporal
import re
from agent.utils import parse_iso_datetime_safe

class IntentionTemporalDetector:
    """Detecta la intención temporal en consultas del usuario con contexto de momento."""
    PATRONES_TEMPORALES = [
        # Patrones básicos más flexibles
        r'\b(ayer|hoy|manana)\b',
        r'\b(que|como|cuando)\s+.*\s+(ayer|hoy|manana)\b',
        r'\b(ayer|hoy|manana)\s+.*\s+(que|como|paso|hicimos|tengo|hay)\b',
        # Patrones con variaciones de escritura
        r'\bq\s+.*\s+(ayer|hoy|manana)\b',
        r'\b(ayer|hoy|manana)\s+.*\bq\b',
        # Patrones más específicos
        r'\b(hicimos|paso|sucedio|ocurrio)\s+ayer\b',
        r'\bayer\s+(hicimos|paso|sucedio|ocurrio)\b',
        r'\b(tengo|hay|pasa)\s+(hoy|manana)\b',
        r'\b(hoy|manana)\s+(tengo|hay|pasa)\b',
        # Patrones de planificación
        r'\bpara\s+(hoy|manana|ayer)\b',
        r'\b(programado|planeado|agendado)\s+(hoy|manana|ayer)\b'
    ]
    
    PALABRAS_TEMPORALES = [
        'reciente', 'actual', 'pendiente', 'proximo', 'futuro', 
        'pasado', 'ahora', 'hoy', 'manana', 'ayer', 'semana', 'mes',  # SIN TILDES
        'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo',
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ]
    
    PATRONES_ESTRUCTURALES = [
        r'\b(como) .*(funciona|hacer)\b',  # Sin tildes después de normalización
        r'\b(que) .*(significa|concepto)\b',
        r'\b(cual) .*(diferencia|ventaja)\b',
        r'\b(donde) .*(encuentra|esta)\b',
    ]

    def _normalizar_pregunta(self, pregunta: str) -> str:
        """Normaliza pregunta para manejar cualquier variación del usuario."""
        # 1. Limpiar signos de puntuación completamente
        normalizada = re.sub(r'[¿?¡!.,;:()"\'-]', ' ', pregunta.lower().strip())
        
        # 2. Normalizar espacios múltiples 
        normalizada = re.sub(r'\s+', ' ', normalizada)
        
        # 3. Normalizar acentos y caracteres especiales
        reemplazos = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u', 'ç': 'c'
        }
        for original, reemplazo in reemplazos.items():
            normalizada = normalizada.replace(original, reemplazo)
        
        # 4. Manejar variaciones comunes
        variaciones = {
            'q ': 'que ', 'xq': 'porque', 'pq': 'porque',
            'tmb': 'tambien', 'tb': 'tambien',
            'manyana': 'manana', 'mañana': 'manana'
        }
        for variacion, correccion in variaciones.items():
            normalizada = normalizada.replace(variacion, correccion)
        
        return normalizada.strip()
    
    def _resolver_referencias_contextuales(self, pregunta: str, momento_consulta: datetime) -> Optional[str]:
        """Resuelve referencias temporales relativas al momento de la consulta."""
        referencias = extraer_referencias_del_texto(pregunta)
        
        if not referencias:
            # Intentar parsing manual para casos no cubiertos
            return self._parsing_manual_referencias(pregunta, momento_consulta)
        
        # Tomar la primera referencia encontrada
        ref_texto, timestamp_base, tipo = referencias[0]
        
        # Si ya es una fecha absoluta, la devolvemos
        if tipo == "fecha_exacta":
            return timestamp_base
        
        # Para referencias relativas, recalcular desde momento_consulta
        timestamp_contextual, _ = parsear_referencia_temporal(ref_texto, momento_consulta)
        
        return timestamp_contextual
    
    def _parsing_manual_referencias(self, pregunta: str, momento_consulta: datetime) -> Optional[str]:
        """Parsing manual para referencias temporales complejas."""
        pregunta_lower = pregunta.lower()
        
        # Días de la semana específicos
        dias_semana = {
            'lunes': 0, 'martes': 1, 'miércoles': 2, 'jueves': 3,
            'viernes': 4, 'sábado': 5, 'domingo': 6
        }
        
        for dia, numero_dia in dias_semana.items():
            if dia in pregunta_lower:
                # Buscar el día más cercano (anterior o siguiente)
                dias_hasta = (numero_dia - momento_consulta.weekday()) % 7
                if dias_hasta == 0:  # Es hoy
                    fecha_objetivo = momento_consulta
                else:
                    # Si menciona "el lunes" probablemente se refiere al lunes más cercano
                    fecha_objetivo = momento_consulta + timedelta(days=dias_hasta)
                return fecha_objetivo.isoformat()
        
        # Meses específicos
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        for mes_nombre, mes_numero in meses.items():
            if mes_nombre in pregunta_lower:
                # Asumir el año actual o siguiente si ya pasó
                año = momento_consulta.year
                if mes_numero < momento_consulta.month:
                    año += 1
                fecha_objetivo = datetime(año, mes_numero, 1)
                return fecha_objetivo.isoformat()
        
        return None
    
    def _calcular_ventana_temporal(self, intencion: str, referencia_temporal: Optional[str], 
                        pregunta_original: str) -> Tuple[Optional[str], Optional[str]]:
        """MEJORADO: Calcula ventana temporal según intención y tipo de consulta."""
        if not referencia_temporal:
            return None, None

        try:
            # USAR EL PARSER MEJORADO
            fecha_ref = parse_iso_datetime_safe(referencia_temporal)
            if not fecha_ref:
                print(f"Error parseando referencia temporal: {referencia_temporal}")
                return None, None
        except Exception as e:
            print(f"Error en cálculo temporal: {e}")
            return None, None
        
        pregunta_lower = pregunta_original.lower()
        
        # DEBUG: Mostrar fecha de referencia
        print(f"Fecha de referencia para consulta: {fecha_ref.strftime('%d/%m/%Y %H:%M')}")
        
        # VENTANAS ESPECÍFICAS POR TIPO DE CONSULTA
        if "ayer" in pregunta_lower:
            # SOLO el día anterior - SIN expandir a "hoy"
            fecha_ayer = fecha_ref - timedelta(days=1)
            inicio_dia = fecha_ayer.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = fecha_ayer.replace(hour=23, minute=59, second=59, microsecond=999999)
            return inicio_dia.isoformat(), fin_dia.isoformat()
    
        elif "hoy" in pregunta_lower:
            # SOLO el día actual
            inicio_dia = fecha_ref.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = fecha_ref.replace(hour=23, minute=59, second=59, microsecond=999999)
            return inicio_dia.isoformat(), fin_dia.isoformat()
        
        elif any(palabra in pregunta_lower for palabra in ["mañana", "manana"]):  # Ambas versiones
            # Para "mañana", crear ventana del día siguiente completo
            fecha_manana = fecha_ref + timedelta(days=1)
            inicio_dia = fecha_manana.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = fecha_manana.replace(hour=23, minute=59, second=59, microsecond=999999)
            print(f"Ventana para 'mañana': {inicio_dia.strftime('%d/%m %H:%M')} a {fin_dia.strftime('%d/%m %H:%M')}")
            return inicio_dia.isoformat(), fin_dia.isoformat()
        
        elif "semana pasada" in pregunta_lower or "la semana anterior" in pregunta_lower:
            # Calcular inicio de semana pasada (lunes)
            dias_desde_lunes = fecha_ref.weekday()
            inicio_semana_actual = fecha_ref - timedelta(days=dias_desde_lunes)
            inicio_semana_pasada = inicio_semana_actual - timedelta(days=7)
            fin_semana_pasada = inicio_semana_pasada + timedelta(days=6)
            return inicio_semana_pasada.isoformat(), fin_semana_pasada.isoformat()
        
        elif "esta semana" in pregunta_lower or "semana actual" in pregunta_lower:
            dias_desde_lunes = fecha_ref.weekday()
            inicio_semana = fecha_ref - timedelta(days=dias_desde_lunes)
            fin_semana = inicio_semana + timedelta(days=6)
            return inicio_semana.isoformat(), fin_semana.isoformat()
        
        elif "este mes" in pregunta_lower or "mes actual" in pregunta_lower:
            inicio_mes = fecha_ref.replace(day=1)
            # Calcular último día del mes
            if fecha_ref.month == 12:
                fin_mes = fecha_ref.replace(year=fecha_ref.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                fin_mes = fecha_ref.replace(month=fecha_ref.month + 1, day=1) - timedelta(days=1)
            return inicio_mes.isoformat(), fin_mes.isoformat()
        
        elif "mes pasado" in pregunta_lower or "mes anterior" in pregunta_lower:
            if fecha_ref.month == 1:
                inicio_mes_pasado = fecha_ref.replace(year=fecha_ref.year - 1, month=12, day=1)
                fin_mes_pasado = fecha_ref.replace(day=1) - timedelta(days=1)
            else:
                inicio_mes_pasado = fecha_ref.replace(month=fecha_ref.month - 1, day=1)
                fin_mes_pasado = fecha_ref.replace(day=1) - timedelta(days=1)
            return inicio_mes_pasado.isoformat(), fin_mes_pasado.isoformat()
        
        elif any(dia in pregunta_lower for dia in ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']):
            # Para días específicos, ventana del día completo
            inicio_dia = fecha_ref.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = fecha_ref.replace(hour=23, minute=59, second=59, microsecond=999999)
            return inicio_dia.isoformat(), fin_dia.isoformat()
        
        # VENTANAS POR INTENSIDAD DE INTENCIÓN (fallback)
        elif intencion == 'fuerte':
            # Búsqueda precisa: ±1 día
            inicio = (fecha_ref - timedelta(days=1)).isoformat()
            fin = (fecha_ref + timedelta(days=1)).isoformat()
            return inicio, fin
        elif intencion == 'media':
            # Búsqueda amplia: ±3 días
            inicio = (fecha_ref - timedelta(days=3)).isoformat()
            fin = (fecha_ref + timedelta(days=3)).isoformat()
            return inicio, fin
        
        return None, None
    
    def analizar_intencion(self, pregunta: str, momento_consulta: Optional[datetime] = None) -> Dict:
        """Analiza la intención temporal considerando el momento de consulta."""
        if momento_consulta is None:
            momento_consulta = datetime.now()
        
        # NORMALIZACIÓN MEJORADA DE LA PREGUNTA
        pregunta_normalizada = self._normalizar_pregunta(pregunta)
        
        print(f"Pregunta original: '{pregunta}'")
        print(f"Pregunta normalizada: '{pregunta_normalizada}'")
        
        # 1. Resolver referencia temporal contextual
        referencia_contextual = self._resolver_referencias_contextuales(pregunta, momento_consulta)
        
        # 2. Temporal fuerte: patrones explícitos
        for patron in self.PATRONES_TEMPORALES:
            if re.search(patron, pregunta_normalizada):
                print(f"Patrón temporal detectado: {patron}")
                ventana_inicio, ventana_fin = self._calcular_ventana_temporal(
                    'fuerte', referencia_contextual, pregunta
                )
                
                # Obtener factor base desde configuración
                try:
                    import main
                    factor_base = main.parametros_sistema.get('factor_refuerzo_temporal', 1.5)
                except:
                    factor_base = 1.5

                factor_refuerzo = self._calcular_factor_refuerzo(pregunta_normalizada, factor_base)
                
                return self._crear_respuesta(
                    'fuerte', 0.9, factor_refuerzo, 
                    f'Patrón temporal detectado | Momento consulta: {momento_consulta.strftime("%d/%m %H:%M")}',
                    referencia_contextual,
                    momento_consulta.isoformat(),
                    ventana_inicio,
                    ventana_fin
                )
        
        # 3. Referencias encontradas
        if referencia_contextual:
            ventana_inicio, ventana_fin = self._calcular_ventana_temporal(
                'fuerte', referencia_contextual, pregunta
            )
            factor_refuerzo = self._calcular_factor_refuerzo(pregunta_normalizada)
            
            return self._crear_respuesta(
                'fuerte', 0.95, factor_refuerzo, 
                f'Referencia temporal contextual | Consultado: {momento_consulta.strftime("%d/%m %H:%M")}',
                referencia_contextual,
                momento_consulta.isoformat(),
                ventana_inicio,
                ventana_fin
            )
        
        # 4. Temporal medio: palabras relacionadas
        palabras_encontradas = [p for p in self.PALABRAS_TEMPORALES if p in pregunta_normalizada]
        if palabras_encontradas:
            print(f"Palabras temporales encontradas: {palabras_encontradas}")
            return self._crear_respuesta(
                'media', 0.6, 1.5, 
                f'Palabras temporales: {", ".join(palabras_encontradas)} | Contexto: {momento_consulta.strftime("%d/%m %H:%M")}',
                momento_consulta.isoformat(),
                momento_consulta.isoformat()
            )
        
        # 5. Estructural: patrones no temporales
        for patron in self.PATRONES_ESTRUCTURALES:
            if re.search(patron, pregunta_normalizada):
                return self._crear_respuesta(
                    'nula', 0.8, 0.2, 
                    'Consulta estructural detectada',
                    None,
                    momento_consulta.isoformat()
                )
        
        # 6. Default: débil
        return self._crear_respuesta(
            'debil', 0.3, 1.0, 
            'Sin indicadores temporales claros',
            None,
            momento_consulta.isoformat()
        )
    
    def _calcular_factor_refuerzo(self, pregunta_lower: str, factor_base: float = 1.5) -> float:
        """Calcula multiplicador sobre el factor base configurado."""
        if any(palabra in pregunta_lower for palabra in ['hoy', 'ahora', 'actual']):
            return factor_base * 2.0  # 2x el valor configurado
        elif any(palabra in pregunta_lower for palabra in ['manana', 'ayer']):
            return factor_base * 1.5  # 1.5x el valor configurado
        elif any(palabra in pregunta_lower for palabra in ['semana', 'mes']):
            return factor_base * 1.2  # 1.2x el valor configurado
        else:
            return factor_base  # Usar tal como está configurado
    
    def _crear_respuesta(self, intencion, confianza, factor, explicacion, 
                        timestamp=None, momento_consulta=None, 
                        ventana_inicio=None, ventana_fin=None):
        """Helper para crear respuesta consistente con contexto temporal."""
        respuesta = {
            'intencion_temporal': intencion,
            'confianza': confianza,
            'factor_refuerzo_temporal': factor,
            'timestamp_referencia': timestamp,
            'momento_consulta': momento_consulta or datetime.now().isoformat(),
            'explicacion': explicacion
        }
        
        # Agregar ventana temporal si existe
        if ventana_inicio and ventana_fin:
            respuesta['ventana_temporal'] = {
                'inicio': ventana_inicio,
                'fin': ventana_fin
            }
        
        return respuesta

# Instancia global
detector = IntentionTemporalDetector()

def analizar_intencion_temporal(pregunta: str, momento_consulta: Optional[datetime] = None) -> Dict:
    """Función principal para analizar intención temporal con contexto."""
    return detector.analizar_intencion(pregunta, momento_consulta)

