// script.js - Funcionalidad del AGPC

// Variables globales
let ultimaRespuesta = "";
let ultimaPregunta = "";
let contextoEditando = null;

// Event listeners para cuando la página carga
document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Página cargada, configurando event listeners...");
    
    // Toggle para mostrar/ocultar formulario de agregar contexto
    const toggleButton = document.getElementById('toggleAgregarContexto');
    if (toggleButton) {
        toggleButton.addEventListener('click', function() {
            const form = document.getElementById('formAgregarContexto');
            if (form) {
                form.classList.toggle('hidden');
                if (!form.classList.contains('hidden')) {
                    const tituloInput = document.getElementById('titulo');
                    if (tituloInput) {
                        tituloInput.focus();
                    }
                }
            }
        });
        console.log("✅ Toggle agregar contexto configurado");
    }

    // Cancelar agregar contexto
    const cancelarButton = document.getElementById('cancelarAgregar');
    if (cancelarButton) {
        cancelarButton.addEventListener('click', function() {
            const form = document.getElementById('formAgregarContexto');
            const tituloInput = document.getElementById('titulo');
            const textoInput = document.getElementById('texto');
            
            if (form) form.classList.add('hidden');
            if (tituloInput) tituloInput.value = '';
            if (textoInput) textoInput.value = '';
        });
        console.log("✅ Botón cancelar configurado");
    }

    // Enter en campos de input para ejecutar acciones
    const preguntaInput = document.getElementById('pregunta');
    if (preguntaInput) {
        preguntaInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                preguntar();
            }
        });
    }

    const busquedaInput = document.getElementById('textoBusqueda');
    if (busquedaInput) {
        busquedaInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                buscarSemantico();
            }
        });
    }
    
    console.log("✅ Todos los event listeners configurados correctamente");
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
        // Mostrar indicador de carga (opcional)
        const botonGuardar = document.querySelector('button[onclick="agregarContexto()"]');
        const textoOriginal = botonGuardar.innerHTML;
        botonGuardar.innerHTML = "⏳ Guardando...";
        botonGuardar.disabled = true;

        // Enviar petición
        const res = await axios.post('/contexto/', { titulo, texto });
        
        // Verificar respuesta
        if (res.data && res.data.id) {
            alert(`✅ Contexto agregado exitosamente!\n\nTítulo: "${titulo}"\nID: ${res.data.id}\n\nRelaciones automáticas calculadas.`);
            
            // Limpiar campos
            document.getElementById('titulo').value = '';
            document.getElementById('texto').value = '';
            
            // Ocultar formulario
            document.getElementById('formAgregarContexto').classList.add('hidden');
            
            // Actualizar lista de contextos automáticamente
            await mostrarContextos();
            
            console.log("✅ Contexto agregado y visualización actualizada");
        } else {
            throw new Error("Respuesta inválida del servidor");
        }
        
    } catch (error) {
        console.error("❌ Error agregando contexto:", error);
        alert(`❌ Error al agregar contexto: ${error.response?.data?.detail || error.message}`);
    } finally {
        // Restaurar botón
        const botonGuardar = document.querySelector('button[onclick="agregarContexto()"]');
        if (botonGuardar) {
            botonGuardar.innerHTML = "✅ Guardar";
            botonGuardar.disabled = false;
        }
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

        const container = document.getElementById("todosContextos");
        const numContextos = Object.keys(contextos).length;
        
        if (numContextos === 0) {
            container.innerHTML = "<p class='text-gray-500 italic'>No hay contextos almacenados aún.</p>";
            return;
        }

        // Header con estadísticas
        let html = `<div class='mb-3 p-2 bg-blue-50 border border-blue-200 rounded'>
                     <p class='text-sm font-semibold text-blue-800'>📊 Total: ${numContextos} contextos</p>
                    </div>`;

        // Lista de contextos con botones de acción
        for (const [id, datos] of Object.entries(contextos)) {
            const relacionados = datos.relaciones.map(rid => 
                contextos[rid]?.titulo || rid
            ).join(', ') || 'Ninguno';

            html += `
                <div class='mb-4 p-3 bg-white border border-gray-200 rounded-lg shadow-sm'>
                    <div class='flex justify-between items-start mb-2'>
                        <h4 class='font-semibold text-blue-800 text-sm break-words flex-1 mr-2'>${datos.titulo}</h4>
                        <button onclick="editarContexto('${id}')" 
                                class='bg-yellow-500 text-white px-3 py-1 rounded-lg text-xs hover:bg-yellow-600 transition-colors flex-shrink-0 font-medium'
                                title="Editar contexto">
                            ✏️ Editar
                        </button>
                    </div>
                    
                    <p class='text-xs text-gray-700 mb-2 break-words'>
                        📄 ${datos.texto.substring(0, 120)}${datos.texto.length > 120 ? '...' : ''}
                    </p>
                    
                    <div class='text-xs text-gray-500 space-y-1'>
                        <p><strong>🔗 Relacionados:</strong> ${relacionados}</p>
                        <p><strong>🔑 Palabras clave:</strong> ${datos.palabras_clave.join(', ') || 'Ninguna'}</p>
                        <p><strong>🆔 ID:</strong> <code class='bg-gray-100 px-1 rounded'>${id}</code></p>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
        
    } catch (error) {
        document.getElementById("todosContextos").innerHTML = 
            `<p class="text-red-600 text-sm">Error cargando contextos: ${error.message}</p>`;
    }
}

async function editarContexto(id) {
    try {
        // Obtener datos actuales del contexto
        const res = await axios.get('/contexto/');
        const contexto = res.data[id];
        
        if (!contexto) {
            alert("❌ Contexto no encontrado");
            return;
        }

        // Modal de edición usando prompts simples (luego podemos mejorarlo)
        const nuevoTitulo = prompt(`✏️ Editar título:\n\n(Deja en blanco para mantener el actual)`, contexto.titulo);
        
        // Si el usuario canceló
        if (nuevoTitulo === null) {
            return;
        }

        const nuevoTexto = prompt(`✏️ Editar texto:\n\n(Deja en blanco para mantener el actual)`, contexto.texto);
        
        // Si el usuario canceló
        if (nuevoTexto === null) {
            return;
        }

        // Preparar datos para enviar (solo enviar si hay cambios)
        const datosEdicion = {};
        
        if (nuevoTitulo.trim() && nuevoTitulo.trim() !== contexto.titulo) {
            datosEdicion.titulo = nuevoTitulo.trim();
        }
        
        if (nuevoTexto.trim() && nuevoTexto.trim() !== contexto.texto) {
            datosEdicion.texto = nuevoTexto.trim();
        }

        // Si no hay cambios
        if (Object.keys(datosEdicion).length === 0) {
            alert("ℹ️ No se detectaron cambios");
            return;
        }

        // Confirmar antes de guardar
        const cambios = [];
        if (datosEdicion.titulo) cambios.push("título");
        if (datosEdicion.texto) cambios.push("texto y relaciones automáticas");
        
        const confirmacion = confirm(`¿Confirmar cambios en: ${cambios.join(', ')}?\n\n${datosEdicion.texto ? '⚠️ Cambiar el texto recalculará todas las relaciones automáticamente.' : ''}`);
        
        if (!confirmacion) {
            return;
        }

        // Enviar edición
        const editRes = await axios.put(`/contexto/${id}`, datosEdicion);
        
        if (editRes.data.status === "editado") {
            alert(`✅ Contexto editado exitosamente!\n\n${datosEdicion.texto ? '🔄 Las relaciones se recalcularon automáticamente.' : ''}`);
            
            // Actualizar visualización
            mostrarContextos();
        } else {
            alert(`❌ Error: ${editRes.data.message || 'No se pudo editar'}`);
        }
        
    } catch (error) {
        alert(`❌ Error editando contexto: ${error.message}`);
    }
}

function cerrarModalEditar() {
    console.log("🚪 Cerrando modal de edición...");
    
    // Ocultar modal
    const modal = document.getElementById('modalEditarContexto');
    if (modal) {
        modal.classList.add('hidden');
    }
    
    // Limpiar formulario
    const campos = ['editarId', 'editarTitulo', 'editarTexto'];
    campos.forEach(campoId => {
        const campo = document.getElementById(campoId);
        if (campo) {
            campo.value = '';
        }
    });
    
    // Restaurar botón si estaba en estado de carga
    const botonGuardar = document.querySelector('button[onclick="guardarEdicionContexto()"]');
    if (botonGuardar) {
        botonGuardar.innerHTML = "💾 Guardar Cambios";
        botonGuardar.disabled = false;
    }
    
    // Limpiar variable de contexto
    contextoEditando = null;
    
    console.log("✅ Modal cerrado y limpiado correctamente");
}

async function guardarEdicionContexto() {
    console.log("🔄 Iniciando proceso de edición...");
    
    if (!contextoEditando) {
        console.error("❌ No hay contexto para editar");
        alert("❌ No hay contexto para editar");
        return;
    }

    // Obtener valores del formulario
    const nuevoTitulo = document.getElementById('editarTitulo').value.trim();
    const nuevoTexto = document.getElementById('editarTexto').value.trim();

    console.log("📝 Datos del formulario:", { nuevoTitulo, nuevoTexto });
    console.log("📝 Datos originales:", { 
        titulo: contextoEditando.tituloOriginal, 
        texto: contextoEditando.textoOriginal 
    });

    // Validaciones
    if (!nuevoTitulo) {
        alert("❌ El título no puede estar vacío");
        document.getElementById('editarTitulo').focus();
        return;
    }

    if (!nuevoTexto) {
        alert("❌ El contenido no puede estar vacío");
        document.getElementById('editarTexto').focus();
        return;
    }

    // Verificar si hay cambios
    const hayCambioTitulo = nuevoTitulo !== contextoEditando.tituloOriginal;
    const hayCambioTexto = nuevoTexto !== contextoEditando.textoOriginal;

    console.log("🔍 Análisis de cambios:", { hayCambioTitulo, hayCambioTexto });

    if (!hayCambioTitulo && !hayCambioTexto) {
        console.log("ℹ️ No se detectaron cambios");
        alert("ℹ️ No se detectaron cambios");
        return;
    }

    // Preparar datos para enviar
    const datosEdicion = {};
    
    if (hayCambioTitulo) {
        datosEdicion.titulo = nuevoTitulo;
    }
    
    if (hayCambioTexto) {
        datosEdicion.texto = nuevoTexto;
    }

    console.log("📤 Datos que se enviarán:", datosEdicion);

    // Confirmación con resumen de cambios
    let mensajeConfirmacion = "¿Confirmar los siguientes cambios?\n\n";
    
    if (hayCambioTitulo) {
        mensajeConfirmacion += `📝 Título: "${contextoEditando.tituloOriginal}" → "${nuevoTitulo}"\n`;
    }
    
    if (hayCambioTexto) {
        mensajeConfirmacion += `📄 Contenido: Se modificará el texto\n`;
        mensajeConfirmacion += `⚠️ Se recalcularán automáticamente las relaciones\n`;
    }

    const confirmacion = confirm(mensajeConfirmacion);
    if (!confirmacion) {
        console.log("❌ Usuario canceló la edición");
        return;
    }

    try {
        console.log("🚀 Enviando petición de edición...");
        
        // Mostrar indicador de carga
        const botonGuardar = document.querySelector('button[onclick="guardarEdicionContexto()"]');
        const textoOriginal = botonGuardar.innerHTML;
        botonGuardar.innerHTML = "⏳ Guardando...";
        botonGuardar.disabled = true;

        // Enviar edición
        const editRes = await axios.put(`/contexto/${contextoEditando.id}`, datosEdicion);
        
        console.log("📥 Respuesta del servidor:", editRes.data);
        
        if (editRes.data.status === "editado") {
            console.log("✅ Contexto editado exitosamente!");
            alert(`✅ Contexto editado exitosamente!\n\n${hayCambioTexto ? '🔄 Las relaciones se recalcularon automáticamente.' : ''}`);
            
            // Cerrar modal
            cerrarModalEditar();
            
            // Actualizar visualización
            console.log("🔄 Actualizando lista de contextos...");
            await mostrarContextos();
            console.log("✅ Lista actualizada correctamente");
            
        } else {
            console.error("❌ Error en la respuesta:", editRes.data);
            alert(`❌ Error: ${editRes.data.message || 'No se pudo editar'}`);
        }
        
    } catch (error) {
        console.error("❌ Error editando contexto:", error);
        alert(`❌ Error editando contexto: ${error.response?.data?.detail || error.message}`);
    } finally {
        // Restaurar botón
        const botonGuardar = document.querySelector('button[onclick="guardarEdicionContexto()"]');
        if (botonGuardar) {
            botonGuardar.innerHTML = "💾 Guardar Cambios";
            botonGuardar.disabled = false;
        }
        console.log("🔧 Botón restaurado");
    }
}

// Event listener para cerrar modal con Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        if (!document.getElementById('modalEditarContexto').classList.contains('hidden')) {
            cerrarModalEditar();
        } else {
            cerrarModalGrafo();
        }
    }
});

// Event listener para guardar con Ctrl+Enter en el modal de edición
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        if (!document.getElementById('modalEditarContexto').classList.contains('hidden')) {
            guardarEdicionContexto();
        }
    }
});

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