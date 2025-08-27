// Variables globales
let ultimaRespuesta = "";
let ultimaPregunta = "";
let networkInstance = null;
let ultimoSubgrafo = null;

// Event listeners principales
document.addEventListener('DOMContentLoaded', function() {
    // Toggle formulario agregar contexto
    document.getElementById('toggleAgregarContexto').addEventListener('click', function() {
        const form = document.getElementById('formAgregarContexto');
        form.classList.toggle('hidden');
        if (!form.classList.contains('hidden')) {
            document.getElementById('titulo').focus();
        }
    });

    // Cancelar agregar contexto
    document.getElementById('cancelarAgregar').addEventListener('click', function() {
        limpiarFormulario();
    });

    // Enter en campos de input
    document.getElementById('pregunta').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') preguntar();
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
});

// Función principal para preguntar
async function preguntar() {
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
    
    respuestaDiv.innerHTML = "🧠 Analizando intención temporal y buscando contextos relevantes...";
    botonDiv.style.display = 'none';
    botonArbolDiv.style.display = 'none';
    panelEstrategia.classList.add('hidden');

    try {
        const res = await axios.get(`/preguntar/?pregunta=${encodeURIComponent(pregunta)}`);
        
        respuestaDiv.innerText = res.data.respuesta;
        ultimaRespuesta = res.data.respuesta;
        ultimaPregunta = pregunta;
        
        // Mostrar información de estrategia aplicada
        if (res.data.analisis_intencion && res.data.estrategia_aplicada) {
            const analisis = res.data.analisis_intencion;
            const estrategia = res.data.estrategia_aplicada;
            
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
                </div>
            `;
            
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

// Agregar contexto optimizado
async function agregarContexto() {
    const titulo = document.getElementById('titulo').value.trim();
    const texto = document.getElementById('texto').value.trim();
    
    if (!titulo || !texto) {
        alert("Por favor completá título y texto.");
        return;
    }
    
    // Determinar modo temporal
    const modoTemporal = document.querySelector('input[name="modoTemporal"]:checked').value;
    const referenciaManual = document.getElementById('referenciaManualInput').value.trim();
    
    // Preparar payload
    const payload = { titulo, texto };
    
    if (modoTemporal === 'auto') {
        payload.es_temporal = null; // Auto-detección
    } else if (modoTemporal === 'temporal') {
        payload.es_temporal = true;
        if (referenciaManual) {
            payload.referencia_temporal = referenciaManual;
        }
    } else { // atemporal
        payload.es_temporal = false;
    }
    
    try {
        const res = await axios.post('/contexto/', payload);
        const data = res.data;
        
        const tipoContexto = data.es_temporal ? "TEMPORAL 🕒" : "ATEMPORAL 📋";
        alert(`✅ Contexto ${tipoContexto} agregado!\nID: ${data.id}`);
        
        limpiarFormulario();
        mostrarContextos();
        
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
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
            const width = Math.max(2, pesoEfectivo * 8);
            
            // Color según tipo de relación
            const colorArista = relevanciaTemp > 0.1 ? "#4caf50" : "#2196f3";
            
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
                    highlight: relevanciaTemp > 0.1 ? "#66bb6a" : "#42a5f5"
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
            const esTemporal = relevanciatemporal > 0.1;
            
            // Color y grosor basado en peso efectivo
            let colorArista = '#90a4ae';
            let widthArista = Math.max(1, pesoEfectivo * 4);
            
            if (esTemporal) {
                const intensidad = Math.min(255, 100 + (relevanciatemporal * 400));
                colorArista = `rgb(76, ${intensidad}, 50)`;
                widthArista = Math.max(2, pesoEfectivo * 6);
            } else if (pesoEstructural > 0.5) {
                colorArista = '#2196f3';
                widthArista = Math.max(2, pesoEfectivo * 5);
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
                    roundness: esTemporal ? 0.2 : 0.1
                }
            };
        });

        // CONFIGURACIÓN COMPLETAMENTE ESTÁTICA - CERO FÍSICAS
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
            // FÍSICAS COMPLETAMENTE DESHABILITADAS
            physics: false,  // Forma más directa de deshabilitar
            interaction: {
                hover: true,
                hoverConnectedEdges: true,
                selectConnectedEdges: true,
                zoomView: true,
                dragView: true,
                dragNodes: false,
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
                console.log(`Nodo seleccionado: ${nodeId}`);
            }
        });

        networkInstance.on("selectEdge", function (params) {
            if (params.edges.length > 0) {
                const edgeId = params.edges[0];
                console.log(`Arista seleccionada: ${edgeId}`);
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
    try {
        const res = await axios.get('/estadisticas/');
        const stats = res.data;
        
        document.getElementById('estadisticas').innerHTML = `
            <div class="space-y-2">
                <div class="flex justify-between">
                    <span>📊 Contextos:</span>
                    <span class="font-bold text-green-600">${stats.total_contextos}</span>
                </div>
                <div class="flex justify-between">
                    <span>🕒 Temporales:</span>
                    <span class="font-bold text-blue-600">${stats.contextos_temporales || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span>📋 Atemporales:</span>
                    <span class="font-bold text-gray-600">${stats.contextos_atemporales || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span>🔗 Relaciones:</span>
                    <span class="font-bold text-blue-600">${stats.total_relaciones}</span>
                </div>
            </div>
        `;
        
    } catch (error) {
        document.getElementById('estadisticas').innerHTML = 
            `<p class="text-red-600 text-xs">Error: ${error.message}</p>`;
    }
}

// Función helper para limpiar formulario
function limpiarFormulario() {
    document.getElementById('titulo').value = '';
    document.getElementById('texto').value = '';
    document.getElementById('referenciaManualInput').value = '';
    document.getElementById('referenciaManualContainer').classList.add('hidden');
    document.querySelector('#modoAuto').checked = true;
    document.getElementById('formAgregarContexto').classList.add('hidden');
}

// Event listener para cerrar modales con Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        cerrarModalGrafo();
        cerrarModalArbol();
    }
});