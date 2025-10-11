import os
from typing import Dict, List, Optional
from datetime import datetime
import PyPDF2

def extraer_texto_pdf(pdf_path: str) -> Optional[str]:
    """
    Extrae el texto completo de un archivo PDF.
    Args:
        pdf_path: Ruta del archivo PDF
    Returns:
        Texto extraído o None si hay error
    """
    try:
        texto_completo = []
        
        with open(pdf_path, 'rb') as archivo:
            lector = PyPDF2.PdfReader(archivo)
            num_paginas = len(lector.pages)
            
            for num_pagina in range(num_paginas):
                pagina = lector.pages[num_pagina]
                texto = pagina.extract_text()
                if texto.strip():
                    texto_completo.append(texto)
        
        return "\n\n".join(texto_completo)
    
    except Exception as e:
        print(f"❌ Error al extraer texto del PDF {pdf_path}: {e}")
        return None


def fragmentar_texto_pdf(texto: str, max_palabras: int = 500) -> List[str]:
    """
    Fragmenta el texto extraído del PDF en segmentos manejables.
    Usa la misma lógica que la fragmentación de conversaciones.
    Args:
        texto: Texto completo del PDF
        max_palabras: Máximo de palabras por fragmento
        
    Returns:
        Lista de fragmentos de texto
    """
    if not texto:
        return []
    
    # Dividir en párrafos
    parrafos = texto.split('\n\n')
    fragmentos = []
    fragmento_actual = []
    palabras_actuales = 0
    
    for parrafo in parrafos:
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        
        palabras_parrafo = len(parrafo.split())
        
        # Si el párrafo solo ya excede el límite, dividirlo por oraciones
        if palabras_parrafo > max_palabras:
            oraciones = parrafo.replace('!', '.').replace('?', '.').split('.')
            for oracion in oraciones:
                oracion = oracion.strip()
                if not oracion:
                    continue
                
                palabras_oracion = len(oracion.split())
                
                if palabras_actuales + palabras_oracion > max_palabras:
                    if fragmento_actual:
                        fragmentos.append(' '.join(fragmento_actual))
                        fragmento_actual = []
                        palabras_actuales = 0
                
                fragmento_actual.append(oracion + '.')
                palabras_actuales += palabras_oracion
        else:
            # Agregar párrafo completo
            if palabras_actuales + palabras_parrafo > max_palabras:
                if fragmento_actual:
                    fragmentos.append(' '.join(fragmento_actual))
                    fragmento_actual = []
                    palabras_actuales = 0
            
            fragmento_actual.append(parrafo)
            palabras_actuales += palabras_parrafo
    
    # Agregar último fragmento
    if fragmento_actual:
        fragmentos.append(' '.join(fragmento_actual))
    
    return fragmentos


def crear_attachment_pdf(
    pdf_path: str,
    filename: str,
    conversacion_id: str
) -> Optional[Dict]:
    """
    Procesa un PDF y crea la estructura de attachment.
    Args:
        pdf_path: Ruta del archivo PDF original
        filename: Nombre del archivo
        conversacion_id: ID de la conversación a la que pertenece
    Returns:
        Diccionario con la información del attachment
    """
    try:
        # Extraer texto
        texto_extraido = extraer_texto_pdf(pdf_path)
        if not texto_extraido:
            return None
        
        # Obtener metadata del archivo
        tamaño_bytes = os.path.getsize(pdf_path)
        
        # Crear estructura de attachment
        attachment = {
            'filename': filename,
            'file_path': pdf_path,
            'extracted_text': texto_extraido,
            'metadata': {
                'size_bytes': tamaño_bytes,
                'upload_date': datetime.now().isoformat(),
                'type': 'pdf'
            }
        }
        
        return attachment
    
    except Exception as e:
        print(f"❌ Error al crear attachment PDF: {e}")
        return None


def guardar_pdf_en_storage(
    archivo_bytes: bytes,
    filename: str,
    conversacion_id: str
) -> Optional[str]:
    """
    Guarda el archivo PDF en el directorio de storage.
    Args:
        archivo_bytes: Contenido del archivo en bytes
        filename: Nombre del archivo
        conversacion_id: ID de la conversación
    Returns:
        Ruta donde se guardó el archivo o None si hay error
    """
    try:
        # Crear directorio para la conversación
        directorio = f"storage/documents/{conversacion_id}"
        os.makedirs(directorio, exist_ok=True)
        
        # Ruta completa del archivo
        ruta_archivo = os.path.join(directorio, filename)
        
        # Guardar archivo
        with open(ruta_archivo, 'wb') as f:
            f.write(archivo_bytes)
        
        print(f"PDF guardado en: {ruta_archivo}")
        return ruta_archivo
    
    except Exception as e:
        print(f"Error al guardar PDF: {e}")
        return None