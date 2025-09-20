// Variables globales
let ultimaRespuesta = "";
let ultimaPregunta = "";
let networkInstance = null;
let ultimoSubgrafo = null;
// Variables para el sistema doble nivel
let vistaActual = 'macro';
let conversacionesList = {};
let estadisticasDobleNivel = null;
// Variables globales para propagación
let propagacionHabilitada = true;
let parametrosPropagacion = {
    factor_decaimiento: 0.8,
    umbral_activacion: 0.01,
    max_pasos: 3
};

// Event listeners principales
document.addEventListener('DOMContentLoaded', function() {
    // Enter en campos de input
    document.getElementById('pregunta').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') preguntarConPropagacion();
    });

    document.getElementById('textoBusqueda').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') buscarSemantico();
    });

    // Radio buttons para modo temporal
    const radios = document.querySelectorAll('input[name="modoTemporal"]');
    radios.forEach(radio => {
        radio.addEventListener('change', function() {
            const container = document.getElementById('referenciaManualContainer');
            if (this.value === 'temporal') {
                container.classList.remove('hidden');
            } else {
                container.classList.add('hidden');
            }
        });
    });

    // Toggle formulario agregar conversación
    document.getElementById('toggleAgregarConversacion').addEventListener('click', function() {
        const form = document.getElementById('formAgregarConversacion');
        form.classList.toggle('hidden');
        if (!form.classList.contains('hidden')) {
            document.getElementById('tituloConversacion').focus();
        }
    });

    // Cancelar agregar conversación
    document.getElementById('cancelarAgregarConversacion').addEventListener('click', function() {
        limpiarFormularioConversacion();
    });

    // Cargar conversaciones inicialmente
    mostrarConversaciones();

    // NUEVO: Radios de vista
    const radiosVista = document.querySelectorAll('input[name="tipoVista"]');
    radiosVista.forEach(radio => {
        radio.addEventListener('change', function() {
            actualizarVistaSeleccionada(this.value);
        });
    });
    
    // Selector de conversación para vista micro filtrada
    document.getElementById('conversacionFiltro').addEventListener('change', function() {
        if (this.value && vistaActual === 'micro-filtrada') {
            cargarGrafoDobleNivel();
        }
    });

    //Cargar estado inicial después de un breve delay
    setTimeout(() => {
        obtenerEstadoPropagacion();
    }, 1000);
});

// Función mejorada de preguntar con propagación
async function preguntarConPropagacion() {
    const pregunta = document.getElementById('pregunta').value.trim();
    if (!pregunta) {
        alert("Por favor escribí una pregunta.");
        return;
    }

    const respuestaDiv = document.getElementById('respuesta');
    const botonDiv = document.getElementById('botonAgregarRespuesta');
    const botonArbolDiv = document.getElementById('botonVerArbol');
    const panelEstrategia = document.getElementById('panelEstrategia');
    const contenidoEstrategia = document.getElementById('contenidoEstrategia');
    
    respuestaDiv.innerHTML = "🧠 Analizando con propagación de activación...";
    botonDiv.style.display = 'none';
    botonArbolDiv.style.display = 'none';
    panelEstrategia.classList.add('hidden');

    try {
        const usarPropagacion = propagacionHabilitada;
        const maxPasos = parametrosPropagacion.max_pasos;

        // ENVIAR PARÁMETROS ACTUALES EN CADA CONSULTA
        const factorDecaimiento = parametrosPropagacion.factor_decaimiento;
        const umbralActivacion = parametrosPropagacion.umbral_activacion;
        
        const url = `/preguntar-con-propagacion/?pregunta=${encodeURIComponent(pregunta)}&usar_propagacion=${usarPropagacion}&max_pasos=${maxPasos}&factor_decaimiento=${factorDecaimiento}&umbral_activacion=${umbralActivacion}`;
        const res = await axios.get(url);    

        respuestaDiv.innerText = res.data.respuesta;
        ultimaRespuesta = res.data.respuesta;
        ultimaPregunta = pregunta;
        
        // Mostrar información de estrategia aplicada incluyendo propagación
        if (res.data.analisis_intencion && res.data.estrategia_aplicada) {
            const analisis = res.data.analisis_intencion;
            const estrategia = res.data.estrategia_aplicada;
            const propagacion = res.data.propagacion || {};
            
            let estrategiaHtml = `
                <div class="grid grid-cols-2 gap-3 text-xs">
                    <div>
                        <div class="font-medium">🧠 Intención:</div>
                        <div>${analisis.intencion_temporal?.toUpperCase() || 'N/A'}</div>
                    </div>
                    <div>
                        <div class="font-medium">⚙️ Factor:</div>
                        <div>${(estrategia.factor_refuerzo || 1.0)}x</div>
                    </div>
                    <div>
                        <div class="font-medium">🔄 Propagación:</div>
                        <div>${usarPropagacion ? 'ACTIVA' : 'DESACTIVADA'}</div>
                    </div>
                    <div>
                        <div class="font-medium">➕ Nuevos contextos:</div>
                        <div>${estrategia.nodos_adicionales_propagacion || 0}</div>
                    </div>
                </div>
            `;
            
            // Información adicional de propagación si está disponible
            if (propagacion.total_nodos_alcanzados > 0) {
                estrategiaHtml += `
                    <div class="mt-2 pt-2 border-t border-yellow-300 text-xs">
                        <div class="font-medium text-green-700 mb-1">🔄 Detalles de Propagación:</div>
                        <div class="grid grid-cols-2 gap-2">
                            <div>Directos: <span class="font-bold">${propagacion.contextos_directos?.length || 0}</span></div>
                            <div>Indirectos: <span class="font-bold">${propagacion.contextos_indirectos?.length || 0}</span></div>
                            <div>Solo propagación: <span class="font-bold">${propagacion.solo_por_propagacion?.length || 0}</span></div>
                            <div>Pasos: <span class="font-bold">${propagacion.pasos_propagacion || maxPasos}</span></div>
                        </div>
                    </div>
                `;
            }
            
            contenidoEstrategia.innerHTML = estrategiaHtml;
            panelEstrategia.classList.remove('hidden');
        }
        
        // Mostrar botón agregar respuesta
        if (res.data.respuesta && !res.data.respuesta.startsWith("[ERROR]")) {
            botonDiv.style.display = 'block';
        }

        // Mostrar botón árbol si hay subgrafo
        const subgrafo = res.data.subgrafo;
        if (subgrafo && subgrafo.nodes && subgrafo.nodes.length > 0) {
            ultimoSubgrafo = subgrafo;
            botonArbolDiv.style.display = 'block';
        } else {
            ultimoSubgrafo = null;
        }
        
    } catch (error) {
        respuestaDiv.innerText = `Error: ${error.message}`;
        botonDiv.style.display = 'none';
        botonArbolDiv.style.display = 'none';
        panelEstrategia.classList.add('hidden');
    }
}

// Función para configurar parámetros de propagación
async function configurarPropagacion(factorDecaimiento = null, umbralActivacion = null) {
    try {
        const res = await axios.post('/configurar-propagacion/', {}, {
            params: {
                factor_decaimiento: factorDecaimiento,
                umbral_activacion: umbralActivacion
            }
        });
        
        if (res.data.error) {
            alert(`❌ Error: ${res.data.error}`);
            return;
        }
        
        // Actualizar parámetros locales
        parametrosPropagacion.factor_decaimiento = res.data.factor_decaimiento;
        parametrosPropagacion.umbral_activacion = res.data.umbral_activacion;
        
        alert(`✅ Parámetros actualizados:\nFactor decaimiento: ${res.data.factor_decaimiento}\nUmbral activación: ${res.data.umbral_activacion}`);
        
        // Actualizar estado
        obtenerEstadoPropagacion();
        
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}

// Función para aplicar configuración desde la interfaz
async function aplicarConfiguracionPropagacion() {
    const factorDecaimiento = parseFloat(document.getElementById('factorDecaimiento').value);
    const umbralActivacion = parametrosPropagacion.umbral_activacion; // Mantener el actual o usar un valor por defecto
    
    try {
        await configurarPropagacion(factorDecaimiento, umbralActivacion);
    } catch (error) {
        alert(`Error aplicando configuración: ${error.message}`);
    }
}

// Función simplificada para obtener estado
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
                    <span>🔉 Factor decaimiento:</span>
                    <span class="font-bold">${estado.factor_decaimiento || 'N/A'}</span>
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

// Función auxiliar para mostrar resultados en modal
function mostrarResultadosEnModal(titulo, contenido) {
    // Crear modal dinámico para mostrar resultados
    const modalExistente = document.getElementById('modalResultadosPropagacion');
    if (modalExistente) {
        modalExistente.remove();
    }
    
    const modal = document.createElement('div');
    modal.id = 'modalResultadosPropagacion';
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50';
    
    modal.innerHTML = `
        <div class="bg-white rounded-lg shadow-xl w-11/12 max-w-4xl max-h-[90vh] flex flex-col">
            <div class="p-4 border-b">
                <h2 class="text-lg font-bold text-gray-800">${titulo}</h2>
            </div>
            <div class="p-4 flex-1 overflow-y-auto">
                <pre class="text-sm text-gray-700 whitespace-pre-wrap">${contenido}</pre>
            </div>
            <div class="p-4 border-t flex justify-center">
                <button onclick="cerrarModalResultados()" 
                        class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition-colors">
                    Cerrar
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// Función para cerrar modal de resultados
function cerrarModalResultados() {
    const modal = document.getElementById('modalResultadosPropagacion');
    if (modal) {
        modal.remove();
    }
}

// Función para alternar propagación
function alternarPropagacion() {
    propagacionHabilitada = !propagacionHabilitada;
    
    const boton = document.getElementById('togglePropagacion');
    const estado = document.getElementById('estadoPropagacionToggle');
    
    if (boton && estado) {
        if (propagacionHabilitada) {
            boton.classList.remove('bg-red-600', 'hover:bg-red-700');
            boton.classList.add('bg-green-600', 'hover:bg-green-700');
            boton.textContent = '🔄 Desactivar Propagación';
            estado.textContent = 'ACTIVA';
            estado.classList.remove('text-red-600');
            estado.classList.add('text-green-600');
        } else {
            boton.classList.remove('bg-green-600', 'hover:bg-green-700');
            boton.classList.add('bg-red-600', 'hover:bg-red-700');
            boton.textContent = '🔄 Activar Propagación';
            estado.textContent = 'INACTIVA';
            estado.classList.remove('text-green-600');
            estado.classList.add('text-red-600');
        }
    }
}


// Agregar respuesta como contexto
async function agregarRespuestaComoContexto() {
    if (!ultimaRespuesta || !ultimaPregunta) {
        alert("❌ No hay una respuesta válida para agregar.");
        return;
    }

    const tituloSugerido = `Respuesta: ${ultimaPregunta.substring(0, 50)}${ultimaPregunta.length > 50 ? '...' : ''}`;
    const titulo = prompt(`💡 Título para este contexto:`, tituloSugerido);
    
    if (!titulo || !titulo.trim()) {
        alert("❌ Se necesita un título.");
        return;
    }

    const esTemporal = confirm("🕒 ¿Hacer este contexto TEMPORAL?\n\n✅ SÍ = Con fecha actual\n❌ NO = Atemporal");

    try {
        const respuestaLimpia = ultimaRespuesta.split('\n\n📚 Contextos:')[0];
        
        const res = await axios.post('/contexto/', { 
            titulo: titulo.trim(), 
            texto: respuestaLimpia,
            es_temporal: esTemporal
        });
        
        const tipoContexto = esTemporal ? "TEMPORAL 🕒" : "ATEMPORAL 📋";
        alert(`✅ Respuesta agregada como contexto ${tipoContexto}!\nID: ${res.data.id}`);
        
        document.getElementById('botonAgregarRespuesta').style.display = 'none';
        mostrarContextos();
        
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}

// Mostrar todos los contextos
async function mostrarContextos() {
    try {
        const res = await axios.get('/contexto/');
        const contextos = res.data;

        const numContextos = Object.keys(contextos).length;
        
        if (numContextos === 0) {
            document.getElementById("todosContextos").innerText = "No hay contextos almacenados aún.";
            return;
        }

        const temporales = Object.values(contextos).filter(ctx => ctx.es_temporal).length;
        const atemporales = numContextos - temporales;
        
        let salida = `📊 Total: ${numContextos} contextos (🕒 ${temporales} temporales, 📋 ${atemporales} atemporales)\n\n`;
        
        for (const [id, datos] of Object.entries(contextos)) {
            const icono = datos.es_temporal ? "🕒" : "📋";
            
            salida += `${icono} ${datos.titulo}\n`;
            salida += `📄 ${datos.texto.substring(0, 150)}${datos.texto.length > 150 ? '...' : ''}\n`;
            
            if (datos.es_temporal && datos.timestamp) {
                const fecha = new Date(datos.timestamp);
                salida += `⏰ ${fecha.toLocaleString()}\n`;
            }
            
            salida += `🔑 ${datos.palabras_clave.slice(0, 3).join(', ') || 'N/A'}\n\n`;
        }

        document.getElementById("todosContextos").innerText = salida;
        
    } catch (error) {
        document.getElementById("todosContextos").innerText = `Error: ${error.message}`;
    }
}

// Búsqueda semántica
async function buscarSemantico() {
    const texto = document.getElementById('textoBusqueda').value.trim();
    if (!texto) {
        alert("Por favor escribí algo para buscar.");
        return;
    }

    try {
        const res = await axios.get(`/buscar/?texto=${encodeURIComponent(texto)}`);
        const datos = res.data;

        const container = document.getElementById('resultadosBusqueda');
        container.innerHTML = '';

        if (Object.keys(datos).length === 0) {
            container.innerHTML = "<p class='text-gray-500 italic'>No se encontraron resultados.</p>";
            return;
        }

        for (const [id, info] of Object.entries(datos)) {
            const icono = info.es_temporal ? "🕒" : "📋";
            const timestamp = info.timestamp ? `<p class="text-xs text-gray-500 mt-1">⏰ ${new Date(info.timestamp).toLocaleString()}</p>` : "";
            
            const div = document.createElement("div");
            div.className = "p-3 bg-gray-100 rounded border-l-4 border-pink-600 shadow";
            div.innerHTML = `
                <strong class="text-pink-800">${icono} ${info.titulo}</strong><br>
                <p class="text-sm text-gray-700 mt-1">${info.texto.substring(0, 120)}${info.texto.length > 120 ? '...' : ''}</p>
                ${timestamp}
            `;
            container.appendChild(div);
        }
        
    } catch (error) {
        document.getElementById('resultadosBusqueda').innerHTML = `<p class="text-red-600">Error: ${error.message}</p>`;
    }
}

// Mostrar árbol de consulta
function mostrarArbolConsulta() {
    if (ultimoSubgrafo && ultimoSubgrafo.nodes && ultimoSubgrafo.nodes.length > 0) {
        abrirModalArbol(ultimoSubgrafo);
    } else {
        alert("❌ No hay subgrafo disponible para mostrar.");
    }
}

// Abrir modal del árbol
function abrirModalArbol(subgrafo) {
    const modal = document.getElementById('modalArbol');
    modal.classList.remove('hidden');
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
        // Procesar nodos con mejor styling
        const nodes = subgrafo.nodes.map(n => {
            let color, shape = "box";
            let fontConfig = { size: 12, color: "#374151", align: "center" };
            
            if (n.group && n.group.includes("pregunta")) {
                color = { background: "#dbeafe", border: "#3b82f6" };
                shape = "diamond";
                fontConfig = { size: 14, color: "#1e40af", align: "center" };
            } else if (n.group === "temporal") {
                // Color diferenciado por tipo de contexto
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
                shadow: {
                    enabled: true,
                    size: 3,
                    x: 1,
                    y: 1,
                    color: 'rgba(0,0,0,0.1)'
                }
            };
        });

        // Procesar aristas con mejor información visual
        const edges = subgrafo.edges.map(e => {
            const pesoEfectivo = e.peso_efectivo || 0;
            const relevanciaTemp = e.relevancia_temporal || 0;
            const width = Math.max(1, pesoEfectivo * 2);
            
            // Color según tipo de relación
            const colorArista = relevanciaTemp > 0.3 ? "#4caf50" : "#2196f3";
            
            return {
                from: e.from,
                to: e.to,
                arrows: { to: { enabled: true, scaleFactor: 1.2 } },
                label: e.label || "",
                title: `Peso Estructural: ${e.peso_estructural || 0}\nRelevancia Temporal: ${relevanciaTemp}\nPeso Efectivo: ${pesoEfectivo}`,
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

        // Crear visualización mejorada
        const network = new vis.Network(container, { 
            nodes: new vis.DataSet(nodes), 
            edges: new vis.DataSet(edges) 
        }, options);

        // Ajustar vista después de renderizado
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

// Cerrar modales
function cerrarModalArbol() {
    document.getElementById('modalArbol').classList.add('hidden');
}

function cerrarModalGrafo() {
    document.getElementById('modalGrafo').classList.add('hidden');
}

// Abrir modal del grafo
function abrirModalGrafo() {
    document.getElementById('modalGrafo').classList.remove('hidden');
    setTimeout(() => cargarGrafo(), 100);
}

// Cargar y mostrar el grafo principal
async function cargarGrafo() {
    try {
        const res = await axios.get('/grafo/visualizacion/');
        const datos = res.data;

        if (!datos.nodes || datos.nodes.length === 0) {
            document.getElementById('grafo').innerHTML = 
                '<div class="flex items-center justify-center h-full text-gray-500"><p>No hay contextos para visualizar.</p></div>';
            return;
        }

        const container = document.getElementById('grafo');
        
        // Procesar nodos con colores según temporalidad y tipo
        const nodes = datos.nodes.map(node => {
            const esTemporal = node.es_temporal;
            const tipoContexto = node.tipo_contexto || 'general';
            
            // Colores diferenciados por tipo de contexto
            const coloresPorTipo = {
                'reunion': { background: esTemporal ? '#e3f2fd' : '#f5f5f5', border: esTemporal ? '#1976d2' : '#757575' },
                'tarea': { background: esTemporal ? '#fff3e0' : '#f5f5f5', border: esTemporal ? '#f57c00' : '#757575' },
                'evento': { background: esTemporal ? '#e8f5e8' : '#f5f5f5', border: esTemporal ? '#388e3c' : '#757575' },
                'proyecto': { background: esTemporal ? '#fce4ec' : '#f5f5f5', border: esTemporal ? '#c2185b' : '#757575' },
                'conocimiento': { background: esTemporal ? '#f3e5f5' : '#f5f5f5', border: esTemporal ? '#7b1fa2' : '#757575' },
                'general': { background: esTemporal ? '#bbdefb' : '#f5f5f5', border: esTemporal ? '#1976d2' : '#757575' }
            };
            
            const colores = coloresPorTipo[tipoContexto] || coloresPorTipo['general'];
            
            return {
                ...node,
                color: colores,
                font: { 
                    color: esTemporal ? '#1565c0' : '#424242', 
                    size: 12 
                },
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    size: 5,
                    x: 2,
                    y: 2,
                    color: 'rgba(0,0,0,0.1)'
                }
            };
        });

        // Procesar aristas con información visual mejorada
        const edges = datos.edges.map(edge => {
            const pesoEstructural = edge.peso_estructural || 0;
            const relevanciatemporal = edge.relevancia_temporal || 0;
            const pesoEfectivo = edge.peso_efectivo || edge.weight || 0;
            const esTemporal = relevanciatemporal > 0.3;
            
            // Color y grosor basado en peso efectivo
            let colorArista = '#90a4ae';
            let widthArista = Math.max(0.5, pesoEfectivo * 1.5);
            
            if (esTemporal) {
                const intensidad = Math.min(255, 100 + (relevanciatemporal * 400));
                colorArista = `rgb(76, ${intensidad}, 50)`;
                widthArista = Math.max(1, pesoEfectivo * 2);
            } else if (pesoEstructural > 0.5) {
                colorArista = '#2196f3';
                widthArista = Math.max(1, pesoEfectivo * 1.5);
            }
            
            const labelCompacto = `${pesoEstructural.toFixed(2)}|${relevanciatemporal.toFixed(2)}|${pesoEfectivo.toFixed(2)}`;
            
            const tooltip = [
                `Peso Estructural: ${pesoEstructural.toFixed(3)}`,
                `Relevancia Temporal: ${relevanciatemporal.toFixed(3)}`,
                `Peso Efectivo: ${pesoEfectivo.toFixed(3)}`,
                edge.tipos_contexto ? `Tipos: ${edge.tipos_contexto}` : '',
                esTemporal ? '🕒 Relación temporal' : '📋 Relación semántica'
            ].filter(Boolean).join('\n');
            
            return {
                from: edge.from,
                to: edge.to,
                color: { 
                    color: colorArista,
                    highlight: esTemporal ? '#4caf50' : '#2196f3',
                    hover: esTemporal ? '#66bb6a' : '#42a5f5'
                },
                width: widthArista,
                label: pesoEfectivo > 0.3 ? labelCompacto : '',
                title: tooltip,
                font: {
                    size: 9,
                    color: '#333333',
                    background: 'rgba(255,255,255,0.8)',
                    strokeWidth: 1,
                    strokeColor: 'rgba(255,255,255,0.9)'
                },
                arrows: {
                    to: {
                        enabled: true,
                        scaleFactor: Math.min(1.5, 0.5 + pesoEfectivo),
                        type: 'arrow'
                    }
                },
                smooth: {
                    type: 'continuous',
                    roundness: esTemporal ? 0.2 : 0.3
                }
            };
        });

        const options = {
            nodes: { 
                shape: 'box',
                margin: { top: 8, right: 8, bottom: 8, left: 8 },
                chosen: {
                    node: function(values, id, selected, hovering) {
                        if (hovering) {
                            values.shadow = true;
                            values.shadowSize = 15;
                            values.shadowColor = 'rgba(0,0,0,0.3)';
                        }
                    }
                }
            },
            edges: {
                chosen: {
                    edge: function(values, id, selected, hovering) {
                        if (hovering) {
                            values.width = values.width + 2;
                            values.shadow = true;
                            values.shadowSize = 8;
                            values.shadowColor = 'rgba(0,0,0,0.2)';
                        }
                    }
                },
                labelHighlightBold: false
            },
            physics: false, 
            interaction: {
                hover: true,
                hoverConnectedEdges: true,
                selectConnectedEdges: true,
                zoomView: true,
                dragView: true,
                dragNodes: True,//para poder mover los nodos
                tooltipDelay: 200,
                hideEdgesOnDrag: false,
                hideEdgesOnZoom: false
            },
            layout: {
                randomSeed: 1, 
                improvedLayout: false
            }
        };

        // Crear red
        networkInstance = new vis.Network(container, {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        }, options);

        // Eventos de interacción
        networkInstance.on("hoverNode", function (params) {
            const nodeId = params.node;
            const connectedNodes = networkInstance.getConnectedNodes(nodeId);
            const connectedEdges = networkInstance.getConnectedEdges(nodeId);
        });

        networkInstance.on("selectNode", function (params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
            }
        });

        networkInstance.on("selectEdge", function (params) {
            if (params.edges.length > 0) {
                const edgeId = params.edges[0];
            }
        });
        console.log(`Grafo cargado: ${nodes.length} nodos, ${edges.length} aristas (completamente estático)`);

        // Ajustar vista inicial SIN animación para evitar cualquier movimiento
        setTimeout(() => {
            if (networkInstance) {
                networkInstance.fit();  // Sin animación = sin movimiento
            }
        }, 100);
        
    } catch (error) {
        document.getElementById('grafo').innerHTML = 
            `<div class="text-red-600 p-4 text-center">
                <p class="font-semibold">❌ Error cargando grafo</p>
                <p class="text-sm mt-1">${error.message}</p>
                <button onclick="cargarGrafo()" class="mt-3 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700">
                    🔄 Reintentar
                </button>
            </div>`;
    }
}

// Cargar estadísticas
async function cargarEstadisticas() {
    const estadisticasBtn = event.target;
    const originalText = estadisticasBtn.textContent;
    
    // Mostrar que está cargando
    estadisticasBtn.textContent = '⏳ Cargando...';
    estadisticasBtn.disabled = true;
    
    // Cargar estadísticas de actualización incremental
    await cargarEstadisticasActualizacion();
    
    // Restaurar botón
    estadisticasBtn.textContent = originalText;
    estadisticasBtn.disabled = false;
}

// Event listener para cerrar modales con Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        cerrarModalGrafo();
        cerrarModalArbol();
    }
});

// Agregar conversación
async function agregarConversacion() {
    const titulo = document.getElementById('tituloConversacion').value.trim();
    const contenido = document.getElementById('contenidoConversacion').value.trim();
    
    if (!titulo || !contenido) {
        alert("Por favor completá título y contenido de la conversación.");
        return;
    }
    
    // Obtener metadatos opcionales
    const participantesText = document.getElementById('participantesConversacion').value.trim();
    const participantes = participantesText ? participantesText.split(',').map(p => p.trim()).filter(p => p) : [];
    const fecha = document.getElementById('fechaConversacion').value;
    const tipo = document.getElementById('tipoConversacion').value;
    
    const payload = {
        titulo,
        contenido,
        participantes,
        metadata: { tipo }
    };
    
    if (fecha) {
        payload.fecha = new Date(fecha).toISOString();
    }
    
    try {
        const res = await axios.post('/conversacion/', payload);
        const data = res.data;
        
        if (data.status === 'conversacion_agregada') {
            alert(`✅ Conversación fragmentada exitosamente!\n\n📊 Fragmentos creados: ${data.total_fragmentos}\n🆔 ID Conversación: ${data.conversacion_id.substring(0, 8)}...`);
            
            limpiarFormularioConversacion();
            mostrarConversaciones();
            
            // También actualizar contextos ya que los fragmentos aparecen allí
            mostrarContextos();
        } else {
            throw new Error(data.mensaje || 'Error desconocido');
        }
        
    } catch (error) {
        alert(`❌ Error: ${error.response?.data?.mensaje || error.message}`);
    }
}

// Mostrar conversaciones
async function mostrarConversaciones() {
    try {
        const res = await axios.get('/conversaciones/');
        const conversaciones = res.data;

        const numConversaciones = Object.keys(conversaciones).length;
        
        if (numConversaciones === 0) {
            document.getElementById("todasConversaciones").innerText = "No hay conversaciones almacenadas aún.";
            return;
        }
        
        let salida = `📊 Total: ${numConversaciones} conversaciones\n\n`;
        
        for (const [id, datos] of Object.entries(conversaciones)) {
            const fecha = datos.fecha ? new Date(datos.fecha) : new Date();
            // Verificar si participantes existe antes de usar .join()
            const participantesStr = datos.participantes && datos.participantes.length > 0 
                ? datos.participantes.join(', ') 
                : 'N/A';
            
            const tipoIcon = {
                'reunion': '👥',
                'entrevista': '🎤', 
                'brainstorm': '💡',
                'planning': '📋',
                'general': '📄'
            }[datos.metadata?.tipo] || '📄';
            
            salida += `${tipoIcon} ${datos.titulo || 'Sin título'}\n`;
            salida += `📊 ${datos.total_fragmentos || 0} fragmentos\n`;
            salida += `👥 ${participantesStr}\n`;
            salida += `⏰ ${fecha.toLocaleString()}\n`;
            salida += `🔑 ID: ${id.substring(0, 8)}...\n\n`;
        }

        document.getElementById("todasConversaciones").innerText = salida;
        
    } catch (error) {
        console.error("Error al mostrar conversaciones:", error);
        document.getElementById("todasConversaciones").innerText = 
            `Error al cargar conversaciones: ${error.message}`;
    }
}

// Limpiar formulario de conversación
function limpiarFormularioConversacion() {
    document.getElementById('tituloConversacion').value = '';
    document.getElementById('contenidoConversacion').value = '';
    document.getElementById('participantesConversacion').value = '';
    document.getElementById('fechaConversacion').value = '';
    document.getElementById('tipoConversacion').value = 'general';
    document.getElementById('formAgregarConversacion').classList.add('hidden');
}

// FUNCIONALIDAD DE DATASETS 
// Subir archivo de dataset
async function subirDataset() {
    const fileInput = document.getElementById('fileDataset');
    const file = fileInput.files[0];
    
    if (!file) {
        alert("Por favor selecciona un archivo JSON.");
        return;
    }
    
    if (!file.name.endsWith('.json')) {
        alert("Solo se permiten archivos .json");
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('sobrescribir', 'false');
    
    const resultadosDiv = document.getElementById('resultadosDataset');
    resultadosDiv.innerHTML = "📤 Subiendo y procesando archivo...";
    
    try {
        const response = await axios.post('/dataset/upload/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 60000 // 60 segundos para archivos grandes
        });
        
        const data = response.data;
        
        if (data.status === 'archivo_procesado') {
            const stats = data.estadisticas;
            const duracion = stats.tiempo_fin && stats.tiempo_inicio ? 
                ((new Date(stats.tiempo_fin) - new Date(stats.tiempo_inicio)) / 1000).toFixed(2) : 'N/A';
            
            resultadosDiv.innerHTML = `
                <div class="space-y-2 text-sm">
                    <div class="font-medium text-green-700">✅ Dataset procesado exitosamente</div>
                    <div class="grid grid-cols-2 gap-2 text-xs">
                        <div>📁 Archivo: ${data.archivo}</div>
                        <div>🏷️ Dominio: ${stats.dominio}</div>
                        <div>💬 Conversaciones: ${stats.conversaciones_procesadas}</div>
                        <div>🔗 Fragmentos: ${stats.fragmentos_generados}</div>
                        <div>⏱️ Tiempo: ${duracion}s</div>
                        <div>❌ Errores: ${stats.errores?.length || 0}</div>
                    </div>
                    ${stats.errores && stats.errores.length > 0 ? 
                        `<div class="text-red-600 text-xs mt-2">
                            <details>
                                <summary>Ver errores (${stats.errores.length})</summary>
                                <div class="mt-1 max-h-32 overflow-y-auto">
                                    ${stats.errores.slice(0, 5).map(err => `<div>• ${err}</div>`).join('')}
                                    ${stats.errores.length > 5 ? `<div>... y ${stats.errores.length - 5} más</div>` : ''}
                                </div>
                            </details>
                        </div>` : ''
                    }
                </div>
            `;
            
            // Actualizar listas
            mostrarConversaciones();
            mostrarContextos();
            
        } else {
            resultadosDiv.innerHTML = `<div class="text-red-600 text-sm">❌ Error: ${data.mensaje}</div>`;
        }
        
    } catch (error) {
        resultadosDiv.innerHTML = `<div class="text-red-600 text-sm">❌ Error: ${error.response?.data?.mensaje || error.message}</div>`;
    } finally {
        // Limpiar input
        fileInput.value = '';
    }
}

// Validar JSON sin procesarlo
async function validarJSON() {
    const jsonText = document.getElementById('jsonDataset').value.trim();
    
    if (!jsonText) {
        alert("Por favor pega el JSON del dataset.");
        return;
    }
    
    let dataset;
    try {
        dataset = JSON.parse(jsonText);
    } catch (e) {
        alert("JSON inválido: " + e.message);
        return;
    }
    
    const resultadosDiv = document.getElementById('resultadosDataset');
    resultadosDiv.innerHTML = "🔍 Validando formato...";
    
    try {
        const response = await axios.post('/dataset/validar/', dataset);
        const data = response.data;
        
        if (data.valido) {
            resultadosDiv.innerHTML = `
                <div class="space-y-2 text-sm">
                    <div class="font-medium text-green-700">✅ Dataset válido</div>
                    <div class="grid grid-cols-2 gap-2 text-xs">
                        <div>🏷️ Dominio: ${data.dominio}</div>
                        <div>💬 Conversaciones: ${data.total_conversaciones}</div>
                    </div>
                    <div class="text-green-600 text-xs">
                        ✨ El dataset está listo para ser procesado
                    </div>
                </div>
            `;
        } else {
            resultadosDiv.innerHTML = `
                <div class="space-y-2 text-sm">
                    <div class="font-medium text-red-700">❌ Dataset inválido</div>
                    <div class="text-red-600 text-xs">
                        <div class="font-medium mb-1">Errores encontrados:</div>
                        ${data.errores.map(err => `<div>• ${err}</div>`).join('')}
                    </div>
                </div>
            `;
        }
        
    } catch (error) {
        resultadosDiv.innerHTML = `<div class="text-red-600 text-sm">❌ Error: ${error.message}</div>`;
    }
}

// Actualizar información según vista seleccionada
function actualizarVistaSeleccionada(vista) {
    vistaActual = vista;
    
    const selectorConv = document.getElementById('selectorConversacion');
    const infoNivel = document.getElementById('infoNivelActual');
    
    // Mostrar/ocultar selector de conversación
    if (vista === 'micro-filtrada') {
        selectorConv.classList.remove('hidden');
        cargarListaConversacionesParaFiltro();
    } else {
        selectorConv.classList.add('hidden');
    }
    
    // Actualizar información del nivel
    const infoTextos = {
        'macro': '<p><strong>🌐 Nivel Macro:</strong> Cada nodo = conversación completa. Las aristas muestran relaciones calculadas entre fragmentos de diferentes conversaciones.</p>',
        'micro': '<p><strong>🔬 Nivel Micro:</strong> Cada nodo = fragmento individual. Muestra todas las conexiones semánticas y temporales con máxima granularidad.</p>',
        'micro-filtrada': '<p><strong>🎯 Micro Filtrada:</strong> Solo fragmentos de una conversación específica. Útil para analizar la estructura interna de una conversación.</p>'
    };
    
    infoNivel.innerHTML = infoTextos[vista] || infoTextos['macro'];
}

// Cargar lista de conversaciones para el filtro
async function cargarListaConversacionesParaFiltro() {
    if (Object.keys(conversacionesList).length === 0) {
        try {
            const res = await axios.get('/conversaciones/');
            conversacionesList = res.data;
        } catch (error) {
            console.error('Error cargando conversaciones:', error);
            return;
        }
    }
    
    const selector = document.getElementById('conversacionFiltro');
    selector.innerHTML = '<option value="">Seleccionar conversación...</option>';
    
    for (const [id, datos] of Object.entries(conversacionesList)) {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = `${datos.titulo} (${datos.total_fragmentos} frags)`;
        selector.appendChild(option);
    }
}

// Abrir modal con vista doble nivel
function abrirModalGrafoDobleNivel() {
    document.getElementById('modalGrafo').classList.remove('hidden');
    setTimeout(() => cargarGrafoDobleNivel(), 100);
}

// Cargar grafo según la vista actual
async function cargarGrafoDobleNivel() {
    const container = document.getElementById('grafo');
    container.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><p>Cargando grafo...</p></div>';
    
    try {
        let endpoint = '';
        let datos = null;
        
        // Determinar endpoint según vista
        switch(vistaActual) {
            case 'macro':
                endpoint = '/grafo/macro/conversaciones/';
                break;
            case 'micro':
                endpoint = '/grafo/micro/fragmentos/';
                break;
            case 'micro-filtrada':
                const conversacionId = document.getElementById('conversacionFiltro').value;
                if (!conversacionId) {
                    container.innerHTML = '<div class="flex items-center justify-center h-full text-orange-500"><p>⚠️ Selecciona una conversación para filtrar</p></div>';
                    return;
                }
                endpoint = `/grafo/micro/conversacion/${conversacionId}`;
                break;
            default:
                endpoint = '/grafo/macro/conversaciones/';
        }
        
        const res = await axios.get(endpoint);
        datos = res.data;
        
        if (!datos.nodes || datos.nodes.length === 0) {
            container.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><p>No hay datos para visualizar en esta vista.</p></div>';
            return;
        }
        
        // Actualizar header del modal
        actualizarHeaderGrafo(datos);
        
        // Actualizar leyenda
        actualizarLeyendaGrafo();
        
        // Renderizar grafo
        renderizarGrafoDobleNivel(datos, container);
        
    } catch (error) {
        container.innerHTML = `
            <div class="text-red-600 p-4 text-center">
                <p class="font-semibold">❌ Error cargando vista ${vistaActual}</p>
                <p class="text-sm mt-1">${error.message}</p>
                <button onclick="cargarGrafoDobleNivel()" class="mt-3 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700">
                    🔄 Reintentar
                </button>
            </div>`;
    }
}

// Actualizar header del modal según la vista
function actualizarHeaderGrafo(datos) {
    const meta = datos.meta || {};
    
    const titulos = {
        'macro': '🌐 Vista Macro - Conversaciones',
        'micro': '🔬 Vista Micro - Fragmentos Completa', 
        'micro-filtrada': '🎯 Vista Micro - Fragmentos Filtrada'
    };
    
    const descripciones = {
        'macro': 'Cada nodo representa una conversación completa',
        'micro': 'Cada nodo representa un fragmento individual',
        'micro-filtrada': `Fragmentos de: ${meta.conversacion_titulo || 'Conversación seleccionada'}`
    };
    
    document.getElementById('tituloVistaGrafo').textContent = titulos[vistaActual] || titulos['macro'];
    document.getElementById('descripcionVistaGrafo').textContent = descripciones[vistaActual] || descripciones['macro'];
    
    // Actualizar métricas
    document.getElementById('totalNodos').textContent = datos.nodes?.length || 0;
    document.getElementById('totalAristas').textContent = datos.edges?.length || 0;
}

// Actualizar leyenda según la vista
function actualizarLeyendaGrafo() {
    const leyendaMacro = document.getElementById('leyendaMacro');
    const leyendaMicro = document.getElementById('leyendaMicro');
    
    if (vistaActual === 'macro') {
        leyendaMacro.classList.remove('hidden');
        leyendaMicro.classList.add('hidden');
        
        leyendaMacro.innerHTML = `
            <div>
                <p class="font-semibold text-blue-800 mb-2">💬 Nodos por Tipo de Conversación:</p>
                <div class="space-y-1 text-xs">
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-green-100 border border-green-600 rounded mr-2 flex items-center justify-center text-xs">👥</div>
                        <span>Reuniones</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-blue-100 border border-blue-600 rounded mr-2 flex items-center justify-center text-xs">🎤</div>
                        <span>Entrevistas</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-purple-100 border border-purple-600 rounded mr-2 flex items-center justify-center text-xs">💡</div>
                        <span>Brainstorms</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-orange-100 border border-orange-600 rounded mr-2 flex items-center justify-center text-xs">📋</div>
                        <span>Planning</span>
                    </div>
                </div>
            </div>
            <div>
                <p class="font-semibold text-blue-800 mb-2">🔗 Aristas entre Conversaciones:</p>
                <div class="space-y-1 text-xs">
                    <div class="flex items-center">
                        <div class="w-8 h-1 bg-green-500 mr-2 rounded"></div>
                        <span>Relaciones temporales</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-8 h-1 bg-blue-400 mr-2 rounded"></div>
                        <span>Relaciones semánticas</span>
                    </div>
                    <div class="text-xs text-gray-600 mt-2 p-2 bg-gray-100 rounded">
                        <strong>Formato:</strong> P=Peso promedio | C=Conexiones de fragmentos
                    </div>
                </div>
            </div>
        `;
    } else {
        leyendaMacro.classList.add('hidden');
        leyendaMicro.classList.remove('hidden');
        
        leyendaMicro.innerHTML = `
            <div>
                <p class="font-semibold text-purple-800 mb-2">🧩 Fragmentos por Tipo:</p>
                <div class="space-y-1 text-xs">
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-blue-100 border border-blue-600 rounded mr-2 flex items-center justify-center text-xs">👥</div>
                        <span>Reunión</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-green-100 border border-green-600 rounded mr-2 flex items-center justify-center text-xs">⚖️</div>
                        <span>Decisión</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-orange-100 border border-orange-600 rounded mr-2 flex items-center justify-center text-xs">⚡</div>
                        <span>Acción</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-4 h-4 bg-red-100 border border-red-600 rounded mr-2 flex items-center justify-center text-xs">❓</div>
                        <span>Pregunta</span>
                    </div>
                </div>
            </div>
            <div>
                <p class="font-semibold text-purple-800 mb-2">🔗 Conexiones entre Fragmentos:</p>
                <div class="space-y-1 text-xs">
                    <div class="flex items-center">
                        <div class="w-8 h-1 bg-green-500 mr-2 rounded"></div>
                        <span>🕒 Con relevancia temporal</span>
                    </div>
                    <div class="flex items-center">
                        <div class="w-8 h-1 bg-blue-400 mr-2 rounded"></div>
                        <span>📋 Solo semánticas</span>
                    </div>
                    <div class="text-xs text-gray-600 mt-2 p-2 bg-gray-100 rounded">
                        <strong>Formato:</strong> E=Estructural | T=Temporal | W=Peso efectivo
                    </div>
                </div>
            </div>
        `;
    }
}

// Renderizar grafo con configuraciones específicas por vista
function renderizarGrafoDobleNivel(datos, container) {
    try {
        // Procesar nodos según la vista
        const nodes = datos.nodes.map(node => {
            let config = {
                ...node,
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    size: 5,
                    x: 2,
                    y: 2,
                    color: 'rgba(0,0,0,0.1)'
                }
            };
            
            if (vistaActual === 'macro') {
                // Configuración para vista macro (conversaciones)
                const tipoConv = node.tipo_conversacion || 'general';
                const coloresMacro = {
                    'reunion': { background: '#e8f5e8', border: '#4caf50' },
                    'entrevista': { background: '#e3f2fd', border: '#2196f3' },
                    'brainstorm': { background: '#f3e5f5', border: '#9c27b0' },
                    'planning': { background: '#fff3e0', border: '#ff9800' },
                    'general': { background: '#f5f5f5', border: '#757575' }
                };
                
                config.color = coloresMacro[tipoConv] || coloresMacro['general'];
                config.size = Math.max(20, Math.min(50, (node.total_fragmentos || 1) * 4));
                config.font = { size: 12, color: '#1565c0' };
                
            } else {
                // Configuración para vista micro (fragmentos) - usar la existente
                const esTemporal = node.group === 'temporal';
                config.color = esTemporal ? 
                    { background: '#e3f2fd', border: '#1976d2' } : 
                    { background: '#f5f5f5', border: '#757575' };
                config.font = { size: 10, color: esTemporal ? '#1565c0' : '#424242' };
            }
            
            return config;
        });
        
        // Procesar aristas
        const edges = datos.edges.map(edge => {
            let config = { ...edge };
            
            if (vistaActual === 'macro') {
                // Aristas para conversaciones - más gruesas y destacadas
                config.width = Math.max(1, (edge.peso_total || 1) * 1.5);
                config.color = edge.es_temporal ? '#4caf50' : '#2196f3';
                config.font = {
                    size: 11,
                    background: 'rgba(255,255,255,0.9)',
                    strokeWidth: 1,
                    strokeColor: 'rgba(255,255,255,0.9)'
                };
            } else {
                // Aristas para fragmentos - configuración existente
                const relevanciaTemp = edge.relevancia_temporal || 0;
                config.width = Math.max(1, (edge.peso_efectivo || 0) * 2);
                config.color = relevanciaTemp > 0.3 ? '#4caf50' : '#2196f3';
                config.font = { size: 9 };
            }
            
            config.arrows = { to: { enabled: true, scaleFactor: 1.2 } };
            config.smooth = { type: 'continuous', roundness: 0.3 };
            
            return config;
        });
        
        // Configuración de layout según vista
        const layoutConfig = vistaActual === 'macro' ? 
            {
                // Layout para conversaciones - más espacio
                improvedLayout: true,
                randomSeed: 1,
                avoidOverlap: 0.5
            } : 
            {
                // Layout para fragmentos - más compacto
                improvedLayout: false,
                randomSeed: 1
            };
        
        const options = {
            nodes: { 
                shape: 'box',
                margin: { top: 8, right: 8, bottom: 8, left: 8 }
            },
            edges: {
                labelHighlightBold: false,
                selectionWidth: 3
            },
            physics: false,
            interaction: {
                hover: true,
                hoverConnectedEdges: true,
                selectConnectedEdges: true,
                zoomView: true,
                dragView: true,
                dragNodes: true, // Solo permitir arrastrar en todas las vistas
                tooltipDelay: 200
            },
            layout: layoutConfig
        };

        // Crear red
        networkInstance = new vis.Network(container, {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        }, options);

        // Eventos específicos por vista
        if (vistaActual === 'macro') {
            // En vista macro, doble clic cambia a vista micro filtrada
            networkInstance.on("doubleClick", function (params) {
                if (params.nodes.length > 0) {
                    const conversacionId = params.nodes[0];
                    
                    // Cambiar a vista micro filtrada
                    document.getElementById('vistaMicroFiltrada').checked = true;
                    document.getElementById('conversacionFiltro').value = conversacionId;
                    actualizarVistaSeleccionada('micro-filtrada');
                    
                    // Recargar grafo con nueva vista
                    setTimeout(() => cargarGrafoDobleNivel(), 100);
                }
            });
        }
        console.log(`Grafo ${vistaActual} cargado: ${nodes.length} nodos, ${edges.length} aristas`);

        // Ajustar vista inicial
        setTimeout(() => {
            if (networkInstance) {
                networkInstance.fit();
            }
        }, 100);
        
    } catch (error) {
        container.innerHTML = `
            <div class="text-red-600 p-4 text-center">
                <p class="font-semibold">❌ Error renderizando grafo</p>
                <p class="text-sm mt-1">${error.message}</p>
            </div>`;
    }
}

// Cambiar vista rápidamente
function cambiarVistaGrafo() {
    const vistas = ['macro', 'micro', 'micro-filtrada'];
    const indiceActual = vistas.indexOf(vistaActual);
    const siguienteIndice = (indiceActual + 1) % vistas.length;
    const siguienteVista = vistas[siguienteIndice];
    
    // Actualizar radio button
    document.getElementById(`vista${siguienteVista.charAt(0).toUpperCase() + siguienteVista.slice(1).replace('-', '')}`).checked = true;
    actualizarVistaSeleccionada(siguienteVista);
    
    // Recargar grafo
    cargarGrafoDobleNivel();
}

// Cargar estadísticas de doble nivel
async function cargarEstadisticasDobleNivel() {
    try {
        const res = await axios.get('/estadisticas/doble-nivel/');
        estadisticasDobleNivel = res.data;
        
        const macro = estadisticasDobleNivel.nivel_macro;
        const micro = estadisticasDobleNivel.nivel_micro;
        const relaciones = estadisticasDobleNivel.relaciones;
        const metricas = estadisticasDobleNivel.metricas;
        
        document.getElementById('estadisticas').innerHTML = `
            <div class="space-y-3 text-xs">
                <!-- Nivel Macro -->
                <div class="border-b pb-2">
                    <div class="font-medium text-purple-700 mb-1">🌐 Nivel Macro (Conversaciones)</div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>Total: <span class="font-bold text-purple-600">${macro.total_conversaciones}</span></div>
                        <div>Complejas: <span class="font-bold">${macro.conversaciones_complejas}</span></div>
                    </div>
                    <div class="mt-1 text-xs text-gray-600">
                        Tipos: ${Object.entries(macro.tipos_conversaciones).map(([tipo, count]) => `${tipo}(${count})`).join(', ')}
                    </div>
                </div>
                
                <!-- Nivel Micro -->
                <div class="border-b pb-2">
                    <div class="font-medium text-blue-700 mb-1">🔬 Nivel Micro (Fragmentos)</div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>Total: <span class="font-bold text-blue-600">${micro.total_fragmentos}</span></div>
                        <div>Temporales: <span class="font-bold text-green-600">${micro.fragmentos_temporales}</span></div>
                    </div>
                    <div class="mt-1 text-xs text-gray-600">
                        Top tipos: ${Object.entries(micro.tipos_fragmentos)
                            .sort(([,a], [,b]) => b - a)
                            .slice(0, 3)
                            .map(([tipo, count]) => `${tipo}(${count})`)
                            .join(', ')}
                    </div>
                </div>
                
                <!-- Relaciones -->
                <div class="border-b pb-2">
                    <div class="font-medium text-orange-700 mb-1">🔗 Relaciones</div>
                    <div class="grid grid-cols-2 gap-2">
                        <div>Internas: <span class="font-bold text-orange-600">${relaciones.intra_conversacion}</span></div>
                        <div>Entre conv: <span class="font-bold text-red-600">${relaciones.inter_conversacion}</span></div>
                    </div>
                </div>
                
                <!-- Métricas Calculadas -->
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
        document.getElementById('estadisticas').innerHTML = 
            `<p class="text-red-600 text-xs">Error cargando stats doble nivel: ${error.message}</p>`;
    }
}

// Mostrar estadísticas de actualización incremental
async function cargarEstadisticasActualizacion() {
    try {
        const res = await axios.get('/estadisticas-actualizacion/');
        
        if (res.data.status === 'success') {
            const stats = res.data.estadisticas;
            
            const estadisticasHtml = `
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
                        <span>🕒 Temporales:</span>
                        <span class="font-bold text-blue-600">${stats.contextos_temporales || 0}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>📋 Atemporales:</span>
                        <span class="font-bold text-gray-600">${stats.contextos_atemporales || 0}</span>
                    </div>
                </div>
                <div class="mt-3 p-2 bg-green-50 border border-green-200 rounded text-xs">
                    <div class="font-medium text-green-800">✅ Beneficios Actualización Incremental:</div>
                    <div class="text-green-700 mt-1">
                        • Solo calcula relaciones del nodo nuevo (O(n) vs O(n²))<br>
                        • Muestra estadísticas de conexiones creadas<br>
                        • Mantiene rendimiento constante al escalar
                    </div>
                </div>
            `;
            
            document.getElementById('estadisticas').innerHTML = estadisticasHtml;
            
        } else {
            document.getElementById('estadisticas').innerHTML = 
                `<p class="text-red-600 text-xs">❌ ${res.data.error}</p>`;
        }
        
    } catch (error) {
        document.getElementById('estadisticas').innerHTML = 
            `<p class="text-red-600 text-xs">❌ Error: ${error.message}</p>`;
    }
}

// Cerrar modal con Escape también para propagación
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        cerrarModalGrafo();
        cerrarModalArbol();
        cerrarModalResultados();
        ocultarFormularioContextosRelacionados();
        ocultarFormularioCaminos();
    }
});