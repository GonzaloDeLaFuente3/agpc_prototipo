// Variables globales
let ultimaRespuesta = "";
let ultimaPregunta = "";
let networkInstance = null;
let mostrandoLabels = true;
let ultimoSubgrafo = null;
let timeoutPreview = null;
let timeoutIntencion = null;

// Event listeners para cuando la página carga
document.addEventListener('DOMContentLoaded', function() {
    // Toggle para mostrar/ocultar formulario de agregar contexto
    document.getElementById('toggleAgregarContexto').addEventListener('click', function() {
        const form = document.getElementById('formAgregarContexto');
        form.classList.toggle('hidden');
        if (!form.classList.contains('hidden')) {
            document.getElementById('titulo').focus();
        }
    });

    // Cancelar agregar contexto
    document.getElementById('cancelarAgregar').addEventListener('click', function() {
        document.getElementById('formAgregarContexto').classList.add('hidden');
        document.getElementById('titulo').value = '';
        document.getElementById('texto').value = '';
        document.getElementById('esTemporal').checked = false;
    });

    // Enter en campos de input
    document.getElementById('pregunta').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') preguntar();
    });

    document.getElementById('textoBusqueda').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') buscarSemantico();
    });

    // Listener para el checkbox de labels
    document.getElementById('mostrarLabelsAristas').addEventListener('change', function() {
        mostrandoLabels = this.checked;
        if (networkInstance) {
            cargarGrafo(); // Recargar con la nueva configuración
        }
    });
    // Nuevos listeners para radio buttons
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

async function agregarContexto() {
    // Redirigir a la nueva función
    return agregarContextoMejorado();
}

async function actualizarPesosTemporal() {
    const boton = event.target;
    const textoOriginal = boton.textContent;
    boton.textContent = "⏳ Actualizando...";
    boton.disabled = true;

    try {
        const res = await axios.post('/grafo/actualizar-temporal/');
        const resultado = res.data;
        
        // Mostrar resultado
        const container = document.getElementById('resultadoActualizacion');
        container.innerHTML = `
            <div class="text-green-700">
                <p class="font-semibold">✅ Actualización completada</p>
                <p>🕒 Tiempo: ${resultado.duracion_segundos}s</p>
                <p>🔗 Aristas totales: ${resultado.total_aristas}</p>
                <p>⚡ Aristas temporales: ${resultado.aristas_temporales}</p>
                <p class="text-xs text-gray-600 mt-1">Actualizado: ${new Date(resultado.timestamp).toLocaleString()}</p>
            </div>
        `;
        container.classList.remove('hidden');
        
        setTimeout(() => {
            container.classList.add('hidden');
        }, 5000);
        
        cargarEstadisticas();
        
    } catch (error) {
        alert(`❌ Error al actualizar pesos temporales: ${error.message}`);
    } finally {
        boton.textContent = textoOriginal;
        boton.disabled = false;
    }
}

async function preguntar() {
    console.log("🔍 INICIO - función preguntar() con análisis de intención");
    
    const pregunta = document.getElementById('pregunta').value;
    console.log("📝 Pregunta:", pregunta);

    if (!pregunta.trim()) {
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
        console.log("📡 Enviando request con análisis de intención...");
        const res = await axios.get(`/preguntar/?pregunta=${encodeURIComponent(pregunta)}`);
        
        console.log("✅ Respuesta completa del servidor:");
        console.log(JSON.stringify(res.data, null, 2));
        
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
                        <div class="font-medium">🧠 Intención Detectada:</div>
                        <div>${analisis.intencion_temporal?.toUpperCase() || 'N/A'}</div>
                        <div class="text-gray-600">Confianza: ${((analisis.confianza || 0) * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                        <div class="font-medium">⚙️ Factor Aplicado:</div>
                        <div>${(estrategia.factor_refuerzo || 1.0)}x</div>
                        <div class="text-gray-600">
                            ${estrategia.factor_refuerzo > 1.5 ? '🕒 Prioridad temporal' : 
                              estrategia.factor_refuerzo < 0.5 ? '📋 Prioridad semántica' : 
                              '⚖️ Balance mixto'}
                        </div>
                    </div>
                </div>
                <div class="mt-2 text-xs text-gray-700">
                    <strong>Explicación:</strong> ${estrategia.explicacion || analisis.explicacion || 'N/A'}
                </div>
            `;
            
            contenidoEstrategia.innerHTML = estrategiaHtml;
            panelEstrategia.classList.remove('hidden');
            
            console.log("✅ Panel de estrategia mostrado");
        }
        
        // Mostrar botón agregar respuesta si la respuesta es válida
        if (res.data.respuesta && !res.data.respuesta.startsWith("[ERROR]")) {
            botonDiv.style.display = 'block';
            console.log("✅ Botón agregar respuesta mostrado");
        } else {
            console.log("❌ Botón agregar respuesta NO mostrado - respuesta inválida");
        }

        // Análisis del subgrafo (igual que antes)
        const subgrafo = res.data.subgrafo;
        console.log("\n🌳 === ANÁLISIS DEL SUBGRAFO ===");
        console.log("subgrafo:", subgrafo);
        
        if (subgrafo && subgrafo.nodes && subgrafo.nodes.length > 0) {
            ultimoSubgrafo = subgrafo;
            botonArbolDiv.style.display = 'block';
            console.log("✅ ÉXITO: Botón de árbol MOSTRADO");
        } else {
            ultimoSubgrafo = null;
            botonArbolDiv.style.display = 'none';
            console.log("❌ FALLO: Botón de árbol NO mostrado");
        }
        
        // Debug del análisis de intención
        if (res.data.debug) {
            console.log("\n🔧 === DEBUG INFO ===");
            console.log("Intención temporal:", res.data.debug.intencion_temporal);
            console.log("Factor refuerzo:", res.data.debug.factor_refuerzo);
            console.log(res.data.debug);
        }
        
        console.log("\n✅ FINAL - función preguntar() completada con análisis de intención");
        
    } catch (error) {
        console.log("💥 ERROR en preguntar():");
        console.error(error);
        respuestaDiv.innerText = `Error: ${error.message}`;
        botonDiv.style.display = 'none';
        botonArbolDiv.style.display = 'none';
        panelEstrategia.classList.add('hidden');
    }
}

function mostrarArbolConsulta() {
    console.log("\n🌳 === MOSTRAR ÁRBOL CONSULTA ===");
    console.log("ultimoSubgrafo:", ultimoSubgrafo);
    
    if (ultimoSubgrafo && ultimoSubgrafo.nodes && ultimoSubgrafo.nodes.length > 0) {
        console.log("✅ Llamando a abrirModalArbol()...");
        abrirModalArbol(ultimoSubgrafo);
    } else {
        console.log("❌ No se puede mostrar - ultimoSubgrafo inválido");
        alert("❌ No hay subgrafo disponible para mostrar.\n\nVerifica la consola del navegador (F12) para más detalles.");
    }
}

function abrirModalArbol(subgrafo) {
    console.log("Abriendo modal con subgrafo:", subgrafo); // Debug
    
    const modal = document.getElementById('modalArbol');
    modal.classList.remove('hidden');

    const container = document.getElementById('arbolConsulta');

    if (!subgrafo || !subgrafo.nodes || subgrafo.nodes.length === 0) {
        const errorMsg = subgrafo?.meta?.error || "Subgrafo vacío o inválido";
        container.innerHTML = `
            <div class="flex items-center justify-center h-full text-gray-500 flex-col">
                <p class="text-lg mb-2">❌ No se puede mostrar el árbol</p>
                <p class="text-sm">${errorMsg}</p>
                ${subgrafo?.meta ? `<p class="text-xs mt-2 text-gray-400">Meta: ${JSON.stringify(subgrafo.meta)}</p>` : ''}
            </div>
        `;
        return;
    }

    try {
        // Nodos estilizados con mejor diferenciación visual
        const nodes = subgrafo.nodes.map(n => {
            let color;
            let shape = "box";
            let fontConfig = { 
                size: 12,
                color: "#374151",
                align: "center" // ⬅️ Por defecto centro
            };
            
            if (n.group === "pregunta") {
                color = { background: "#fef3c7", border: "#f59e0b", highlight: { background: "#fed7aa", border: "#ea580c" } };
                shape = "diamond";
                fontConfig = { 
                    size: 14,
                    color: "#92400e",
                    align: "top",        // ⬅️ CAMBIO: texto en la parte superior
                    vadjust: -80       // ⬅️ NUEVO: ajuste vertical hacia arriba
                };
            } else if (n.group === "temporal") {
                color = { background: "#dbeafe", border: "#2563eb", highlight: { background: "#bfdbfe", border: "#1d4ed8" } };
                fontConfig = { 
                    size: 12,
                    color: "#1e40af",
                    align: "center" 
                };
            } else {
                color = { background: "#f3f4f6", border: "#6b7280", highlight: { background: "#e5e7eb", border: "#4b5563" } };
            }

            return {
                id: n.id,
                label: n.label || n.id,
                title: n.title || n.label || n.id,
                color: color,
                shape: shape,
                font: fontConfig,
                margin: { top: 10, right: 10, bottom: 10, left: 10 } // ⬅️ Más margen para el rombo
            };
        });

        // Aristas con mejor visualización de pesos
        const edges = subgrafo.edges.map(e => {
            const pesoEfectivo = e.peso_efectivo || 0;
            const width = Math.max(2, pesoEfectivo * 8); // Más grosor para mejor visibilidad
            
            return {
                from: e.from,
                to: e.to,
                arrows: { to: { enabled: true, scaleFactor: 1 } },
                label: e.label || "",
                title: `Peso Estructural: ${e.peso_estructural}\nRelevancia Temporal: ${e.relevancia_temporal}\nPeso Efectivo: ${e.peso_efectivo}`,
                font: { size: 10, align: "top" },
                color: { color: "#059669", highlight: "#047857" },
                width: width,
                smooth: { type: "cubicBezier", roundness: 0.4 }
            };
        });

        console.log(`Renderizando ${nodes.length} nodos y ${edges.length} aristas`); // Debug

        const options = {
            layout: {
                hierarchical: {
                    enabled: true,
                    direction: "UD", // (Down-Up = pregunta arriba)
                    sortMethod: "directed",
                    nodeSpacing: 150,
                    levelSeparation: 100
                }
            },
            physics: {
                enabled: false // Deshabilitado para layout jerárquico
            },
            edges: {
                smooth: { type: "cubicBezier", roundness: 0.4 },
                width: 2
            },
            nodes: { 
                borderWidth: 2,
                shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 5 }
            },
            interaction: {
                hover: true,
                zoomView: true,
                dragView: true,
                dragNodes: true,
                tooltipDelay: 100
            },
            physics: {
                enabled: true,
                solver: "forceAtlas2Based",
                stabilization: { iterations: 150 },
                barnesHut: { gravitationalConstant: -2000, springLength: 150, springConstant: 0.04 }
            }
        };

        // Crear la visualización
        const network = new vis.Network(
            container, 
            { 
                nodes: new vis.DataSet(nodes), 
                edges: new vis.DataSet(edges) 
            }, 
            options
        );

        // Evento para mostrar información al hacer click
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const node = subgrafo.nodes.find(n => n.id === nodeId);
                if (node) {
                    console.log("Click en nodo:", node);
                }
            }
        });

        console.log("✅ Árbol de consulta renderizado correctamente");
        
    } catch (error) {
        console.error("Error renderizando árbol:", error);
        container.innerHTML = `
            <div class="flex items-center justify-center h-full text-red-500 flex-col">
                <p class="text-lg mb-2">❌ Error al renderizar</p>
                <p class="text-sm">${error.message}</p>
            </div>
        `;
    }
}

async function agregarRespuestaComoContexto() {
    if (!ultimaRespuesta || !ultimaPregunta) {
        alert("❌ No hay una respuesta válida para agregar como contexto.");
        return;
    }

    const tituloSugerido = `Respuesta: ${ultimaPregunta.substring(0, 50)}${ultimaPregunta.length > 50 ? '...' : ''}`;
    const titulo = prompt(`💡 Ingresá un título para este nuevo contexto:\n\n(Sugerencia basada en tu pregunta)`, tituloSugerido);
    
    if (!titulo || !titulo.trim()) {
        alert("❌ Se necesita un título para crear el contexto.");
        return;
    }

    const esTemporal = confirm("🕒 ¿Querés que este contexto sea TEMPORAL (con fecha/hora actual)?\n\n✅ SÍ = Temporal (relevante por proximidad de tiempo)\n❌ NO = Atemporal (relevante solo por contenido)");

    try {
        const respuestaLimpia = ultimaRespuesta.split('\n\n📚 Contextos utilizados:')[0];
        
        const res = await axios.post('/contexto/', { 
            titulo: titulo.trim(), 
            texto: respuestaLimpia,
            es_temporal: esTemporal
        });
        
        const tipoContexto = esTemporal ? "TEMPORAL 🕒" : "ATEMPORAL 📋";
        alert(`✅ ¡Respuesta agregada como contexto ${tipoContexto}!\n\nTítulo: "${titulo.trim()}"\nID: ${res.data.id}\n\nYa puede ser usada en futuras consultas.`);
        
        document.getElementById('botonAgregarRespuesta').style.display = 'none';
        mostrarContextos();
        
    } catch (error) {
        alert(`❌ Error al agregar respuesta como contexto: ${error.message}`);
    }
}

async function mostrarContextos() {
    try {
        const res = await axios.get('/contexto/');
        const contextos = res.data;

        let salida = "";
        const numContextos = Object.keys(contextos).length;
        
        if (numContextos === 0) {
            salida = "No hay contextos almacenados aún.";
        } else {
            const temporales = Object.values(contextos).filter(ctx => ctx.es_temporal).length;
            const atemporales = numContextos - temporales;
            
            salida = `📊 Total: ${numContextos} contextos (🕒 ${temporales} temporales, 📋 ${atemporales} atemporales)\n\n`;
            
            for (const [id, datos] of Object.entries(contextos)) {
                const icono = datos.es_temporal ? "🕒" : "📋";
                
                salida += `${icono} ${datos.titulo}\n`;
                salida += `📄 ${datos.texto.substring(0, 150)}${datos.texto.length > 150 ? '...' : ''}\n`;
                
                // NUEVA: Información temporal detallada
                if (datos.es_temporal) {
                    if (datos.referencia_original) {
                        salida += `📅 Referencia: "${datos.referencia_original}" (${datos.tipo_referencia || 'N/A'})\n`;
                    }
                    if (datos.timestamp) {
                        const fecha = new Date(datos.timestamp);
                        const ahora = new Date();
                        const esFuturo = fecha > ahora;
                        const diasDiff = Math.ceil(Math.abs(fecha - ahora) / (1000 * 60 * 60 * 24));
                        
                        salida += `⏰ ${fecha.toLocaleString()} (${esFuturo ? '🔮' : '⏪'} ${diasDiff === 0 ? 'hoy' : diasDiff + ' días'})\n`;
                    }
                }
                
                salida += `🔗 Relacionados: ${datos.relaciones.map(rid => contextos[rid]?.titulo || rid).join(', ') || 'Ninguno'}\n`;
                salida += `🔑 Palabras clave: ${datos.palabras_clave.join(', ') || 'Ninguna'}\n\n`;
            }
        }

        document.getElementById("todosContextos").innerText = salida;
    } catch (error) {
        document.getElementById("todosContextos").innerText = `Error cargando contextos: ${error.message}`;
    }
}

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
                <p class="text-sm text-gray-700 mt-1">${info.texto.substring(0, 150)}${info.texto.length > 150 ? '...' : ''}</p>
                ${timestamp}
                <p class="text-xs text-gray-500 mt-1">🆔 ${id}</p>
            `;
            container.appendChild(div);
        }
    } catch (error) {
        document.getElementById('resultadosBusqueda').innerHTML = `<p class="text-red-600">Error en la búsqueda: ${error.message}</p>`;
    }
}

function abrirModalGrafo() {
    document.getElementById('modalGrafo').classList.remove('hidden');
    mostrandoLabels = document.getElementById('mostrarLabelsAristas').checked;
    setTimeout(() => cargarGrafo(), 100);
}

function cerrarModalGrafo() {
    document.getElementById('modalGrafo').classList.add('hidden');
    document.getElementById('panelInfo').classList.add('hidden');
}

function cerrarModalArbol() {
    document.getElementById('modalArbol').classList.add('hidden');
}


function toggleLabelsAristas() {
    mostrandoLabels = !mostrandoLabels;
    document.getElementById('mostrarLabelsAristas').checked = mostrandoLabels;
    if (networkInstance) {
        cargarGrafo();
    }
}

// NUEVA: Función para mostrar información detallada
function mostrarInfoDetallada(info) {
    const panel = document.getElementById('panelInfo');
    const content = document.getElementById('infoContent');
    
    content.innerHTML = `
        <div class="grid grid-cols-2 gap-4">
            <div>
                <p class="font-semibold text-gray-800">${info.titulo || 'Información'}</p>
                ${info.tipo ? `<p class="text-sm">Tipo: ${info.tipo}</p>` : ''}
                ${info.peso_estructural ? `<p class="text-sm">Peso Estructural: ${info.peso_estructural}</p>` : ''}
                ${info.relevancia_temporal !== undefined ? `<p class="text-sm">Relevancia Temporal: ${info.relevancia_temporal}</p>` : ''}
                ${info.peso_efectivo ? `<p class="text-sm">Peso Efectivo: ${info.peso_efectivo}</p>` : ''}
            </div>
            <div>
                ${info.timestamp ? `<p class="text-sm">Timestamp: ${new Date(info.timestamp).toLocaleString()}</p>` : ''}
                ${info.es_temporal !== undefined ? `<p class="text-sm">Es temporal: ${info.es_temporal ? 'Sí' : 'No'}</p>` : ''}
                ${info.conexiones ? `<p class="text-sm">Conexiones: ${info.conexiones}</p>` : ''}
            </div>
        </div>
    `;
    
    panel.classList.remove('hidden');
}

async function cargarGrafo() {
    try {
        const res = await axios.get('/grafo/visualizacion/');
        const datos = res.data;

        if (!datos.nodes || datos.nodes.length === 0) {
            const container = document.getElementById('grafo');
            container.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><p>No hay contextos para visualizar. Agregá algunos contextos primero.</p></div>';
            return;
        }

        const container = document.getElementById('grafo');
        
        // Procesar nodos con colores mejorados basados en temporalidad
        const nodes = datos.nodes.map(node => {
            const esTemporal = node.es_temporal;
            return {
                ...node,
                color: {
                    background: esTemporal ? '#bbdefb' : '#f5f5f5',
                    border: esTemporal ? '#1976d2' : '#757575',
                    highlight: { 
                        background: esTemporal ? '#90caf9' : '#e0e0e0', 
                        border: esTemporal ? '#0d47a1' : '#424242' 
                    }
                },
                font: { 
                    color: esTemporal ? '#1565c0' : '#424242', 
                    size: 12, 
                    face: 'Arial',
                    strokeWidth: 1,
                    strokeColor: '#ffffff'
                },
                borderWidth: 3,
                shadow: {
                    enabled: true,
                    color: esTemporal ? '#1976d2' : '#757575',
                    size: 10,
                    x: 2,
                    y: 2
                }
            };
        });

        // Procesar edges con labels y colores mejorados
        const edges = datos.edges.map(edge => {
            const esTemporal = edge.tipo === 'semantica_temporal';
            const pesoEstructural = edge.peso_estructural || 0;
            const relevanciaTemp = edge.relevancia_temporal || 0;
            const pesoEfectivo = edge.peso_efectivo || pesoEstructural;
            
            // Determinar color basado en el peso efectivo
            let color = '#90a4ae'; // Por defecto gris
            if (esTemporal) {
                // Verde intensidad basada en peso efectivo
                const intensidad = Math.floor(pesoEfectivo * 255);
                color = `rgb(76, ${Math.max(175, intensidad)}, 80)`;
            }
            
            // Label compacto que se muestra en la arista
            let label = '';
            if (mostrandoLabels) {
                label = `E:${pesoEstructural.toFixed(2)}|T:${relevanciaTemp.toFixed(2)}|Ef:${pesoEfectivo.toFixed(2)}`;
            }
            
            return {
                ...edge,
                label: label,
                color: {
                    color: color,
                    highlight: '#37474f',
                    opacity: 0.8
                },
                width: Math.max(1, pesoEfectivo * 6), // Grosor basado en peso efectivo
                smooth: { 
                    enabled: true, 
                    type: 'continuous',
                    roundness: 0.5
                },
                font: {
                    size: 10,
                    color: '#333333',
                    background: 'rgba(255,255,255,0.8)',
                    strokeWidth: 1,
                    strokeColor: '#ffffff'
                },
                title: `🔗 Relación ${esTemporal ? 'Temporal' : 'Semántica'}\n\n📊 Peso Estructural: ${pesoEstructural.toFixed(3)}\n⏰ Relevancia Temporal: ${relevanciaTemp.toFixed(3)}\n⚡ Peso Efectivo: ${pesoEfectivo.toFixed(3)}\n\n${esTemporal ? '🕒 Esta relación considera proximidad temporal' : '📋 Esta relación es puramente semántica'}`
            };
        });

        // Configuración mejorada del network - SIN ACTUALIZACIONES AUTOMÁTICAS
        const options = {
            nodes: { 
                shape: 'box',
                scaling: {
                    min: 16,
                    max: 32,
                    label: {
                        enabled: true,
                        min: 12,
                        max: 16,
                    }
                },
                margin: {
                    top: 5,
                    right: 5,
                    bottom: 5,
                    left: 5
                }
            },
            edges: {
                arrows: { 
                    to: { enabled: true, scaleFactor: 0.5 }
                },
                smooth: { type: 'continuous' }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09
                },
                stabilization: {
                    iterations: 200,
                    fit: true
                },
                // CLAVE: Una vez estabilizado, deshabilitar la física
                adaptiveTimestep: false
            },
            interaction: {
                hover: true,
                navigationButtons: true,
                keyboard: true,
                zoomView: true,
                dragView: true,
                // CLAVE: Permitir arrastrar nodos pero sin reactivar física
                dragNodes: true,
                selectConnectedEdges: false
            },
            layout: {
                improvedLayout: true,
                hierarchical: false
            },
            height: '100%',
            width: '100%',
            autoResize: true
        };

        networkInstance = new vis.Network(container, {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        }, options);

        // CLAVE: Deshabilitar física después de la estabilización inicial
        networkInstance.once("stabilized", function() {
            networkInstance.setOptions({ physics: false });
            console.log("🔒 Física deshabilitada - los nodos ya no se moverán automáticamente");
        });

        // Eventos mejorados - SIN ACTUALIZACIONES DEL GRAFO
        networkInstance.on("click", async function(params) {
            if (params.nodes.length > 0) {
                // Click en nodo
                const nodeId = params.nodes[0];
                try {
                    const contextoRes = await axios.get('/contexto/');
                    const contexto = contextoRes.data[nodeId];
                    if (contexto) {
                        mostrarInfoDetallada({
                            titulo: `🎯 ${contexto.titulo}`,
                            tipo: contexto.es_temporal ? 'Temporal 🕒' : 'Atemporal 📋',
                            timestamp: contexto.timestamp,
                            es_temporal: contexto.es_temporal,
                            conexiones: contexto.relaciones.length
                        });
                    }
                } catch (error) {
                    console.error('Error cargando contexto:', error);
                }
            } else if (params.edges.length > 0) {
                // Click en arista
                const edgeId = params.edges[0];
                const edgeData = datos.edges.find(e => 
                    (e.from + '-' + e.to) === edgeId || (e.to + '-' + e.from) === edgeId
                );
                
                if (edgeData) {
                    mostrarInfoDetallada({
                        titulo: `🔗 Relación ${edgeData.tipo === 'semantica_temporal' ? 'Temporal' : 'Semántica'}`,
                        tipo: edgeData.tipo,
                        peso_estructural: edgeData.peso_estructural.toFixed(3),
                        relevancia_temporal: edgeData.relevancia_temporal.toFixed(3),
                        peso_efectivo: edgeData.peso_efectivo.toFixed(3)
                    });
                }
            }
        });

        // Eventos de hover simplificados - SIN MODIFICAR EL GRAFO
        networkInstance.on("hoverNode", function(params) {
            // Solo cambiar el cursor, no modificar el grafo
            container.style.cursor = 'pointer';
        });

        networkInstance.on("blurNode", function(params) {
            container.style.cursor = 'default';
        });

        // REMOVIDO: Los eventos que causaban actualizaciones del grafo

        console.log(`✅ Grafo cargado (estático): ${nodes.length} nodos, ${edges.length} aristas`);
        
    } catch (error) {
        console.error('Error cargando grafo:', error);
        document.getElementById('grafo').innerHTML = `<div class="text-red-600 p-4">Error cargando grafo: ${error.message}</div>`;
    }
}

async function cargarEstadisticas() {
    try {
        const res = await axios.get('/estadisticas/');
        const stats = res.data;
        
        const container = document.getElementById('estadisticas');
        container.innerHTML = `
            <div class="space-y-2">
                <div class="flex justify-between">
                    <span class="font-medium">🗃️ Sistema:</span>
                    <span class="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                        Temporal v2.1
                    </span>
                </div>
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
                <div class="flex justify-between">
                    <span>⚡ Temporales:</span>
                    <span class="font-bold text-green-600">${stats.aristas_temporales || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span>📋 Semánticas:</span>
                    <span class="font-bold text-gray-600">${stats.aristas_semanticas || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span>🎯 Densidad:</span>
                    <span class="font-semibold">${(stats.densidad || 0).toFixed(3)}</span>
                </div>
                <div class="flex justify-between">
                    <span>💾 Tamaño:</span>
                    <span class="text-xs">${((stats.tamaño_grafo_mb || 0) + (stats.tamaño_metadatos_mb || 0)).toFixed(2)} MB</span>
                </div>
            </div>
            ${stats.nodo_mas_conectado ? `
            <div class="mt-3 p-2 bg-orange-50 border border-orange-200 rounded">
                <div class="font-medium text-orange-800 text-xs">🏆 Más Conectado:</div>
                <div class="text-xs">"${stats.nodo_mas_conectado.titulo}"</div>
                <div class="text-xs text-gray-600">${stats.nodo_mas_conectado.conexiones} conexiones</div>
            </div>
            ` : ''}
        `;
    } catch (error) {
        document.getElementById('estadisticas').innerHTML = `<p class="text-red-600 text-xs">Error cargando estadísticas: ${error.message}</p>`;
    }
}

async function mostrarContextosCentrales() {
    try {
        const res = await axios.get('/grafo/centrales/');
        const centrales = res.data;
        
        const container = document.getElementById('contextosCentrales');
        if (centrales.length === 0) {
            container.innerHTML = '<p class="text-gray-500 italic text-xs">No hay suficientes contextos</p>';
            return;
        }
        
        let html = '<div class="space-y-1 mt-2">';
        centrales.forEach((ctx, index) => {
            const icono = ctx.es_temporal ? "🕒" : "📋";
            html += `
                <div class="flex items-start text-xs mb-2">
                    <span class="font-bold text-blue-600 mr-1 min-w-4">${index + 1}.</span>
                    <div class="flex-1 break-words">
                        <div class="font-semibold whitespace-normal">${icono} ${ctx.titulo}</div>
                        <div class="text-gray-500">Centralidad: ${ctx.centralidad}</div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
        
    } catch (error) {
        document.getElementById('contextosCentrales').innerHTML = `<p class="text-red-600 text-xs">Error: ${error.message}</p>`;
    }
}

// Cerrar modal con Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        cerrarModalGrafo();
    }
});

window.addEventListener('resize', function() {
    if (networkInstance) {
        networkInstance.fit();
    }
});

// Mostrar/ocultar campo de referencia temporal
function toggleReferenciaTemporalInput() {
    const checkbox = document.getElementById('esTemporal');
    const container = document.getElementById('referenciaTemporalContainer');
    
    if (checkbox.checked) {
        container.classList.remove('hidden');
        document.getElementById('referenciaTemporalInput').focus();
    } else {
        container.classList.add('hidden');
        document.getElementById('referenciaTemporalInput').value = '';
        document.getElementById('resultadoParser').innerHTML = '';
    }
}

// Probar el parser temporal
async function probarParser() {
    const referencia = document.getElementById('referenciaTemporalInput').value.trim();
    const resultadoDiv = document.getElementById('resultadoParser');
    
    if (!referencia) {
        resultadoDiv.innerHTML = '<div class="text-yellow-600">⚠️ Escribe una referencia temporal para probar</div>';
        return;
    }
    
    try {
        const res = await axios.get(`/temporal/test/?referencia=${encodeURIComponent(referencia)}`);
        const data = res.data;
        
        if (data.parseado_exitoso) {
            const esFuturo = data.es_futuro ? "🔮 Futuro" : "⏪ Pasado";
            const diasDiff = Math.abs(data.dias_diferencia);
            const tiempoRelativo = diasDiff === 0 ? "hoy" : `${diasDiff} días`;
            
            resultadoDiv.innerHTML = `
                <div class="bg-green-50 border border-green-200 p-2 rounded">
                    <div class="text-green-800 font-medium">✅ Parseado correctamente</div>
                    <div class="text-green-700 text-xs">
                        📅 <strong>${data.fecha_legible}</strong><br>
                        🕰️ ${esFuturo} (${tiempoRelativo})<br>
                        🏷️ Tipo: ${data.tipo_referencia}
                    </div>
                </div>
            `;
        } else {
            resultadoDiv.innerHTML = `
                <div class="bg-red-50 border border-red-200 p-2 rounded">
                    <div class="text-red-800 font-medium">❌ No se pudo parsear</div>
                    <div class="text-red-700 text-xs">
                        Tipo: ${data.tipo_referencia}<br>
                        💡 Intenta con: "mañana", "25/01/2025", "en 3 días"
                    </div>
                </div>
            `;
        }
        
    } catch (error) {
        resultadoDiv.innerHTML = `<div class="text-red-600 text-xs">❌ Error: ${error.message}</div>`;
    }
}

// Previsualización en tiempo real
async function previewDeteccion() {
    const titulo = document.getElementById('titulo').value.trim();
    const texto = document.getElementById('texto').value.trim();
    const panelPreview = document.getElementById('panelPreview');
    const contenidoPreview = document.getElementById('contenidoPreview');
    
    // Debounce para evitar demasiadas llamadas
    clearTimeout(timeoutPreview);
    
    if (!titulo && !texto) {
        panelPreview.classList.add('hidden');
        return;
    }
    
    timeoutPreview = setTimeout(async () => {
        try {
            const res = await axios.post('/contexto/previsualizar/', {
                titulo: titulo,
                texto: texto,
                es_temporal: null  // Auto-detección
            });
            
            const data = res.data;
            panelPreview.classList.remove('hidden');
            
            if (data.sera_temporal) {
                let html = `
                    <div class="flex items-center mb-2">
                        <div class="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                        <span class="font-medium text-blue-800">🕒 Será TEMPORAL</span>
                        <span class="text-gray-500 ml-2">(${data.total_referencias} referencias encontradas)</span>
                    </div>
                `;
                
                // Mostrar referencias detectadas
                data.referencias.forEach((ref, index) => {
                    const esFuturo = ref.es_futuro ? "🔮" : "⏪";
                    const diasDiff = Math.abs(ref.dias_diferencia);
                    const tiempoRelativo = diasDiff === 0 ? "hoy" : `${diasDiff} días`;
                    
                    html += `
                        <div class="bg-blue-50 border border-blue-200 rounded p-2 mb-1">
                            <div class="font-medium text-blue-900">"${ref.texto}"</div>
                            <div class="text-blue-700">
                                📅 ${ref.fecha_legible} ${esFuturo} (${tiempoRelativo})
                            </div>
                            <div class="text-blue-600 text-xs">Tipo: ${ref.tipo}</div>
                        </div>
                    `;
                });
                
                contenidoPreview.innerHTML = html;
            } else {
                contenidoPreview.innerHTML = `
                    <div class="flex items-center">
                        <div class="w-3 h-3 bg-gray-500 rounded-full mr-2"></div>
                        <span class="font-medium text-gray-700">📋 Será ATEMPORAL</span>
                        <span class="text-gray-500 ml-2">(sin referencias temporales detectadas)</span>
                    </div>
                `;
            }
            
        } catch (error) {
            contenidoPreview.innerHTML = `
                <div class="text-red-600">❌ Error en previsualización: ${error.message}</div>
            `;
        }
    }, 500); // Debounce de 500ms
}

// Probar referencia manual
async function probarReferenciaManual() {
    const referencia = document.getElementById('referenciaManualInput').value.trim();
    const resultadoDiv = document.getElementById('resultadoReferenciaManual');
    
    if (!referencia) {
        resultadoDiv.innerHTML = '<div class="text-yellow-600">⚠️ Escribe una referencia temporal</div>';
        return;
    }
    
    try {
        const res = await axios.get(`/temporal/test/?referencia=${encodeURIComponent(referencia)}`);
        const data = res.data;
        
        if (data.parseado_exitoso) {
            const esFuturo = data.es_futuro ? "🔮 Futuro" : "⏪ Pasado";
            const diasDiff = Math.abs(data.dias_diferencia);
            const tiempoRelativo = diasDiff === 0 ? "hoy" : `${diasDiff} días`;
            
            resultadoDiv.innerHTML = `
                <div class="bg-green-50 border border-green-200 p-2 rounded">
                    <div class="text-green-800 font-medium">✅ ${data.fecha_legible}</div>
                    <div class="text-green-700 text-xs">${esFuturo} (${tiempoRelativo}) - ${data.tipo_referencia}</div>
                </div>
            `;
        } else {
            resultadoDiv.innerHTML = `
                <div class="bg-red-50 border border-red-200 p-2 rounded">
                    <div class="text-red-800">❌ No se pudo parsear</div>
                </div>
            `;
        }
    } catch (error) {
        resultadoDiv.innerHTML = `<div class="text-red-600">❌ Error: ${error.message}</div>`;
    }
}

// NUEVA función para agregar contexto con detección automática
async function agregarContextoMejorado() {
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
        
        // Construir mensaje informativo
        let mensaje = `✅ Contexto agregado!\n`;
        mensaje += `📋 ID: ${data.id}\n`;
        
        if (data.es_temporal) {
            mensaje += `🕒 Tipo: TEMPORAL`;
            if (data.fue_autodetectado) {
                mensaje += ` (detectado automáticamente)`;
            } else {
                mensaje += ` (especificado manualmente)`;
            }
            
            // Información temporal detallada
            if (data.info_temporal) {
                const info = data.info_temporal;
                mensaje += `\n\n📅 Información Temporal:`;
                mensaje += `\n• Fecha: ${info.fecha_legible || 'N/A'}`;
                if (info.referencia_original) {
                    mensaje += `\n• Referencia: "${info.referencia_original}"`;
                }
                mensaje += `\n• Tipo: ${info.tipo_referencia || 'N/A'}`;
                if (info.es_futuro !== undefined) {
                    mensaje += `\n• Tiempo: ${info.es_futuro ? '🔮 Futuro' : '⏪ Pasado'}`;
                }
            }
        } else {
            mensaje += `📋 Tipo: ATEMPORAL`;
        }
        
        alert(mensaje);
        
        // Limpiar formulario
        limpiarFormulario();
        
        // Actualizar vista
        mostrarContextos();
        
    } catch (error) {
        alert(`❌ Error al agregar contexto: ${error.message}`);
    }
}

// Función helper para limpiar formulario
function limpiarFormulario() {
    document.getElementById('titulo').value = '';
    document.getElementById('texto').value = '';
    document.getElementById('referenciaManualInput').value = '';
    document.getElementById('resultadoReferenciaManual').innerHTML = '';
    document.getElementById('panelPreview').classList.add('hidden');
    document.getElementById('referenciaManualContainer').classList.add('hidden');
    document.querySelector('#modoAuto').checked = true; // Reset a auto
    document.getElementById('formAgregarContexto').classList.add('hidden');
}

// Previsualización de intención temporal en tiempo real
async function previewIntencionTemporal() {
    const pregunta = document.getElementById('pregunta').value.trim();
    const panelIntencion = document.getElementById('panelIntencionTemporal');
    const contenidoIntencion = document.getElementById('contenidoIntencionTemporal');
    
    // Debounce para evitar demasiadas llamadas
    clearTimeout(timeoutIntencion);
    
    if (!pregunta || pregunta.length < 5) {
        panelIntencion.classList.add('hidden');
        return;
    }
    
    timeoutIntencion = setTimeout(async () => {
        try {
            const res = await axios.get(`/query/analizar/?pregunta=${encodeURIComponent(pregunta)}`);
            const data = res.data;
            
            panelIntencion.classList.remove('hidden');
            
            // Emoji y colores según intención
            const infoIntencion = {
                'fuerte': { emoji: '🔴', color: 'text-red-700', bg: 'bg-red-50', nombre: 'TEMPORAL FUERTE' },
                'media': { emoji: '🟡', color: 'text-yellow-700', bg: 'bg-yellow-50', nombre: 'TEMPORAL MEDIA' },
                'debil': { emoji: '🟢', color: 'text-green-700', bg: 'bg-green-50', nombre: 'TEMPORAL DÉBIL' },
                'nula': { emoji: '⚫', color: 'text-gray-700', bg: 'bg-gray-50', nombre: 'ESTRUCTURAL' }
            };
            
            const info = infoIntencion[data.intencion_temporal] || infoIntencion['debil'];
            
            let html = `
                <div class="flex items-center mb-2">
                    <div class="w-3 h-3 rounded-full mr-2" style="background-color: ${info.emoji === '🔴' ? '#ef4444' : info.emoji === '🟡' ? '#eab308' : info.emoji === '🟢' ? '#22c55e' : '#6b7280'}"></div>
                    <span class="font-medium ${info.color}">${info.emoji} Intención: ${info.nombre}</span>
                    <span class="text-gray-500 ml-2">(confianza: ${(data.confianza * 100).toFixed(0)}%)</span>
                </div>
                
                <div class="text-gray-600 mb-2">
                    <strong>Factor de refuerzo temporal:</strong> ${data.factor_refuerzo_temporal}x
                </div>
                
                <div class="text-gray-600 mb-2">
                    <strong>Explicación:</strong> ${data.explicacion}
                </div>
            `;
            
            // Mostrar referencia temporal si existe
            if (data.referencia_temporal_detectada) {
                html += `
                    <div class="text-blue-600 mb-2">
                        <strong>Referencia detectada:</strong> "${data.referencia_temporal_detectada}"
                    </div>
                `;
            }
            
            // Mostrar timestamp de referencia si existe
            if (data.timestamp_referencia) {
                const fecha = new Date(data.timestamp_referencia);
                html += `
                    <div class="text-purple-600 text-xs">
                        <strong>Timestamp referencia:</strong> ${fecha.toLocaleString()}
                    </div>
                `;
            }
            
            // Estrategia que se aplicará
            let estrategiaTexto = "";
            if (data.factor_refuerzo_temporal > 1.5) {
                estrategiaTexto = "🕒 Se priorizarán contextos temporalmente relevantes";
            } else if (data.factor_refuerzo_temporal < 0.5) {
                estrategiaTexto = "📋 Se priorizará contenido semántico sobre temporal";
            } else {
                estrategiaTexto = "⚖️ Balance entre relevancia semántica y temporal";
            }
            
            html += `
                <div class="mt-2 p-2 ${info.bg} border border-gray-200 rounded text-xs">
                    <strong>Estrategia:</strong> ${estrategiaTexto}
                </div>
            `;
            
            contenidoIntencion.innerHTML = html;
            
        } catch (error) {
            contenidoIntencion.innerHTML = `
                <div class="text-red-600">❌ Error analizando intención: ${error.message}</div>
            `;
        }
    }, 800); // Debounce de 800ms para análisis de intención
}

// NUEVA: Función para probar solo el análisis de intención
async function probarAnalisisIntencion() {
    const pregunta = document.getElementById('pregunta').value.trim();
    
    if (!pregunta) {
        alert("Escribe una pregunta primero");
        return;
    }
    
    try {
        const res = await axios.get(`/query/analisis-completo/?pregunta=${encodeURIComponent(pregunta)}`);
        console.log("📊 Análisis completo de consulta:", res.data);
        
        // Mostrar resultado en un alert detallado
        const analisis = res.data.analisis_intencion;
        const estrategia = res.data.estrategia_aplicada;
        
        let mensaje = `🧠 ANÁLISIS COMPLETO DE CONSULTA\n\n`;
        mensaje += `📝 Pregunta: "${pregunta}"\n\n`;
        mensaje += `🎯 Intención: ${analisis.intencion_temporal?.toUpperCase()}\n`;
        mensaje += `📊 Confianza: ${((analisis.confianza || 0) * 100).toFixed(0)}%\n`;
        mensaje += `⚡ Factor refuerzo: ${(estrategia.factor_refuerzo || 1.0)}x\n`;
        mensaje += `📅 Referencia temporal: ${estrategia.referencia_temporal ? new Date(estrategia.referencia_temporal).toLocaleString() : 'N/A'}\n\n`;
        mensaje += `💡 Explicación: ${estrategia.explicacion}\n\n`;
        mensaje += `🔍 Contextos encontrados: ${res.data.contextos_recuperados?.length || 0}`;
        
        alert(mensaje);
        
    } catch (error) {
        alert(`❌ Error en análisis: ${error.message}`);
    }
}

// NUEVO: Actualizar el árbol de consulta para mostrar información de intención temporal
function abrirModalArbol(subgrafo) {
    console.log("Abriendo modal de árbol con información temporal:", subgrafo);
    
    const modal = document.getElementById('modalArbol');
    modal.classList.remove('hidden');

    const container = document.getElementById('arbolConsulta');

    if (!subgrafo || !subgrafo.nodes || subgrafo.nodes.length === 0) {
        const errorMsg = subgrafo?.meta?.error || "Subgrafo vacío o inválido";
        container.innerHTML = `
            <div class="flex items-center justify-center h-full text-gray-500 flex-col">
                <p class="text-lg mb-2">❌ No se puede mostrar el árbol</p>
                <p class="text-sm">${errorMsg}</p>
            </div>
        `;
        return;
    }

    try {
        // Nodos con información de intención temporal
        const nodes = subgrafo.nodes.map(n => {
            let color;
            let shape = "box";
            let fontConfig = { 
                size: 12,
                color: "#374151",
                align: "center"
            };
            
            if (n.group === "pregunta_temporal") {
                // Pregunta con intención temporal fuerte
                color = { background: "#fef3c7", border: "#f59e0b", highlight: { background: "#fed7aa", border: "#ea580c" } };
                shape = "diamond";
                fontConfig = { 
                    size: 14,
                    color: "#92400e",
                    align: "top",
                    vadjust: -80
                };
            } else if (n.group === "pregunta_estructural") {
                // Pregunta con intención estructural
                color = { background: "#e5e7eb", border: "#6b7280", highlight: { background: "#f3f4f6", border: "#4b5563" } };
                shape = "diamond";
                fontConfig = { 
                    size: 14,
                    color: "#374151",
                    align: "top",
                    vadjust: -80
                };
            } else if (n.group === "pregunta") {
                // Pregunta mixta
                color = { background: "#dbeafe", border: "#3b82f6", highlight: { background: "#bfdbfe", border: "#2563eb" } };
                shape = "diamond";
                fontConfig = { 
                    size: 14,
                    color: "#1e40af",
                    align: "top",
                    vadjust: -80
                };
            } else if (n.group === "temporal") {
                color = { background: "#dbeafe", border: "#2563eb", highlight: { background: "#bfdbfe", border: "#1d4ed8" } };
                fontConfig = { 
                    size: 12,
                    color: "#1e40af",
                    align: "center" 
                };
            } else {
                color = { background: "#f3f4f6", border: "#6b7280", highlight: { background: "#e5e7eb", border: "#4b5563" } };
            }

            return {
                id: n.id,
                label: n.label || n.id,
                title: n.title || n.label || n.id,
                color: color,
                shape: shape,
                font: fontConfig,
                margin: { top: 10, right: 10, bottom: 10, left: 10 }
            };
        });

        // Aristas con información de factor de refuerzo
        const edges = subgrafo.edges.map(e => {
            const pesoEfectivo = e.peso_efectivo || 0;
            const factorRefuerzo = e.factor_refuerzo || 1.0;
            const width = Math.max(2, pesoEfectivo * 8);
            
            // Color según tipo de consulta
            let color = "#059669"; // Verde por defecto
            if (e.tipo === "consulta_temporal_fuerte") {
                color = "#dc2626"; // Rojo para temporal fuerte
            } else if (e.tipo === "consulta_estructural") {
                color = "#6b7280"; // Gris para estructural
            }
            
            return {
                from: e.from,
                to: e.to,
                arrows: { to: { enabled: true, scaleFactor: 1 } },
                label: e.label || "",
                title: `Peso Estructural: ${e.peso_estructural}\nRelevancia Temporal: ${e.relevancia_temporal}\nFactor Refuerzo: ${factorRefuerzo}x\nPeso Efectivo: ${e.peso_efectivo}\nTipo: ${e.tipo}`,
                font: { size: 10, align: "top" },
                color: { color: color, highlight: color },
                width: width,
                smooth: { type: "cubicBezier", roundness: 0.4 }
            };
        });

        console.log(`Renderizando árbol temporal: ${nodes.length} nodos, ${edges.length} aristas`);

        const options = {
            layout: {
                hierarchical: {
                    enabled: true,
                    direction: "UD",
                    sortMethod: "directed",
                    nodeSpacing: 150,
                    levelSeparation: 100
                }
            },
            physics: {
                enabled: true,
                solver: "forceAtlas2Based",
                stabilization: { iterations: 150 },
                barnesHut: { gravitationalConstant: -2000, springLength: 150, springConstant: 0.04 }
            },
            nodes: { 
                borderWidth: 2,
                shadow: { enabled: true, color: 'rgba(0,0,0,0.2)', size: 5 }
            },
            edges: {
                smooth: { type: "cubicBezier", roundness: 0.4 },
                width: 2
            },
            interaction: {
                hover: true,
                zoomView: true,
                dragView: true,
                dragNodes: true,
                tooltipDelay: 100
            }
        };

        // Crear la visualización
        const network = new vis.Network(
            container, 
            { 
                nodes: new vis.DataSet(nodes), 
                edges: new vis.DataSet(edges) 
            }, 
            options
        );

        console.log("✅ Árbol de consulta con análisis temporal renderizado correctamente");
        
    } catch (error) {
        console.error("Error renderizando árbol temporal:", error);
        container.innerHTML = `
            <div class="flex items-center justify-center h-full text-red-500 flex-col">
                <p class="text-lg mb-2">❌ Error al renderizar</p>
                <p class="text-sm">${error.message}</p>
            </div>
        `;
    }
}