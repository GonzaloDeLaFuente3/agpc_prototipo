// Variables globales
let ultimaRespuesta = "";
let ultimaPregunta = "";
let networkInstance = null;
let mostrandoLabels = true;
let ultimoSubgrafo = null;

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
});

async function agregarContexto() {
    const titulo = document.getElementById('titulo').value;
    const texto = document.getElementById('texto').value;
    const esTemporal = document.getElementById('esTemporal').checked;

    if (!titulo || !texto) {
        alert("Por favor completá título y texto.");
        return;
    }

    try {
        const res = await axios.post('/contexto/', { 
            titulo, 
            texto, 
            es_temporal: esTemporal 
        });
        
        const tipoContexto = esTemporal ? "TEMPORAL 🕒" : "ATEMPORAL 📋";
        alert(`✅ Contexto ${tipoContexto} agregado con relaciones detectadas!\nID: ${res.data.id}`);
        
        // Limpiar campos
        document.getElementById('titulo').value = '';
        document.getElementById('texto').value = '';
        document.getElementById('esTemporal').checked = false;
        document.getElementById('formAgregarContexto').classList.add('hidden');
        
        // Actualizar automáticamente
        mostrarContextos();
        
    } catch (error) {
        alert(`❌ Error al agregar contexto: ${error.message}`);
    }
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
    console.log("🔍 INICIO - función preguntar()");
    
    const pregunta = document.getElementById('pregunta').value;
    console.log("📝 Pregunta:", pregunta);

    if (!pregunta.trim()) {
        alert("Por favor escribí una pregunta.");
        return;
    }

    const respuestaDiv = document.getElementById('respuesta');
    const botonDiv = document.getElementById('botonAgregarRespuesta');
    const botonArbolDiv = document.getElementById('botonVerArbol');
    
    console.log("🎯 Elementos DOM encontrados:");
    console.log("  - respuestaDiv:", !!respuestaDiv);
    console.log("  - botonDiv:", !!botonDiv);
    console.log("  - botonArbolDiv:", !!botonArbolDiv);
    
    respuestaDiv.innerHTML = "🔍 Buscando contextos relevantes (semánticos + temporales) y generando respuesta...";
    botonDiv.style.display = 'none';
    botonArbolDiv.style.display = 'none';

    try {
        console.log("📡 Enviando request al servidor...");
        const res = await axios.get(`/preguntar/?pregunta=${encodeURIComponent(pregunta)}`);
        
        console.log("✅ Respuesta completa del servidor:");
        console.log(JSON.stringify(res.data, null, 2));
        
        respuestaDiv.innerText = res.data.respuesta;
        
        ultimaRespuesta = res.data.respuesta;
        ultimaPregunta = pregunta;
        
        // Mostrar botón agregar respuesta si la respuesta es válida
        if (res.data.respuesta && !res.data.respuesta.startsWith("[ERROR]")) {
            botonDiv.style.display = 'block';
            console.log("✅ Botón agregar respuesta mostrado");
        } else {
            console.log("❌ Botón agregar respuesta NO mostrado - respuesta inválida");
        }

        // DIAGNÓSTICO DETALLADO DEL SUBGRAFO
        console.log("\n🌳 === ANÁLISIS DEL SUBGRAFO ===");
        
        const subgrafo = res.data.subgrafo;
        console.log("1. subgrafo existe:", !!subgrafo);
        console.log("2. subgrafo completo:", subgrafo);
        
        if (subgrafo) {
            console.log("3. subgrafo.nodes existe:", !!subgrafo.nodes);
            console.log("4. subgrafo.nodes:", subgrafo.nodes);
            console.log("5. subgrafo.nodes.length:", subgrafo.nodes ? subgrafo.nodes.length : "N/A");
            console.log("6. subgrafo.edges existe:", !!subgrafo.edges);
            console.log("7. subgrafo.edges:", subgrafo.edges);
            console.log("8. subgrafo.edges.length:", subgrafo.edges ? subgrafo.edges.length : "N/A");
            console.log("9. subgrafo.meta:", subgrafo.meta);
        }
        
        // CONDICIÓN PARA MOSTRAR BOTÓN
        const condicion1 = subgrafo;
        const condicion2 = subgrafo && subgrafo.nodes;
        const condicion3 = subgrafo && subgrafo.nodes && subgrafo.nodes.length > 0;
        
        console.log("\n🔍 === EVALUACIÓN DE CONDICIONES ===");
        console.log("  subgrafo existe:", condicion1);
        console.log("  subgrafo.nodes existe:", condicion2);
        console.log("  subgrafo.nodes.length > 0:", condicion3);
        
        if (condicion3) {
            ultimoSubgrafo = subgrafo;
            botonArbolDiv.style.display = 'block';
            console.log("✅ ÉXITO: Botón de árbol MOSTRADO");
            console.log("  ultimoSubgrafo asignado:", !!ultimoSubgrafo);
        } else {
            ultimoSubgrafo = null;
            botonArbolDiv.style.display = 'none';
            console.log("❌ FALLO: Botón de árbol NO mostrado");
            console.log("  Razones:");
            if (!subgrafo) console.log("    - subgrafo no existe");
            if (subgrafo && !subgrafo.nodes) console.log("    - subgrafo.nodes no existe");
            if (subgrafo && subgrafo.nodes && subgrafo.nodes.length === 0) console.log("    - subgrafo.nodes está vacío");
        }
        
        // Debug adicional si hay información
        if (res.data.debug) {
            console.log("\n🔧 === INFO DE DEBUG DEL SERVIDOR ===");
            console.log(res.data.debug);
        }
        
        console.log("\n✅ FINAL - función preguntar() completada");
        
    } catch (error) {
        console.log("💥 ERROR en preguntar():");
        console.error(error);
        respuestaDiv.innerText = `Error: ${error.message}`;
        botonDiv.style.display = 'none';
        botonArbolDiv.style.display = 'none';
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
            
            if (n.group === "pregunta") {
                color = { background: "#fef3c7", border: "#f59e0b", highlight: { background: "#fed7aa", border: "#ea580c" } };
                shape = "diamond";
            } else if (n.group === "temporal") {
                color = { background: "#dbeafe", border: "#2563eb", highlight: { background: "#bfdbfe", border: "#1d4ed8" } };
            } else {
                color = { background: "#f3f4f6", border: "#6b7280", highlight: { background: "#e5e7eb", border: "#4b5563" } };
            }

            return {
                id: n.id,
                label: n.label || n.id,
                title: n.title || n.label || n.id,
                color: color,
                shape: shape,
                font: { 
                    size: n.group === "pregunta" ? 14 : 12,
                    color: n.group === "pregunta" ? "#92400e" : (n.group === "temporal" ? "#1e40af" : "#374151")
                },
                margin: { top: 5, right: 5, bottom: 5, left: 5 }
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
                font: { size: 10, align: "middle" },
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
                    direction: "UD", // top-bottom
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
                dragNodes: false // Evitar que se muevan los nodos del árbol
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
                const timestamp = datos.timestamp ? `\n⏰ ${new Date(datos.timestamp).toLocaleString()}` : "";
                
                salida += `${icono} ${datos.titulo}\n`;
                salida += `📄 ${datos.texto.substring(0, 150)}${datos.texto.length > 150 ? '...' : ''}${timestamp}\n`;
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