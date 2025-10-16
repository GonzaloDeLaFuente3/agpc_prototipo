// Variables globales
let ultimaRespuesta = "";
let ultimaPregunta = "";
let ultimoSubgrafo = null;
let propagacionHabilitada = true;
let parametrosPropagacion = {
    factor_decaimiento: 0.8,
    umbral_activacion: 0.01,
    max_pasos: 3
};
let umbralSimilitud = 0.5;
let factorRefuerzoTemporal = 1.5;
let conversacionesParseadas = null;
let tipoEntradaActual = 'texto';

// SISTEMA UNIFICADO DE NOTIFICACIONES
function mostrarNotificacion(mensaje, tipo = 'error', duracion = 5000) {
    const clases = {
        error: 'bg-red-500',
        exito: 'bg-green-500',
        info: 'bg-blue-500',
        warning: 'bg-orange-500'
    };
    
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 ${clases[tipo]} text-white px-6 py-3 rounded-lg shadow-lg z-50`;
    toast.textContent = mensaje;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), duracion);
}

// SISTEMA UNIFICADO DE MODALES
function gestionarModal(modalId, accion, contenido = null) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    switch(accion) {
        case 'abrir':
            modal.classList.remove('hidden');
            if (contenido) {
                const contenedorContenido = modal.querySelector('[id$="Contenido"], #grafo, #arbolConsulta');
                if (contenedorContenido) contenedorContenido.innerHTML = contenido;
            }
            break;
        case 'cerrar':
            modal.classList.add('hidden');
            break;
    }
}

// SISTEMA UNIFICADO DE PARÁMETROS
const configuracionesParametros = {
    umbral: { 
        url: '/configurar-parametros/', 
        payload: () => ({ 
            umbral_similitud: umbralSimilitud, 
            factor_refuerzo_temporal: factorRefuerzoTemporal 
        }),
        onSuccess: (data) => {
            if (data.relaciones_recalculadas) {
                setTimeout(() => mostrarNotificacion(`Grafo actualizado con nuevo umbral! ${data.mensaje}`, 'info'), 500);
            }
        }
    },
    propagacion: { 
        url: '/configurar-propagacion/', 
        payload: () => ({}),
        params: () => ({
            factor_decaimiento: parametrosPropagacion.factor_decaimiento,
            umbral_activacion: parametrosPropagacion.umbral_activacion
        }),
        onSuccess: (data) => {
            parametrosPropagacion.factor_decaimiento = data.factor_decaimiento;
            parametrosPropagacion.umbral_activacion = data.umbral_activacion;
            obtenerEstadoPropagacion();
        }
    }
};

async function aplicarConfiguracion(tipo) {
    const config = configuracionesParametros[tipo];
    if (!config) return;
    
    const boton = document.getElementById(tipo === 'umbral' ? 'aplicarParametros' : 'aplicarConfiguracionPropagacion');
    const textoOriginal = boton.textContent;
    
    boton.textContent = '⏳ Aplicando...';
    boton.disabled = true;
    
    try {
        const requestConfig = { 
            method: 'post', 
            url: config.url, 
            data: config.payload ? config.payload() : {}
        };
        
        if (config.params) requestConfig.params = config.params();
        
        const response = await axios(requestConfig);
        
        if (response.data.status === 'success') {
            boton.textContent = '✅ Aplicado';
            if (config.onSuccess) config.onSuccess(response.data);
        } else {
            throw new Error(response.data.mensaje || 'Error desconocido');
        }
        
    } catch (error) {
        mostrarNotificacion(`Error aplicando ${tipo}: ${error.message}`, 'error');
        boton.textContent = textoOriginal;
    } finally {
        setTimeout(() => {
            boton.textContent = textoOriginal;
            boton.disabled = false;
        }, 3000);
    }
}

function actualizarValorParametro(parametro, elementoValor) {
    const valor = document.getElementById(parametro).value;
    document.getElementById(elementoValor).textContent = valor;
    
    // Actualizar variables globales
    if (parametro === 'umbralSimilitud') umbralSimilitud = parseFloat(valor);
    if (parametro === 'factorRefuerzoTemporal') factorRefuerzoTemporal = parseFloat(valor);
}

// PROCESAMIENTO UNIFICADO DE GRAFOS
const tiposContexto = {
    'reunion': { bg: '#e8f5e8', border: '#4caf50', icon: '👥' },
    'entrevista': { bg: '#e3f2fd', border: '#2196f3', icon: '🎤' },
    'brainstorm': { bg: '#f3e5f5', border: '#9c27b0', icon: '💡' },
    'planning': { bg: '#fff3e0', border: '#ff9800', icon: '📋' },
    'tarea': { bg: '#e8f5e8', border: '#388e3c', icon: '⚖️' },
    'evento': { bg: '#fce4ec', border: '#c2185b', icon: '⚡' },
    'proyecto': { bg: '#f3e5f5', border: '#7b1fa2', icon: '❓' },
    'conocimiento': { bg: '#e1f5fe', border: '#0288d1', icon: '📚' },
    'general': { bg: '#f5f5f5', border: '#757575', icon: '📄' },
    'documento': { bg: '#ffe4e1', border: '#ff69b4', icon: '📄' }
};

// FUNCIONES PRINCIPALES SIMPLIFICADAS
async function preguntarConPropagacion() {
    const pregunta = document.getElementById('pregunta').value.trim();
    if (!pregunta) return mostrarNotificacion("Por favor escribí una pregunta.", 'warning');

    const elementos = {
        respuesta: document.getElementById('respuesta'),
        botonAgregar: document.getElementById('botonAgregarRespuesta'),
        botonArbol: document.getElementById('botonVerArbol'),
        panelEstrategia: document.getElementById('panelEstrategia'),
        contenidoEstrategia: document.getElementById('contenidoEstrategia')
    };
    
    elementos.respuesta.innerHTML = "🧠 Analizando con propagación de activación...";
    elementos.botonAgregar.style.display = 'none';
    elementos.botonArbol.style.display = 'none';
    elementos.panelEstrategia.classList.add('hidden');

    try {
        const params = new URLSearchParams({
            pregunta: pregunta,
            usar_propagacion: propagacionHabilitada,
            max_pasos: parametrosPropagacion.max_pasos,
            factor_decaimiento: parametrosPropagacion.factor_decaimiento,
            umbral_activacion: parametrosPropagacion.umbral_activacion
        });
        
        const res = await axios.get(`/preguntar-con-propagacion/?${params}`);
        
        elementos.respuesta.innerText = res.data.respuesta;
        ultimaRespuesta = res.data.respuesta;
        ultimaPregunta = pregunta;
        
        // Mostrar información de estrategia
        if (res.data.analisis_intencion && res.data.estrategia_aplicada) {
            mostrarInformacionEstrategia(res.data, elementos);
        }
        
        // Mostrar botones según resultados
        if (res.data.respuesta && !res.data.respuesta.startsWith("[ERROR]")) {
            elementos.botonAgregar.style.display = 'block';
        }
        
        const subgrafo = res.data.subgrafo;
        if (subgrafo && subgrafo.nodes && subgrafo.nodes.length > 0) {
            ultimoSubgrafo = subgrafo;
            elementos.botonArbol.style.display = 'block';
        }
        
    } catch (error) {
        elementos.respuesta.innerText = `Error: ${error.message}`;
        elementos.botonAgregar.style.display = 'none';
        elementos.botonArbol.style.display = 'none';
    }
}

function mostrarInformacionEstrategia(data, elementos) {
    const analisis = data.analisis_intencion;
    const estrategia = data.estrategia_aplicada;
    const propagacion = data.propagacion || {};
    const factorMostrado = estrategia.factor_refuerzo || 1.0;
    
    let estrategiaHtml = `
        <div class="grid grid-cols-2 gap-3 text-xs">
            <div><div class="font-medium">🧠 Intención:</div><div>${analisis.intencion_temporal?.toUpperCase() || 'N/A'}</div></div>
            <div><div class="font-medium">⚙️ Factor de refuerzo:</div><div>${factorMostrado}x</div></div>
            <div><div class="font-medium">🔄 Propagación:</div><div>${propagacionHabilitada ? 'ACTIVA' : 'DESACTIVADA'}</div></div>
            <div><div class="font-medium">➕ Nuevos contextos:</div><div>${estrategia.nodos_adicionales_propagacion || 0}</div></div>
        </div>
    `;
    
    if (propagacion.total_nodos_alcanzados > 0) {
        estrategiaHtml += `
            <div class="mt-2 pt-2 border-t border-yellow-300 text-xs">
                <div class="font-medium text-green-700 mb-1">🔄 Detalles de Propagación:</div>
                <div class="grid grid-cols-2 gap-2">
                    <div>Directos: <span class="font-bold">${propagacion.contextos_directos?.length || 0}</span></div>
                    <div>Indirectos: <span class="font-bold">${propagacion.contextos_indirectos?.length || 0}</span></div>
                    <div>Solo propagación: <span class="font-bold">${propagacion.solo_por_propagacion?.length || 0}</span></div>
                    <div>Pasos: <span class="font-bold">${propagacion.pasos_propagacion || parametrosPropagacion.max_pasos}</span></div>
                </div>
            </div>
        `;
    }
    
    elementos.contenidoEstrategia.innerHTML = estrategiaHtml;
    elementos.panelEstrategia.classList.remove('hidden');
}

// FUNCIONES DE INTERFAZ SIMPLIFICADAS
async function buscarSemantico() {
    const texto = document.getElementById('textoBusqueda').value.trim();
    if (!texto) return mostrarNotificacion("Por favor escribí algo para buscar.", 'warning');

    try {
        const res = await axios.get(`/buscar/?texto=${encodeURIComponent(texto)}`);
        const container = document.getElementById('resultadosBusqueda');
        
        if (Object.keys(res.data).length === 0) {
            container.innerHTML = "<p class='text-gray-500 italic'>No se encontraron resultados.</p>";
            return;
        }

        container.innerHTML = Object.entries(res.data).map(([id, info]) => {
            const icono = info.es_temporal ? "🕐" : "📋";
            const timestamp = info.timestamp ? `<p class="text-xs text-gray-500 mt-1">⏰ ${new Date(info.timestamp).toLocaleString()}</p>` : "";
            
            return `
                <div class="p-3 bg-gray-100 rounded border-l-4 border-pink-600 shadow">
                    <strong class="text-pink-800">${icono} ${info.titulo}</strong><br>
                    <p class="text-sm text-gray-700 mt-1">${info.texto.substring(0, 120)}${info.texto.length > 120 ? '...' : ''}</p>
                    ${timestamp}
                </div>
            `;
        }).join('');
        
    } catch (error) {
        document.getElementById('resultadosBusqueda').innerHTML = `<p class="text-red-600">Error: ${error.message}</p>`;
    }
}

async function agregarRespuestaComoContexto() {
    if (!ultimaRespuesta || !ultimaPregunta) return mostrarNotificacion("No hay una respuesta válida para agregar.", 'warning');

    const tituloSugerido = `Respuesta: ${ultimaPregunta.substring(0, 50)}${ultimaPregunta.length > 50 ? '...' : ''}`;
    const titulo = prompt(`💡 Título para este contexto:`, tituloSugerido);
    
    if (!titulo || !titulo.trim()) return mostrarNotificacion("Se necesita un título.", 'warning');

    const esTemporal = confirm("🕐 ¿Hacer este contexto TEMPORAL?\n\n✅ SÍ = Con fecha actual\n❌ NO = Atemporal");

    try {
        const respuestaLimpia = ultimaRespuesta.split('\n\n📚 Contextos:')[0];
        const res = await axios.post('/contexto/', { 
            titulo: titulo.trim(), 
            texto: respuestaLimpia,
            es_temporal: esTemporal
        });
        
        const tipoContexto = esTemporal ? "TEMPORAL 🕐" : "ATEMPORAL 📋";
        mostrarNotificacion(`Respuesta agregada como contexto ${tipoContexto}! ID: ${res.data.id}`, 'exito');
        document.getElementById('botonAgregarRespuesta').style.display = 'none';
        
    } catch (error) {
        mostrarNotificacion(`Error: ${error.message}`, 'error');
    }
}

// DELEGACIÓN DE EVENTOS UNIFICADA
document.addEventListener('DOMContentLoaded', async function() {
    // Event listeners principales
    const eventos = {
        'pregunta': { evento: 'keypress', funcion: (e) => e.key === 'Enter' && preguntarConPropagacion() },
        'textoBusqueda': { evento: 'keypress', funcion: (e) => e.key === 'Enter' && buscarSemantico() },
        'toggleAgregarConversacion': { evento: 'click', funcion: toggleFormularioConversacion },
        'cancelarAgregarConversacion': { evento: 'click', funcion: limpiarFormularioConversacion },
        'umbralSimilitud': { evento: 'input', funcion: () => actualizarValorParametro('umbralSimilitud', 'valorUmbralSimilitud') },
        'factorRefuerzoTemporal': { evento: 'input', funcion: () => actualizarValorParametro('factorRefuerzoTemporal', 'valorRefuerzoTemporal') },
    };

    Object.entries(eventos).forEach(([id, config]) => {
        const elemento = document.getElementById(id);
        if (elemento) elemento.addEventListener(config.evento, config.funcion);
    });

    // Cargar parámetros iniciales
    try {
        const response = await fetch('/estado-parametros/');
        const data = await response.json();
        if (data.status === 'success') {
            const umbralControl = document.getElementById('umbralSimilitud');
            const refuerzoControl = document.getElementById('factorRefuerzoTemporal');
            
            if (umbralControl) {
                umbralControl.value = data.parametros.umbral_similitud;
                actualizarValorParametro('umbralSimilitud', 'valorUmbralSimilitud');
            }
            if (refuerzoControl) {
                refuerzoControl.value = data.parametros.factor_refuerzo_temporal;
                actualizarValorParametro('factorRefuerzoTemporal', 'valorRefuerzoTemporal');
            }
        }
    } catch (error) {
        console.error('Error cargando parámetros iniciales:', error);
    }

    setTimeout(() => obtenerEstadoPropagacion(), 1000);
});

// FUNCIONES AUXILIARES RESTANTES
function toggleFormularioConversacion() {
    const form = document.getElementById('formAgregarConversacion');
    form.classList.toggle('hidden');
    if (!form.classList.contains('hidden')) {
        document.getElementById('tituloConversacion').focus();
    }
}

function limpiarFormularioConversacion() {
    ['tituloConversacion', 'contenidoConversacion', 'participantesConversacion', 'fechaConversacion'].forEach(id => {
        const elemento = document.getElementById(id);
        if (elemento) elemento.value = '';
    });
    const tipo = document.getElementById('tipoConversacion');
    if (tipo) tipo.value = 'general';
    const checkboxAtemporal = document.getElementById('conversacionAtemporal');
    if (checkboxAtemporal) {
        checkboxAtemporal.checked = false;
        toggleFechaConversacion(); // Restaurar estado del campo fecha
    }
    document.getElementById('formAgregarConversacion').classList.add('hidden');
}

function alternarPropagacion() {
    propagacionHabilitada = !propagacionHabilitada;
    
    const boton = document.getElementById('togglePropagacion');
    const estado = document.getElementById('estadoPropagacionToggle');
    
    if (propagacionHabilitada) {
        boton.className = boton.className.replace('bg-red-600 hover:bg-red-700', 'bg-green-600 hover:bg-green-700');
        boton.textContent = '🔄 Desactivar Propagación';
        estado.textContent = 'ACTIVA';
        estado.className = estado.className.replace('text-red-600', 'text-green-600');
    } else {
        boton.className = boton.className.replace('bg-green-600 hover:bg-green-700', 'bg-red-600 hover:bg-red-700');
        boton.textContent = '🔄 Activar Propagación';
        estado.textContent = 'INACTIVA';
        estado.className = estado.className.replace('text-green-600', 'text-red-600');
    }
}

// FUNCIONES DE COMPATIBILIDAD (mantienen nombres originales)
function aplicarConfiguracionParametros() { return aplicarConfiguracion('umbral'); }

// Función específica para propagación (CORREGIDA)
async function aplicarConfiguracionPropagacion() {
    const factorDecaimiento = parseFloat(document.getElementById('factorDecaimiento').value);
    const maxPasos = parseInt(document.getElementById('maxPasosPropagacion').value);
    
    // Actualizar variable global
    parametrosPropagacion.max_pasos = maxPasos;
    parametrosPropagacion.factor_decaimiento = factorDecaimiento;
    
    const boton = document.querySelector('button[onclick="aplicarConfiguracionPropagacion()"]');
    const textoOriginal = boton.textContent;
    
    boton.textContent = '⏳ Aplicando...';
    boton.disabled = true;
    
    try {
        const response = await axios.post('/configurar-propagacion/', {}, {
            params: {
                factor_decaimiento: factorDecaimiento,
                umbral_activacion: parametrosPropagacion.umbral_activacion
            }
        });
        
        if (response.data.status === 'parametros_actualizados') {
            boton.textContent = '✅ Aplicado';
            mostrarNotificacion(`Propagación configurada: Decaimiento=${factorDecaimiento}, Pasos=${maxPasos}`, 'exito');
            
            await obtenerEstadoPropagacion(); 
        } else {
            throw new Error(response.data.error || 'Error desconocido');
        }
        
    } catch (error) {
        mostrarNotificacion(`Error aplicando propagación: ${error.message}`, 'error');
        boton.textContent = textoOriginal;
    } finally {
        setTimeout(() => {
            boton.textContent = textoOriginal;
            boton.disabled = false;
        }, 3000);
    }
}

function cerrarModalArbol() { gestionarModal('modalArbol', 'cerrar'); }
function mostrarArbolConsulta() { ultimoSubgrafo ? abrirModalArbol(ultimoSubgrafo) : mostrarNotificacion("No hay subgrafo disponible para mostrar.", 'warning'); }

// Event listener para cerrar modal de árbol
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        gestionarModal('modalArbol', 'cerrar');
    }
});

// FUNCIONES QUE PERMANECEN SIN CAMBIOS SIGNIFICATIVOS

async function obtenerEstadoPropagacion() {
    try {
        const res = await axios.get('/estado-propagacion/');
        
        if (res.data.error) {
            document.getElementById('estadoPropagacion').innerHTML = 
                `<p class="text-red-600 text-xs">❌ ${res.data.error}</p>`;
            return res.data;
        }
        
        const estado = res.data;
        
        const estadoHtml = `
            <div class="space-y-2 text-xs">
                <div class="flex justify-between">
                    <span>🔄 Propagación:</span>
                    <span class="font-bold ${estado.propagacion_habilitada ? 'text-green-600' : 'text-red-600'}">
                        ${estado.propagacion_habilitada ? 'HABILITADA' : 'DESHABILITADA'}
                    </span>
                </div>
                <div class="flex justify-between">
                    <span>📉 Factor decaimiento:</span>
                    <span class="font-bold">${estado.factor_decaimiento || 'N/A'}</span>
                </div>
                <div class="flex justify-between">
                    <span>🔢 Pasos máximos:</span>
                    <span class="font-bold text-purple-600">${parametrosPropagacion.max_pasos}</span>
                </div>
                <div class="flex justify-between">
                    <span>🎯 Umbral activación:</span>
                    <span class="font-bold">${estado.umbral_activacion || 'N/A'}</span>
                </div>
                <div class="flex justify-between">
                    <span>📊 Nodos totales:</span>
                    <span class="font-bold text-blue-600">${estado.total_nodos}</span>
                </div>
                <div class="flex justify-between">
                    <span>🔗 Aristas totales:</span>
                    <span class="font-bold text-blue-600">${estado.total_aristas}</span>
                </div>
                <div class="flex justify-between">
                    <span>✅ Sistema listo:</span>
                    <span class="font-bold ${estado.grafo_disponible ? 'text-green-600' : 'text-red-600'}">
                        ${estado.grafo_disponible ? 'SÍ' : 'NO'}
                    </span>
                </div>
            </div>
        `;
        
        document.getElementById('estadoPropagacion').innerHTML = estadoHtml;
        return estado;
        
    } catch (error) {
        document.getElementById('estadoPropagacion').innerHTML = 
            `<p class="text-red-600 text-xs">❌ Error: ${error.message}</p>`;
        return null;
    }
}

function abrirModalArbol(subgrafo) {
    gestionarModal('modalArbol', 'abrir');
    const container = document.getElementById('arbolConsulta');

    if (!subgrafo || !subgrafo.nodes || subgrafo.nodes.length === 0) {
        container.innerHTML = `
            <div class="flex items-center justify-center h-full text-gray-500 flex-col">
                <p class="text-lg mb-2">❌ No se puede mostrar el árbol</p>
                <p class="text-sm">Subgrafo vacío o inválido</p>
            </div>
        `;
        return;
    }

    try {
        const nodes = subgrafo.nodes.map(n => {
            let color, shape = "box";
            let fontConfig = { size: 12, color: "#374151", align: "center" };
            
            if (n.group && n.group.includes("pregunta")) {
                color = { background: "#dbeafe", border: "#3b82f6" };
                shape = "diamond";
                fontConfig = { size: 14, color: "#1e40af", align: "center" };
            } else if (n.group === "temporal") {
                const tipoContexto = n.tipo_contexto || 'general';
                const coloresTipos = {
                    'reunion': { background: "#fff3e0", border: "#f57c00" },
                    'tarea': { background: "#e8f5e8", border: "#388e3c" },
                    'evento': { background: "#fce4ec", border: "#c2185b" },
                    'proyecto': { background: "#f3e5f5", border: "#7b1fa2" },
                    'conocimiento': { background: "#e1f5fe", border: "#0288d1" },
                    'general': { background: "#dbeafe", border: "#2563eb" }
                };
                color = coloresTipos[tipoContexto] || coloresTipos['general'];
                fontConfig = { size: 12, color: "#1e40af" };
            } else {
                color = { background: "#f3f4f6", border: "#6b7280" };
            }

            return {
                id: n.id,
                label: n.label || n.id,
                title: n.title || n.label || n.id,
                color: color,
                shape: shape,
                font: fontConfig,
                margin: { top: 10, right: 10, bottom: 10, left: 10 },
                shadow: { enabled: true, size: 3, x: 1, y: 1, color: 'rgba(0,0,0,0.1)' }
            };
        });

        const edges = subgrafo.edges.map(e => {
            const pesoEfectivo = e.peso_efectivo || 0;
            const relevanciaTemp = e.relevancia_temporal || 0;
            const width = Math.max(1, pesoEfectivo * 2);
            const colorArista = relevanciaTemp > 0.3 ? "#4caf50" : "#2196f3";
            
            return {
                from: e.from,
                to: e.to,
                arrows: { to: { enabled: true, scaleFactor: 1.2 } },
                label: e.label || "",
                title: `Peso Estructural: ${(e.peso_estructural || 0).toFixed(3)}\nRelevancia Temporal: ${relevanciaTemp.toFixed(3)}\nPeso Efectivo: ${pesoEfectivo.toFixed(3)}`,
                font: { 
                    size: 10, 
                    align: "top",
                    background: 'rgba(255,255,255,0.8)',
                    strokeWidth: 1,
                    strokeColor: 'rgba(255,255,255,0.9)'
                },
                color: { 
                    color: colorArista,
                    highlight: relevanciaTemp > 0.3 ? "#66bb6a" : "#42a5f5"
                },
                width: width,
                smooth: { type: "cubicBezier", roundness: 0.4 }
            };
        });

        const options = {
            layout: {
                hierarchical: {
                    enabled: true,
                    direction: "UD",
                    sortMethod: "directed",
                    nodeSpacing: 140,
                    levelSeparation: 100,
                    treeSpacing: 200
                }
            },
            physics: { enabled: false },
            nodes: { borderWidth: 2 },
            edges: { smooth: { type: "cubicBezier", roundness: 0.4 } },
            interaction: { 
                hover: true, 
                zoomView: true, 
                dragView: true,
                selectConnectedEdges: false
            }
        };

        const network = new vis.Network(container, { 
            nodes: new vis.DataSet(nodes), 
            edges: new vis.DataSet(edges) 
        }, options);

        setTimeout(() => {
            network.fit({
                animation: {
                    duration: 800,
                    easingFunction: 'easeInOutQuart'
                }
            });
        }, 200);

    } catch (error) {
        container.innerHTML = `
            <div class="flex items-center justify-center h-full text-red-500 flex-col">
                <p class="text-lg mb-2">❌ Error al renderizar</p>
                <p class="text-sm">${error.message}</p>
            </div>
        `;
    }
}

async function agregarConversacion() {
    const titulo = document.getElementById('tituloConversacion').value.trim();
    const contenido = document.getElementById('contenidoConversacion').value.trim();
    const participantes = document.getElementById('participantesConversacion').value.trim();
    const fecha = document.getElementById('fechaConversacion').value;
    const esAtemporal = document.getElementById('conversacionAtemporal').checked;
    const pdfFile = document.getElementById('pdfFileConversacion').files[0];
    
    if (!titulo || !contenido) {
        alert('Por favor completa título y contenido');
        return;
    }
    
    // Mostrar indicador de carga
    const btnGuardar = event.target;
    const textoOriginal = btnGuardar.textContent;
    btnGuardar.disabled = true;
    btnGuardar.textContent = '⏳ Procesando...';
    
    try {
        // Crear FormData para enviar archivo
        const formData = new FormData();
        formData.append('titulo', titulo);
        formData.append('contenido', contenido);
        
        if (participantes) {
            formData.append('participantes', participantes);
        }
        
        if (!esAtemporal && fecha) {
            formData.append('fecha', fecha);
        }
        
        // Agregar PDF si existe
        if (pdfFile) {
            formData.append('pdf_file', pdfFile);
            console.log('📎 Adjuntando PDF:', pdfFile.name);
        }
        
        // Enviar al servidor
        const response = await fetch('/agregar_conversacion_con_pdf', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.status === 'éxito') {
            let mensaje = `✅ ${data.mensaje}\n`;
            mensaje += `📊 Total fragmentos: ${data.total_fragmentos}\n`;
            mensaje += `💬 Fragmentos de mensajes: ${data.total_fragmentos_mensaje}`;
            
            if (data.total_fragmentos_pdf > 0) {
                mensaje += `\n📄 Fragmentos del PDF: ${data.total_fragmentos_pdf}`;
            }
            
            alert(mensaje);
            
            // Limpiar formulario
            document.getElementById('tituloConversacion').value = '';
            document.getElementById('contenidoConversacion').value = '';
            document.getElementById('participantesConversacion').value = '';
            document.getElementById('fechaConversacion').value = '';
            document.getElementById('conversacionAtemporal').checked = false;
            document.getElementById('pdfFileConversacion').value = '';
            
            // Ocultar formulario
            document.getElementById('formAgregarConversacion').classList.add('hidden');
        } else {
            alert(`❌ Error: ${data.mensaje}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert(`❌ Error al agregar conversación: ${error.message}`);
    } finally {
        // Restaurar botón
        btnGuardar.disabled = false;
        btnGuardar.textContent = textoOriginal;
    }
}

async function cargarEstadisticas() {
    const estadisticasBtn = event.target;
    const originalText = estadisticasBtn.textContent;
    
    estadisticasBtn.textContent = '⏳ Cargando...';
    estadisticasBtn.disabled = true;
    
    try {
        const res = await axios.get('/estadisticas-actualizacion/');
        
        if (res.data.status === 'success') {
            const stats = res.data.estadisticas;
            
            document.getElementById('estadisticas').innerHTML = `
                <div class="space-y-2">
                    <div class="flex justify-between">
                        <span>📊 Total Nodos:</span>
                        <span class="font-bold text-blue-600">${stats.total_nodos}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>🔗 Total Relaciones:</span>
                        <span class="font-bold text-green-600">${stats.total_relaciones}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>⚡ Actualización:</span>
                        <span class="font-bold text-purple-600">INCREMENTAL</span>
                    </div>
                    <div class="flex justify-between">
                        <span>🎯 Umbral:</span>
                        <span class="font-bold">${stats.umbral_similitud}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>🕐 Temporales:</span>
                        <span class="font-bold text-blue-600">${stats.contextos_temporales || 0}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>📋 Atemporales:</span>
                        <span class="font-bold text-gray-600">${stats.contextos_atemporales || 0}</span>
                    </div>
                </div>
            `;
        } else {
            document.getElementById('estadisticas').innerHTML = `<p class="text-red-600 text-xs">❌ ${res.data.error}</p>`;
        }
        
    } catch (error) {
        document.getElementById('estadisticas').innerHTML = `<p class="text-red-600 text-xs">❌ Error: ${error.message}</p>`;
    } finally {
        estadisticasBtn.textContent = originalText;
        estadisticasBtn.disabled = false;
    }
}

async function cargarEstadisticasDobleNivel() {
    try {
        const res = await axios.get('/estadisticas/doble-nivel/');
        const data = res.data;
        const macro = data.nivel_macro;
        const micro = data.nivel_micro;
        const relaciones = data.relaciones;
        const metricas = data.metricas;
        
        document.getElementById('estadisticas').innerHTML = `
            <div class="space-y-3 text-xs">
                <div class="border-b pb-2">
                    <div class="font-medium text-purple-700 mb-1">🌍 Nivel Macro (Conversaciones)</div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>Total: <span class="font-bold text-purple-600">${macro.total_conversaciones}</span></div>
                        <div>Complejas: <span class="font-bold">${macro.conversaciones_complejas}</span></div>
                    </div>
                </div>
                <div class="border-b pb-2">
                    <div class="font-medium text-blue-700 mb-1">🔬 Nivel Micro (Fragmentos)</div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>Total: <span class="font-bold text-blue-600">${micro.total_fragmentos}</span></div>
                        <div>Temporales: <span class="font-bold text-green-600">${micro.fragmentos_temporales}</span></div>
                    </div>
                </div>
                <div class="border-b pb-2">
                    <div class="font-medium text-orange-700 mb-1">🔗 Relaciones</div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>Internas: <span class="font-bold text-orange-600">${relaciones.intra_conversacion}</span></div>
                        <div>Entre conv: <span class="font-bold text-red-600">${relaciones.inter_conversacion}</span></div>
                    </div>
                </div>
                <div>
                    <div class="font-medium text-green-700 mb-1">📊 Métricas</div>
                    <div class="space-y-1">
                        <div>Frags/Conv: <span class="font-bold">${metricas.promedio_fragmentos_por_conversacion}</span></div>
                        <div>% Rel. Internas: <span class="font-bold">${metricas.ratio_relaciones_internas}%</span></div>
                        <div>% Temporal Micro: <span class="font-bold">${metricas.ratio_temporal_micro}%</span></div>
                    </div>
                </div>
            </div>
        `;
        
    } catch (error) {
        document.getElementById('estadisticas').innerHTML = `<p class="text-red-600 text-xs">Error: ${error.message}</p>`;
    }
}

async function forzarRecalculoRelaciones() {
    if (!confirm('¿Recalcular todas las relaciones del grafo?\n\nEsto puede tardar unos segundos con muchos contextos.')) {
        return;
    }
    
    try {
        const response = await axios.post('/recalcular-relaciones/');
        
        if (response.data.status === 'success') {
            const antes = response.data.antes;
            const despues = response.data.despues;
            const diferencia = despues.relaciones - antes.relaciones;
            const signo = diferencia >= 0 ? '+' : '';
            
            mostrarNotificacion(`Relaciones recalculadas! Nodos: ${despues.nodos}, Relaciones: ${antes.relaciones} → ${despues.relaciones} (${signo}${diferencia})`, 'exito', 8000);
            
            if (document.getElementById('estadisticas').innerHTML !== '') {
                cargarEstadisticas();
            }
        } else {
            mostrarNotificacion(`Error: ${response.data.mensaje}`, 'error');
        }
    } catch (error) {
        mostrarNotificacion(`Error de conexión: ${error.message}`, 'error');
    }
}

// PROCESAMIENTO DE CONVERSACIONES
function cambiarTabEntrada(tipo) {
    tipoEntradaActual = tipo;
    
    const tabTexto = document.getElementById('tabTextoPlano');
    const tabJson = document.getElementById('tabArchivoJSON');
    
    if (tipo === 'texto') {
        tabTexto.className = 'flex-1 py-2 text-sm font-medium border-b-2 border-orange-600 text-orange-800';
        tabJson.className = 'flex-1 py-2 text-sm font-medium text-gray-600 hover:text-orange-800';
        document.getElementById('contenidoTextoPlano').classList.remove('hidden');
        document.getElementById('contenidoArchivoJSON').classList.add('hidden');
    } else if (tipo === 'archivo') {
        tabTexto.className = 'flex-1 py-2 text-sm font-medium text-gray-600 hover:text-orange-800';
        tabJson.className = 'flex-1 py-2 text-sm font-medium border-b-2 border-orange-600 text-orange-800';
        document.getElementById('contenidoTextoPlano').classList.add('hidden');
        document.getElementById('contenidoArchivoJSON').classList.remove('hidden');
    }
}

async function analizarYMostrarPreview() {
    let payload;
    
    // Mostrar indicador de carga
    const contenedorPrincipal = document.querySelector('.bg-orange-200.rounded-lg');
    const indicadorCarga = document.createElement('div');
    indicadorCarga.id = 'indicadorProcesamientoConv';
    indicadorCarga.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
    indicadorCarga.innerHTML = `
        <div class="bg-white rounded-lg shadow-2xl p-6 max-w-md">
            <div class="flex flex-col items-center space-y-4">
                <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-orange-600"></div>
                <p class="text-lg font-semibold text-gray-800">Analizando conversaciones...</p>
                <p class="text-sm text-gray-600">Por favor espera</p>
            </div>
        </div>
    `;
    document.body.appendChild(indicadorCarga);
    
    try {
        if (tipoEntradaActual === 'texto') {
            const texto = document.getElementById('textoPlanoConversaciones').value.trim();
            if (!texto) {
                document.getElementById('indicadorProcesamientoConv')?.remove();
                return mostrarNotificacion("Por favor pega el texto con las conversaciones.", 'warning');
            }
            payload = { texto };
            
        } else if (tipoEntradaActual === 'archivo') {
            const fileInput = document.getElementById('archivoJSONConversaciones');
            const file = fileInput.files[0];
            
            if (!file) {
                document.getElementById('indicadorProcesamientoConv')?.remove();
                return mostrarNotificacion("Por favor selecciona un archivo JSON.", 'warning');
            }
            
            if (!file.name.endsWith('.json')) {
                document.getElementById('indicadorProcesamientoConv')?.remove();
                return mostrarNotificacion("Solo se permiten archivos .json", 'warning');
            }
            
            // Leer archivo
            const contenidoArchivo = await file.text();
            const jsonData = JSON.parse(contenidoArchivo);
            payload = { json_data: jsonData };
        }
        
        const response = await axios.post('/conversacion/parse-preview/', payload);
        const data = response.data;
        
        if (data.status === 'preview_listo') {
            conversacionesParseadas = data.conversaciones_parseadas;
            mostrarPreviewEnModal(data.preview);
        } else {
            throw new Error(data.mensaje || 'Error en análisis');
        }
        
    } catch (error) {
        mostrarNotificacion(`Error: ${error.message}`, 'error');
    } finally {
        document.getElementById('indicadorProcesamientoConv')?.remove();
    }
}

function mostrarPreviewEnModal(preview) {
    const container = document.getElementById('previewConversaciones');
    
    let html = `<div class="text-sm font-semibold text-gray-700 mb-3">
        ✅ ${preview.total_conversaciones} conversación(es) encontrada(s)
    </div>`;
    
    preview.conversaciones.forEach((conv, idx) => {
        const participantesStr = conv.participantes.length > 0 
            ? ` | 👥 ${conv.participantes.length} participante(s)`
            : '';
        
        html += `
            <div class="bg-white border border-gray-300 rounded p-3">
                <div class="font-medium text-gray-800">${idx + 1}. ${conv.titulo}</div>
                <div class="text-xs text-gray-600 mt-1">
                    📝 ${conv.palabras_aproximadas} palabras | 📄 ${conv.lineas_aproximadas} líneas${participantesStr}
                </div>
                ${conv.tiene_fecha ? '<div class="text-xs text-green-600 mt-1">📅 Fecha detectada</div>' : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
    document.getElementById('modalMetadatosConversaciones').classList.remove('hidden');
}

async function confirmarYProcesarConversaciones() {
    if (!conversacionesParseadas) {
        return mostrarNotificacion("No hay conversaciones para procesar.", 'error');
    }
    
    const metadataGlobal = {};
    
    // Solo leer la fecha (si existe)
    const fecha = document.getElementById('metadataFecha')?.value;
    if (fecha) {
        metadataGlobal.fecha = new Date(fecha).toISOString();
    }
    
    // Mostrar indicador de procesamiento
    const indicadorProcesamiento = document.createElement('div');
    indicadorProcesamiento.id = 'indicadorGuardandoConv';
    indicadorProcesamiento.className = 'fixed inset-0 bg-black bg-opacity-70 z-50 flex items-center justify-center';
    indicadorProcesamiento.innerHTML = `
        <div class="bg-white rounded-lg shadow-2xl p-8 max-w-md">
            <div class="flex flex-col items-center space-y-4">
                <div class="animate-spin rounded-full h-20 w-20 border-b-4 border-green-600"></div>
                <p class="text-xl font-bold text-gray-800">Guardando conversaciones...</p>
                <p class="text-sm text-gray-600">Fragmentando y detectando metadatos</p>
                <div class="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div class="bg-green-600 h-2 rounded-full animate-pulse" style="width: 70%"></div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(indicadorProcesamiento);
    
    try {
        const response = await axios.post('/conversacion/procesar-con-metadata/', {
            conversaciones: conversacionesParseadas,
            metadata_global: metadataGlobal
        });
        
        const data = response.data;
        
        if (data.status === 'procesado') {
            cerrarModalMetadatos();
            limpiarCamposConversaciones();
            
            // Calcular total de fragmentos
            const totalFragmentos = data.conversaciones_procesadas.reduce(
                (sum, conv) => sum + conv.fragmentos_creados, 0
            );
            
            mostrarNotificacion(
                `✅ ${data.total_procesadas} conversación(es) guardada(s) | ${totalFragmentos} fragmentos creados`, 
                'exito',
                6000
            );
            
            if (data.total_errores > 0) {
                console.warn('Errores en procesamiento:', data.errores);
                mostrarNotificacion(
                    `⚠️ ${data.total_errores} conversación(es) con errores`, 
                    'warning',
                    5000
                );
            }
        } else {
            throw new Error(data.mensaje || 'Error en procesamiento');
        }
        
    } catch (error) {
        mostrarNotificacion(
            `Error: ${error.response?.data?.mensaje || error.message}`, 
            'error'
        );
    } finally {
        document.getElementById('indicadorGuardandoConv')?.remove();
    }
}

function cerrarModalMetadatos() {
    document.getElementById('modalMetadatosConversaciones').classList.add('hidden');
    conversacionesParseadas = null;
    
    // Solo limpiar fecha
    const metadataFecha = document.getElementById('metadataFecha');
    if (metadataFecha) metadataFecha.value = '';
}

function limpiarCamposConversaciones() {
    // Limpiar texto plano
    const textoPlano = document.getElementById('textoPlanoConversaciones');
    if (textoPlano) textoPlano.value = '';
    
    // Limpiar input de archivo JSON
    const archivoInput = document.getElementById('archivoJSONConversaciones');
    if (archivoInput) archivoInput.value = '';
    
    // Limpiar metadatos del modal (solo fecha)
    const metadataFecha = document.getElementById('metadataFecha');
    if (metadataFecha) metadataFecha.value = '';
    
    // Resetear variable global
    conversacionesParseadas = null;
    
    // Resetear a tab de texto
    tipoEntradaActual = 'texto';
    cambiarTabEntrada('texto');
}

function toggleFechaConversacion() {
    const checkbox = document.getElementById('conversacionAtemporal');
    const campoFecha = document.getElementById('fechaConversacion');
    
    if (checkbox.checked) {
        campoFecha.disabled = true;
        campoFecha.value = '';
        campoFecha.classList.add('bg-gray-200', 'cursor-not-allowed');
        campoFecha.classList.remove('bg-green-50');
    } else {
        campoFecha.disabled = false;
        campoFecha.classList.remove('bg-gray-200', 'cursor-not-allowed');
        campoFecha.classList.add('bg-green-50');
    }
}

// Función para abrir la página dedicada del grafo
function abrirPaginaGrafo() {
    window.open('/grafo.html', '_blank');
}