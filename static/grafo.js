let networkInstance = null;
let vistaActual = 'macro';
let conversacionesList = {};
let conversacionFiltroSeleccionada = null;

// FUNCIONES DE NOTIFICACIÓN
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

// FUNCIONES DE NAVEGACIÓN
function volverInicio() {
    window.location.href = '/';
}

// GESTIÓN DE VISTAS
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

// CARGA Y VISUALIZACIÓN DEL GRAFO
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
        
        // Actualizar leyenda
        actualizarLeyenda();
        
        // Renderizar grafo
        renderizarGrafo(data);
        
        mostrarNotificacion('Grafo cargado correctamente', 'exito');
        
    } catch (error) {
        console.error('Error cargando grafo:', error);
        container.innerHTML = `<div class="flex items-center justify-center h-full text-red-500"><p>❌ Error al cargar el grafo</p></div>`;
        mostrarNotificacion('Error al cargar el grafo', 'error');
    }
}

function renderizarGrafo(data) {
    const container = document.getElementById('grafoContainer');
    container.innerHTML = '';
    
    const nodes = new vis.DataSet(data.nodes);
    const edges = new vis.DataSet(data.edges);
    
    const options = {
        nodes: {
            shape: 'box',
            margin: 10,
            widthConstraint: { maximum: 200 },
            font: { size: 12, face: 'Arial' },
            shadow: { enabled: true, size: 5 }
        },
        edges: {
            smooth: { type: 'continuous' },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
            font: { size: 10, align: 'middle' }
        },
        physics: {
            enabled: true,
            barnesHut: {
                gravitationalConstant: -8000,
                centralGravity: 0.3,
                springLength: 150,
                springConstant: 0.04
            },
            stabilization: { iterations: 200 }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            navigationButtons: true,
            keyboard: true
        },
        layout: {
            improvedLayout: true
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
}

function actualizarLeyenda() {
    const leyendaContainer = document.getElementById('leyendaContenido');
    
    if (vistaActual === 'macro') {
        leyendaContainer.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                <div>
                    <p class="font-semibold text-blue-800 mb-1">📦 Nodos (Conversaciones):</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <div class="w-4 h-4 rounded" style="background: #dbeafe; border: 2px solid #3b82f6;"></div>
                            <span>Conversación</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-blue-800 mb-1">🔗 Aristas:</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 bg-gray-400 rounded"></div>
                            <span>Relación entre conversaciones</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-blue-800 mb-1">ℹ️ Información:</p>
                    <p class="text-xs">El grosor indica la cantidad de conexiones entre fragmentos</p>
                </div>
            </div>
        `;
    } else {
        // Leyenda para micro
        leyendaContainer.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div>
                    <p class="font-semibold text-purple-800 mb-1">📦 Tipos de Nodos:</p>
                    <div class="grid grid-cols-2 gap-1 text-xs">
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3" style="background: #fff3e0; border: 2px solid #f57c00;"></div>
                            <span>Reunión</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3" style="background: #e8f5e8; border: 2px solid #388e3c;"></div>
                            <span>Tarea</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3" style="background: #fce4ec; border: 2px solid #c2185b;"></div>
                            <span>Evento</span>
                        </div>
                        <div class="flex items-center gap-1">
                            <div class="w-3 h-3" style="background: #ffe4e1; border: 2px solid #ff69b4;"></div>
                            <span>PDF</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p class="font-semibold text-purple-800 mb-1">🔗 Conexiones:</p>
                    <div class="space-y-1 text-xs">
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 bg-green-500 rounded"></div>
                            <span>Con relevancia temporal</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-1 bg-blue-400 rounded"></div>
                            <span>Solo semánticas</span>
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

// INICIALIZACIÓN
document.addEventListener('DOMContentLoaded', function() {
    // Cargar grafo inicial
    cargarGrafo();
    
    // Detectar parámetros URL si se pasa una vista específica
    const urlParams = new URLSearchParams(window.location.search);
    const vistaParam = urlParams.get('vista');
    
    if (vistaParam && ['macro', 'micro', 'micro-filtrada'].includes(vistaParam)) {
        document.getElementById(`vista${vistaParam.charAt(0).toUpperCase() + vistaParam.slice(1).replace('-', '')}`).checked = true;
        cambiarVista(vistaParam);
    }
});