// Variables globales
let networkInstance = null;
let vistaActual = 'macro';
let conversacionesList = {};
let conversacionFiltroSeleccionada = null;

// ============================================
// PALETA DE COLORES MEJORADA
// ============================================

const coloresTipoContexto = {
    'reunion': {
        temporal: { bg: '#FF6B6B', border: '#C92A2A' },      // Rojo vibrante
        atemporal: { bg: '#FFD1D1', border: '#FFA8A8' }      // Rosa pálido
    },
    'tarea': {
        temporal: { bg: '#4ECDC4', border: '#0B7A75' },      // Turquesa
        atemporal: { bg: '#D4F1EE', border: '#A8E6E3' }      // Turquesa pálido
    },
    'evento': {
        temporal: { bg: '#FFD93D', border: '#F59F00' },      // Amarillo oro
        atemporal: { bg: '#FFF4CC', border: '#FFE066' }      // Amarillo pálido
    },
    'proyecto': {
        temporal: { bg: '#A29BFE', border: '#6C5CE7' },      // Púrpura
        atemporal: { bg: '#E5E3FF', border: '#C5C2FF' }      // Lila pálido
    },
    'conocimiento': {
        temporal: { bg: '#74B9FF', border: '#0984E3' },      // Azul cielo
        atemporal: { bg: '#D9EEFF', border: '#B2D7FF' }      // Azul muy pálido
    },
    'conversacion': {
        temporal: { bg: '#95A5A6', border: '#7F8C8D' },      // Gris medio
        atemporal: { bg: '#E8ECED', border: '#BDC3C7' }      // Gris muy claro
    },
    'general': {
        temporal: { bg: '#B2BEC3', border: '#636E72' },      // Gris medio oscuro
        atemporal: { bg: '#F0F3F5', border: '#DFE6E9' }      // Gris claro
    },
    'documento': {
        temporal: { bg: '#FF85C0', border: '#E056A3' },      // Rosa fucsia
        atemporal: { bg: '#FFE4F0', border: '#FFC2E0' }      // Rosa chicle
    }
};

// ============================================
// FUNCIONES DE NOTIFICACIÓN
// ============================================

function mostrarNotificacion(mensaje, tipo = 'info', duracion = 4000) {
    const colores = {
        error: 'bg-red-500',
        exito: 'bg-green-500',
        info: 'bg-blue-500',
        warning: 'bg-orange-500'
    };
    
    const toast = document.createElement('div');
    toast.className = `${colores[tipo]} text-white px-6 py-3 rounded-lg shadow-lg mb-2 animate-fade-in`;
    toast.textContent = mensaje;
    
    document.getElementById('notificaciones').appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duracion);
}

// ============================================
// FUNCIONES DE NAVEGACIÓN
// ============================================

function volverInicio() {
    window.location.href = '/';
}

// ============================================
// GESTIÓN DE VISTAS
// ============================================

function cambiarVista(nuevaVista) {
    vistaActual = nuevaVista;
    
    // Mostrar/ocultar selector de conversación
    const selector = document.getElementById('selectorConversacion');
    if (nuevaVista === 'micro-filtrada') {
        selector.classList.remove('hidden');
        if (Object.keys(conversacionesList).length === 0) {
            cargarListaConversaciones();
        }
    } else {
        selector.classList.add('hidden');
        conversacionFiltroSeleccionada = null;
    }
    
    actualizarTituloVista();
    cargarGrafo();
}

function actualizarTituloVista() {
    const titulos = {
        'macro': '🌍 Vista Macro - Conversaciones',
        'micro': '🔬 Vista Micro - Fragmentos Completa',
        'micro-filtrada': '🎯 Vista Micro - Fragmentos Filtrada'
    };
    
    const descripciones = {
        'macro': 'Cada nodo representa una conversación completa',
        'micro': 'Cada nodo representa un fragmento individual',
        'micro-filtrada': 'Fragmentos de una conversación específica'
    };
    
    document.getElementById('tituloVista').textContent = titulos[vistaActual] || titulos['macro'];
    document.getElementById('descripcionVista').textContent = descripciones[vistaActual] || descripciones['macro'];
}

async function cargarListaConversaciones() {
    try {
        const res = await axios.get('/conversaciones/');
        conversacionesList = res.data;
        
        const selector = document.getElementById('conversacionFiltro');
        selector.innerHTML = '<option value="">Seleccionar conversación...</option>';
        
        for (const [id, datos] of Object.entries(conversacionesList)) {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${datos.titulo} (${datos.total_fragmentos} fragmentos)`;
            selector.appendChild(option);
        }
    } catch (error) {
        console.error('Error cargando conversaciones:', error);
        mostrarNotificacion('Error al cargar lista de conversaciones', 'error');
    }
}

function aplicarFiltroConversacion() {
    const selector = document.getElementById('conversacionFiltro');
    conversacionFiltroSeleccionada = selector.value;
    
    if (conversacionFiltroSeleccionada) {
        const nombreConv = selector.options[selector.selectedIndex].text;
        document.getElementById('descripcionVista').textContent = `Fragmentos de: ${nombreConv}`;
        cargarGrafo();
    } else {
        mostrarNotificacion('Selecciona una conversación para filtrar', 'warning');
    }
}

// ============================================
// PROCESAMIENTO DE NODOS CON COLORES MEJORADOS
// ============================================

function procesarNodos(nodos, vista) {
    return nodos.map(node => {
        const esPDF = node.es_pdf || node.tipo_contexto === 'documento';
        const esTemporal = node.group === 'temporal' || node.es_temporal;
        const tipo = node.tipo_contexto || 'general';
        
        // Obtener colores según tipo y temporalidad
        const coloresBase = coloresTipoContexto[tipo] || coloresTipoContexto['general'];
        const colores = esTemporal ? coloresBase.temporal : coloresBase.atemporal;
        
        // Emoji indicador de temporalidad
        const emojiTemporal = esTemporal ? '🕐 ' : '📋 ';
        const labelOriginal = node.label || node.titulo || node.id;
        
        if (vista === 'macro') {
            // VISTA MACRO: Nodos más grandes, variables según fragmentos
            return {
                ...node,
                label: `${emojiTemporal}${labelOriginal}`,
                color: {
                    background: colores.bg,
                    border: colores.border
                },
                borderWidth: esTemporal ? 3 : 1.5,
                size: Math.max(25, Math.min(75, (node.total_fragmentos || 1) * 2.5)),
                shape: 'box',
                font: {
                    size: 13,
                    bold: true,
                    color: '#1a1a1a'
                },
                shadow: {
                    enabled: true,
                    size: 8,
                    x: 3,
                    y: 3,
                    color: 'rgba(0,0,0,0.2)'
                },
                margin: 10,
                shapeProperties: {
                    borderRadius: 8
                }
            };
        } else {
            // VISTA MICRO: Nodos uniformes y compactos
            return {
                ...node,
                label: `${emojiTemporal}${labelOriginal}`,
                color: {
                    background: colores.bg,
                    border: colores.border
                },
                borderWidth: esTemporal ? 2.5 : 1.5,
                size: 18,
                shape: 'box',
                font: {
                    size: 10,
                    color: '#2c2c2c'
                },
                shadow: {
                    enabled: true,
                    size: 4,
                    x: 1,
                    y: 1,
                    color: 'rgba(0,0,0,0.15)'
                },
                margin: 8,
                shapeProperties: {
                    borderRadius: 4
                }
            };
        }
    });
}

// ============================================
// PROCESAMIENTO DE ARISTAS CON COLORES MEJORADOS
// ============================================

function procesarAristas(aristas, vista) {
    return aristas.map(edge => {
        const relevanciaTemp = edge.relevancia_temporal || 0;
        const pesoEfectivo = edge.peso_efectivo || edge.weight || 0;
        
        // SISTEMA DE COLORES POR FUERZA DE RELACIÓN
        let color, width, dashes;
        
        if (relevanciaTemp > 0.5) {
            // Alta relevancia temporal - Verde fuerte
            color = '#2ECC71';
            width = Math.max(3, pesoEfectivo * 5);
            dashes = false;
        } else if (relevanciaTemp > 0.3) {
            // Media relevancia temporal - Naranja
            color = '#F39C12';
            width = Math.max(2, pesoEfectivo * 4);
            dashes = false;
        } else if (pesoEfectivo > 0.1) {
            // Solo semántica - Azul
            color = '#3498DB';
            width = Math.max(1.5, pesoEfectivo * 3);
            dashes = false;
        } else {
            // Muy débil - Gris punteado
            color = '#95A5A6';
            width = 1;
            dashes = [5, 5];
        }
        
        // LABELS DIFERENCIADOS POR VISTA
        let label = '';
        let tooltip = '';
        
        if (vista === 'macro') {
            // VISTA MACRO: Mostrar información agregada de conversaciones
            const pesoTotal = edge.peso_total || pesoEfectivo;
            const conexiones = edge.conexiones_fragmentos || 1;
            label = `${pesoTotal.toFixed(2)} | ${conexiones}`;
            
            // Tooltip para vista macro
            tooltip = `🔗 Conexión entre conversaciones
━━━━━━━━━━━━━━━━━━━━━━
📊 Peso total: ${pesoTotal.toFixed(3)}
🔢 Fragmentos conectados: ${conexiones}
💪 Peso promedio: ${(pesoTotal / conexiones).toFixed(3)}
━━━━━━━━━━━━━━━━━━━━━━
Tipo: ${relevanciaTemp > 0.3 ? 'Temporal' : 'Semántica'}`;
            
        } else {
            // VISTA MICRO: Mostrar peso efectivo si es significativo
            if (pesoEfectivo > 0.3) {
                label = pesoEfectivo.toFixed(2);
            }
            
            // Tooltip para vista micro
            tooltip = `🔗 Conexión entre fragmentos
━━━━━━━━━━━━━━━━━━━━━━
💪 Peso estructural: ${(edge.peso_estructural || 0).toFixed(3)}
⏰ Relevancia temporal: ${relevanciaTemp.toFixed(3)}
⚡ Peso efectivo: ${pesoEfectivo.toFixed(3)}
━━━━━━━━━━━━━━━━━━━━━━
Tipo: ${relevanciaTemp > 0.3 ? 'Temporal' : 'Semántica'}`;
        }
        
        return {
            from: edge.from,
            to: edge.to,
            label: label,
            title: tooltip,
            color: {
                color: color,
                highlight: color,
                hover: color,
                opacity: 0.8
            },
            width: width,
            dashes: dashes,
            arrows: {
                to: { enabled: false },
                from: { enabled: false }
            },
            smooth: {
                enabled: true,
                type: 'curvedCW',
                roundness: dashes ? 0.3 : 0.2
            },
            font: {
                size: vista === 'macro' ? 11 : 9,
                background: 'rgba(255,255,255,0.85)',
                strokeWidth: 0
            },
            selectionWidth: 2,
            hoverWidth: 0.5
        };
    });
}

// ============================================
// CARGA Y VISUALIZACIÓN DEL GRAFO
// ============================================

async function cargarGrafo() {
    const container = document.getElementById('grafoContainer');
    container.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><p class="text-lg">⏳ Cargando grafo...</p></div>';
    
    try {
        let url = '';
        
        switch(vistaActual) {
            case 'macro':
                url = '/grafo/macro/conversaciones/';
                break;
            case 'micro':
                url = '/grafo/micro/fragmentos/';
                break;
            case 'micro-filtrada':
                if (!conversacionFiltroSeleccionada) {
                    container.innerHTML = '<div class="flex items-center justify-center h-full text-orange-500"><p>⚠️ Selecciona una conversación para visualizar</p></div>';
                    return;
                }
                url = `/grafo/micro/conversacion/${conversacionFiltroSeleccionada}`;
                break;
        }
        
        const response = await axios.get(url);
        const data = response.data;
        
        if (!data.nodes || data.nodes.length === 0) {
            container.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><p>📭 No hay datos para visualizar</p></div>';
            return;
        }
        
        // Actualizar estadísticas
        document.getElementById('totalNodos').textContent = data.nodes.length;
        document.getElementById('totalAristas').textContent = data.edges.length;
        
        // Procesar y renderizar
        const nodosProcesados = procesarNodos(data.nodes, vistaActual);
        const aristasProcesadas = procesarAristas(data.edges, vistaActual);
        
        // Actualizar leyenda
        actualizarLeyenda();
        
        // Renderizar grafo
        renderizarGrafo(nodosProcesados, aristasProcesadas);
        
        mostrarNotificacion('Grafo cargado correctamente', 'exito');
        
    } catch (error) {
        console.error('Error cargando grafo:', error);
        container.innerHTML = `<div class="flex items-center justify-center h-full text-red-500"><p>❌ Error al cargar el grafo</p></div>`;
        mostrarNotificacion('Error al cargar el grafo', 'error');
    }
}

function renderizarGrafo(nodos, aristas) {
    const container = document.getElementById('grafoContainer');
    container.innerHTML = '';
    
    const nodes = new vis.DataSet(nodos);
    const edges = new vis.DataSet(aristas);
    
    const options = {
        nodes: {
            shape: 'box',
            widthConstraint: { maximum: 200 }
        },
        edges: {
            labelHighlightBold: false,
            selectionWidth: 3
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -8000,
                centralGravity: 0.3,
                springLength: vistaActual === 'macro' ? 180 : 150,
                springConstant: 0.04,
                damping: 0.5,
                avoidOverlap: 0.2
            },
            stabilization: {
                enabled: true,
                iterations: 300,
                updateInterval: 50
            },
            minVelocity: 0.75
        },
        interaction: {
            hover: true,
            tooltipDelay: 150,
            navigationButtons: true,
            keyboard: {
                enabled: true,
                bindToWindow: false
            },
            zoomView: true,
            dragView: true,
            multiselect: true
        },
        layout: {
            improvedLayout: vistaActual === 'macro',
            randomSeed: vistaActual === 'macro' ? 42 : undefined
        }
    };
    
    networkInstance = new vis.Network(container, { nodes, edges }, options);
    
    // Eventos de interacción
    networkInstance.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const nodeData = nodes.get(nodeId);
            console.log('Nodo seleccionado:', nodeData);
        }
    });
    
    networkInstance.on('stabilizationIterationsDone', function() {
        networkInstance.setOptions({ physics: false });
    });
    
    // Fit después de estabilización
    setTimeout(() => {
        if (networkInstance) {
            networkInstance.fit({
                animation: {
                    duration: 500,
                    easingFunction: 'easeInOutQuad'
                }
            });
        }
    }, 100);
}

function actualizarLeyenda() {
    const leyendaContainer = document.getElementById('leyendaContenido');
    
    if (vistaActual === 'macro') {
        leyendaContainer.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div>
                    <p class="font-semibold text-blue-800 mb-2">📦 Nodos (Conversaciones):</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #FF6B6B; border: 2px solid #C92A2A;"></div>
                            <span>Reunión</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #4ECDC4; border: 2px solid #0B7A75;"></div>
                            <span>Tarea</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #FFD93D; border: 2px solid #F59F00;"></div>
                            <span>Evento</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #FF85C0; border: 2px solid #E056A3;"></div>
                            <span>PDF</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #95A5A6; border: 2px solid #7F8C8D;"></div>
                            <span>Conversación general</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-blue-800 mb-2">🔗 Aristas:</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 rounded" style="background: #2ECC71;"></div>
                            <span>Temporal fuerte (>0.5)</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 rounded" style="background: #F39C12;"></div>
                            <span>Temporal media (0.3-0.5)</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 rounded" style="background: #3498DB;"></div>
                            <span>Solo semántica</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-blue-800 mb-2">🎨 Saturación:</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #FF6B6B; border: 3px solid #C92A2A;"></div>
                            <span>Temporal (vibrante)</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #FFD1D1; border: 1.5px solid #FFA8A8;"></div>
                            <span>Atemporal (suave)</span>
                        </div>
                    </div>
                    <p class="text-xs text-gray-600 mt-2">
                        Grosor = # conexiones
                    </p>
                </div>
            </div>
        `;
    } else {
        leyendaContainer.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div>
                    <p class="font-semibold text-purple-800 mb-2">📦 Tipos de Fragmentos:</p>
                    <div class="grid grid-cols-2 gap-1 text-xs">
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3 rounded" style="background: #FF6B6B; border: 2px solid #C92A2A;"></div>
                            <span>Reunión</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3 rounded" style="background: #4ECDC4; border: 2px solid #0B7A75;"></div>
                            <span>Tarea</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3 rounded" style="background: #FFD93D; border: 2px solid #F59F00;"></div>
                            <span>Evento</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3 rounded" style="background: #FF85C0; border: 2px solid #E056A3;"></div>
                            <span>PDF</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3 rounded" style="background: #95A5A6; border: 2px solid #7F8C8D;"></div>
                            <span>Conversación</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-purple-800 mb-2">🔗 Conexiones:</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 rounded" style="background: #2ECC71;"></div>
                            <span>Verde = Temporal fuerte</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 rounded" style="background: #F39C12;"></div>
                            <span>Naranja = Temporal media</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 rounded" style="background: #3498DB;"></div>
                            <span>Azul = Semántica</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 rounded" style="background: #95A5A6; border-top: 1px dashed #7F8C8D;"></div>
                            <span>Gris = Muy débil</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-purple-800 mb-2">ℹ️ Indicadores:</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <span class="font-bold">🕐</span>
                            <span>= Temporal</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="font-bold">📋</span>
                            <span>= Atemporal</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

function actualizarGrafo() {
    cargarGrafo();
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Cargar grafo inicial
    cargarGrafo();
    
    // Detectar parámetros URL si se pasa una vista específica
    const urlParams = new URLSearchParams(window.location.search);
    const vistaParam = urlParams.get('vista');
    
    if (vistaParam && ['macro', 'micro', 'micro-filtrada'].includes(vistaParam)) {
        const radioId = `vista${vistaParam.charAt(0).toUpperCase() + vistaParam.slice(1).replace('-', '')}`;
        const radio = document.getElementById(radioId);
        if (radio) {
            radio.checked = true;
            cambiarVista(vistaParam);
        }
    }
});