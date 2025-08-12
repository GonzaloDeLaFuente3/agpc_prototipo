// script.js - Funcionalidad del AGPC

// Variables globales
let ultimaRespuesta = "";
let ultimaPregunta = "";

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
    });

    // Enter en campos de input para ejecutar acciones
    document.getElementById('pregunta').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            preguntar();
        }
    });

    document.getElementById('textoBusqueda').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            buscarSemantico();
        }
    });

    // Cargar grafo inicial (se cargará cuando se abra el modal)
});

// Funciones principales
async function agregarContexto() {
    const titulo = document.getElementById('titulo').value;
    const texto = document.getElementById('texto').value;

    if (!titulo || !texto) {
        alert("Por favor completá título y texto.");
        return;
    }

    try {
        const res = await axios.post('/contexto/', { titulo, texto });
        alert(`✅ Contexto agregado automáticamente con relaciones detectadas! ID interno: ${res.data.id}`);
        
        // Limpiar campos
        document.getElementById('titulo').value = '';
        document.getElementById('texto').value = '';
        document.getElementById('formAgregarContexto').classList.add('hidden');
        
        // Actualizar automáticamente
        mostrarContextos();
        
    } catch (error) {
        alert(`❌ Error al agregar contexto: ${error.message}`);
    }
}

async function preguntar() {
    const pregunta = document.getElementById('pregunta').value;

    if (!pregunta.trim()) {
        alert("Por favor escribí una pregunta.");
        return;
    }

    // Mostrar indicador de carga
    const respuestaDiv = document.getElementById('respuesta');
    const botonDiv = document.getElementById('botonAgregarRespuesta');
    respuestaDiv.innerHTML = "🔍 Buscando contextos relevantes y generando respuesta...";
    botonDiv.style.display = 'none';

    try {
        const res = await axios.get(`/preguntar/?pregunta=${encodeURIComponent(pregunta)}`);
        respuestaDiv.innerText = res.data.respuesta;
        
        // Guardar para uso posterior
        ultimaRespuesta = res.data.respuesta;
        ultimaPregunta = pregunta;
        
        // Mostrar botón para agregar como contexto (solo si hay respuesta válida)
        if (res.data.respuesta && !res.data.respuesta.startsWith("[ERROR]")) {
            botonDiv.style.display = 'block';
        }
        
    } catch (error) {
        respuestaDiv.innerText = `Error: ${error.message}`;
        botonDiv.style.display = 'none';
    }
}

async function agregarRespuestaComoContexto() {
    if (!ultimaRespuesta || !ultimaPregunta) {
        alert("❌ No hay una respuesta válida para agregar como contexto.");
        return;
    }

    // Pedir título al usuario
    const tituloSugerido = `Respuesta: ${ultimaPregunta.substring(0, 50)}${ultimaPregunta.length > 50 ? '...' : ''}`;
    const titulo = prompt(`💡 Ingresá un título para este nuevo contexto:\n\n(Sugerencia basada en tu pregunta)`, tituloSugerido);
    
    if (!titulo || !titulo.trim()) {
        alert("❌ Se necesita un título para crear el contexto.");
        return;
    }

    try {
        // Limpiar la respuesta (quitar la parte de "contextos utilizados")
        const respuestaLimpia = ultimaRespuesta.split('\n\n📚 Contextos utilizados:')[0];
        
        const res = await axios.post('/contexto/', { 
            titulo: titulo.trim(), 
            texto: respuestaLimpia 
        });
        
        alert(`✅ ¡Respuesta agregada como nuevo contexto!\n\nTítulo: "${titulo.trim()}"\nID: ${res.data.id}\n\nYa puede ser usada en futuras consultas.`);
        
        // Ocultar el botón después de agregar
        document.getElementById('botonAgregarRespuesta').style.display = 'none';
        
        // Actualizar visualizaciones
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
            salida = `📊 Total: ${numContextos} contextos\n\n`;
            for (const [id, datos] of Object.entries(contextos)) {
                salida += `🟦 ${datos.titulo}\n`;
                salida += `📄 ${datos.texto.substring(0, 100)}${datos.texto.length > 100 ? '...' : ''}\n`;
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
            const div = document.createElement("div");
            div.className = "p-3 bg-gray-100 rounded border-l-4 border-pink-600 shadow";
            div.innerHTML = `
                <strong class="text-pink-800">📑 ${info.titulo}</strong><br>
                <p class="text-sm text-gray-700 mt-1">${info.texto.substring(0, 150)}${info.texto.length > 150 ? '...' : ''}</p>
                <p class="text-xs text-gray-500 mt-1">🆔 ${id}</p>
            `;
            container.appendChild(div);
        }
    } catch (error) {
        document.getElementById('resultadosBusqueda').innerHTML = `<p class="text-red-600">Error en la búsqueda: ${error.message}</p>`;
    }
}

// Funciones del Modal del Grafo
function abrirModalGrafo() {
    document.getElementById('modalGrafo').classList.remove('hidden');
    // Cargar el grafo cuando se abre el modal
    setTimeout(() => {
        cargarGrafo();
    }, 100);
}

function cerrarModalGrafo() {
    document.getElementById('modalGrafo').classList.add('hidden');
}

async function cargarGrafo() {
    try {
        // Usar el nuevo endpoint optimizado para visualización
        const res = await axios.get('/grafo/visualizacion/');
        const datos = res.data;

        // Verificar si hay nodos para mostrar
        if (!datos.nodes || datos.nodes.length === 0) {
            const container = document.getElementById('grafo');
            container.innerHTML = '<div class="flex items-center justify-center h-full text-gray-500"><p>No hay contextos para visualizar. Agregá algunos contextos primero.</p></div>';
            return;
        }

        const container = document.getElementById('grafo');
        
        // Configurar colores por grupo (cantidad de palabras clave)
        const colorPalette = ['#e3f2fd', '#f3e5f5', '#e8f5e8', '#fff3e0', '#fce4ec'];
        
        // Procesar nodos con colores dinámicos
        const nodes = datos.nodes.map(node => ({
            ...node,
            color: {
                background: colorPalette[node.group % colorPalette.length] || '#e3f2fd',
                border: '#1976d2',
                highlight: { background: '#bbdefb', border: '#0d47a1' }
            },
            font: { color: '#1565c0', size: 12, face: 'Arial' }
        }));

        // Procesar edges con información de peso
        const edges = datos.edges.map(edge => ({
            ...edge,
            color: {
                color: edge.weight > 0.3 ? '#4caf50' : '#90a4ae',
                highlight: '#37474f'
            },
            width: Math.max(1, edge.weight * 5), // Grosor basado en similitud
            smooth: { enabled: true, type: 'continuous' }
        }));

        const network = new vis.Network(container, {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        }, {
            nodes: { 
                shape: 'box',
                size: 20,
                borderWidth: 2,
                shadow: true,
                margin: 10
            },
            edges: { 
                arrows: { to: { enabled: true, scaleFactor: 0.5 } }
            },
            physics: { 
                stabilization: { iterations: 200 },
                barnesHut: { 
                    gravitationalConstant: -8000, 
                    springConstant: 0.001, 
                    springLength: 200 
                }
            },
            interaction: { hover: true },
            layout: { improvedLayout: true }
        });

        // Evento de click mejorado
        network.on("click", async function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                try {
                    const contextoRes = await axios.get('/contexto/');
                    const contexto = contextoRes.data[nodeId];
                    if (contexto) {
                        const relacionados = contexto.relaciones.map(rid => 
                            contextoRes.data[rid]?.titulo || rid
                        ).join(', ') || 'Ninguno';
                        
                        alert(`📋 ${contexto.titulo}\n\n📝 ${contexto.texto}\n\n🔗 Relacionados: ${relacionados}\n\n🏷️ Palabras clave: ${contexto.palabras_clave.join(', ')}\n\n🆔 ID: ${nodeId}`);
                    }
                } catch (error) {
                    alert(`Error cargando información del contexto: ${error.message}`);
                }
            }
        });
        
    } catch (error) {
        console.error('Error cargando grafo:', error);
        document.getElementById('grafo').innerHTML = `<div class="text-red-600 p-4">Error cargando grafo: ${error.message}</div>`;
    }
}

// Funciones de Estadísticas
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
                        ${stats.storage_type.split(' ')[0]}
                    </span>
                </div>
                <div class="flex justify-between">
                    <span>📊 Contextos:</span>
                    <span class="font-bold text-green-600">${stats.total_contextos}</span>
                </div>
                <div class="flex justify-between">
                    <span>🔗 Relaciones:</span>
                    <span class="font-bold text-blue-600">${stats.total_relaciones}</span>
                </div>
                <div class="flex justify-between">
                    <span>🎯 Densidad:</span>
                    <span class="font-semibold">${(stats.densidad || 0).toFixed(3)}</span>
                </div>
                <div class="flex justify-between">
                    <span>🌐 Componentes:</span>
                    <span class="font-semibold">${stats.componentes_conectados || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span>💾 Tamaño:</span>
                    <span class="text-xs">${((stats.tamaño_grafo_mb || 0) + (stats.tamaño_metadatos_mb || 0)).toFixed(2)} MB</span>
                </div>
            </div>
            ${stats.nodo_mas_conectado ? `
            <div class="mt-3 p-2 bg-orange-50 border border-orange-200 rounded">
                <div class="font-medium text-orange-800 text-xs">🏆 Más Conectado:</div>
                <div class="text-xs">"${stats.nodo_mas_conectado.titulo}."</div>
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
            html += `
                <div class="flex items-start text-xs mb-2">
                    <span class="font-bold text-blue-600 mr-1 min-w-4">${index + 1}.</span>
                    <div class="flex-1 break-words">
                        <div class="font-semibold whitespace-normal">${ctx.titulo}</div>
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