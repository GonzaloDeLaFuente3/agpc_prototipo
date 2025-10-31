// Variables globales
        let contextosData = {};
        let conversacionesData = {};
        let contextosOriginales = {};
        let conversacionesOriginales = {};

        // Inicialización
        document.addEventListener('DOMContentLoaded', function() {
            cargarTodosDatos();
        });

        async function cargarTodosDatos() {
            try {
                await Promise.all([
                    cargarContextos(),
                    cargarConversaciones()
                ]);
                actualizarEstadisticas();
                aplicarFiltros();
            } catch (error) {
                console.error('Error cargando datos:', error);
                mostrarError('Error cargando datos del sistema');
            }
        }

        async function cargarContextos() {
            try {
                const response = await axios.get('/contexto/');
                contextosOriginales = response.data;
                contextosData = { ...contextosOriginales };
                console.log(`Contextos cargados: ${Object.keys(contextosData).length}`);
            } catch (error) {
                console.error('Error cargando contextos:', error);
                contextosData = {};
            }
        }

        async function cargarConversaciones() {
            try {
                const response = await axios.get('/conversaciones/');
                conversacionesOriginales = response.data;
                conversacionesData = { ...conversacionesOriginales };
                console.log(`Conversaciones cargadas: ${Object.keys(conversacionesData).length}`);
            } catch (error) {
                console.error('Error cargando conversaciones:', error);
                conversacionesData = {};
            }
        }

        function actualizarEstadisticas() {
            const totalContextos = Object.keys(contextosData).length;
            const totalConversaciones = Object.keys(conversacionesData).length;
            const totalFragmentos = Object.values(conversacionesData)
                .reduce((sum, conv) => sum + (conv.total_fragmentos || 0), 0);

            document.getElementById('totalContextos').textContent = totalContextos;
            document.getElementById('totalConversaciones').textContent = totalConversaciones;
            document.getElementById('totalFragmentos').textContent = totalFragmentos;
        }

        function renderizarContextos() {
            const container = document.getElementById('listaContextos');
            const contador = document.getElementById('contadorContextos');
            
            const contextos = Object.entries(contextosData);
            contador.textContent = `(${contextos.length})`;
            
            if (contextos.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <div class="text-6xl mb-4">📭</div>
                        <p>No se encontraron contextos con los filtros aplicados</p>
                    </div>
                `;
                return;
            }

            const contextosHTML = contextos.map(([id, contexto]) => {
                const esTemporal = contexto.es_temporal;
                const tipoContexto = contexto.tipo_contexto || 'general';
                const palabrasClave = contexto.palabras_clave || [];
                const fecha = contexto.timestamp ? new Date(contexto.timestamp).toLocaleString() : null;
                
                const iconoTipo = {
                    'reunion': '👥', 'tarea': '📋', 'evento': '🎯',
                    'proyecto': '🚀', 'conocimiento': '📚', 'general': '📄'
                }[tipoContexto] || '📄';

                return `
                    <div class="contexto-card bg-gray-50 border border-gray-200 rounded-lg p-4 cursor-pointer"
                         onclick="verDetallesContexto('${id}')">
                        <div class="flex justify-between items-start mb-3">
                            <h3 class="font-semibold text-gray-800 flex items-center">
                                ${iconoTipo} ${contexto.titulo}
                            </h3>
                            <div class="flex space-x-1">
                                <span class="tag ${esTemporal ? 'tag-temporal' : 'tag-atemporal'}">
                                    ${esTemporal ? '🕒 Temporal' : '📋 Atemporal (No Temporal)'}
                                </span>
                            </div>
                        </div>
                        
                        <p class="text-gray-600 text-sm mb-3 line-clamp-3">
                            ${contexto.texto.substring(0, 200)}${contexto.texto.length > 200 ? '...' : ''}
                        </p>
                        
                        ${fecha ? `<p class="text-xs text-gray-500 mb-2">📅 ${fecha}</p>` : ''}
                        
                        <div class="flex flex-wrap gap-1 mb-2">
                            ${palabrasClave.slice(0, 5).map(palabra => 
                                `<span class="tag">#${palabra}</span>`
                            ).join('')}
                            ${palabrasClave.length > 5 ? `<span class="tag">+${palabrasClave.length - 5} más</span>` : ''}
                        </div>
                        
                        <div class="flex justify-between items-center text-xs text-gray-500">
                            <span>Tipo: ${tipoContexto}</span>
                            <span>ID: ${id.substring(0, 8)}...</span>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = contextosHTML;
        }

        function renderizarConversaciones() {
            const container = document.getElementById('listaConversaciones');
            const contador = document.getElementById('contadorConversaciones');
            
            const conversaciones = Object.entries(conversacionesData);
            contador.textContent = `(${conversaciones.length})`;
            
            if (conversaciones.length === 0) {
                container.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <div class="text-6xl mb-4">💬</div>
                        <p>No se encontraron conversaciones con los filtros aplicados</p>
                    </div>
                `;
                return;
            }

            const conversacionesHTML = conversaciones.map(([id, conversacion]) => {
                const tipo = conversacion.metadata?.tipo || 'general';
                const fecha = conversacion.fecha ? new Date(conversacion.fecha).toLocaleString() : 'Fecha no disponible';
                const participantes = conversacion.participantes || [];
                const totalFragmentos = conversacion.total_fragmentos || 0;
                
                const iconoTipo = {
                    'reunion': '👥', 'entrevista': '🎤', 'brainstorm': '💡',
                    'planning': '📋', 'general': '💬'
                }[tipo] || '💬';

                return `
                    <div class="conversacion-card bg-gray-50 border border-gray-200 rounded-lg p-4 cursor-pointer"
                         onclick="verDetallesConversacion('${id}')">
                        <div class="flex justify-between items-start mb-3">
                            <h3 class="font-semibold text-gray-800 flex items-center">
                                ${iconoTipo} ${conversacion.titulo || 'Sin título'}
                            </h3>
                            <span class="tag">${tipo}</span>
                        </div>
                        
                        <div class="grid grid-cols-2 gap-2 text-sm text-gray-600 mb-3">
                            <div>${totalFragmentos} fragmentos</div>
                            <div>👥 ${participantes.length} participantes</div>
                            <div class="col-span-2">📅 ${fecha}</div>
                        </div>
                        
                        ${participantes.length > 0 ? `
                            <div class="mb-3">
                                <div class="text-xs text-gray-500 mb-1">Participantes:</div>
                                <div class="flex flex-wrap gap-1">
                                    ${participantes.slice(0, 3).map(p => 
                                        `<span class="tag">${p}</span>`
                                    ).join('')}
                                    ${participantes.length > 3 ? `<span class="tag">+${participantes.length - 3} más</span>` : ''}
                                </div>
                            </div>
                        ` : ''}
                        
                        <div class="flex justify-between items-center text-xs text-gray-500">
                            <span>Created: ${new Date(conversacion.created_at || conversacion.fecha).toLocaleDateString()}</span>
                            <span>ID: ${id.substring(0, 8)}...</span>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = conversacionesHTML;
        }

        function aplicarFiltros() {
            const filtroTipo = document.getElementById('filtroTipo').value;
            const filtroTexto = document.getElementById('filtroTexto').value.toLowerCase();

            // Filtrar contextos
            contextosData = {};
            for (const [id, contexto] of Object.entries(contextosOriginales)) {
                let incluir = true;

                // Filtro por tipo temporal
                if (filtroTipo === 'temporal' && !contexto.es_temporal) incluir = false;
                if (filtroTipo === 'atemporal' && contexto.es_temporal) incluir = false;

                // Filtro por texto
                if (filtroTexto && !contexto.titulo.toLowerCase().includes(filtroTexto) && 
                    !contexto.texto.toLowerCase().includes(filtroTexto)) {
                    incluir = false;
                }

                if (incluir) {
                    contextosData[id] = contexto;
                }
            }

            // Filtrar conversaciones
            conversacionesData = {};
            for (const [id, conversacion] of Object.entries(conversacionesOriginales)) {
                let incluir = true;

                // Filtro por tipo temporal
                if (filtroTipo === 'temporal' || filtroTipo === 'atemporal') {
                    // Determinar si la conversación es temporal
                    // Una conversación es temporal si tiene al menos un fragmento temporal
                    const fragmentosIds = conversacion.fragmentos_ids || [];
                    const tieneFragmentosTemporal = fragmentosIds.some(fragId => {
                        const frag = contextosOriginales[fragId];
                        return frag && frag.es_temporal;
                    });

                    if (filtroTipo === 'temporal' && !tieneFragmentosTemporal) {
                        incluir = false;
                    }
                    if (filtroTipo === 'atemporal' && tieneFragmentosTemporal) {
                        incluir = false;
                    }
                }

                // Filtro por texto
                if (filtroTexto && !conversacion.titulo.toLowerCase().includes(filtroTexto)) {
                    incluir = false;
                }

                if (incluir) {
                    conversacionesData[id] = conversacion;
                }
            }

            // Re-renderizar
            renderizarContextos();
            renderizarConversaciones();
            actualizarEstadisticas();
        }

        function cambiarVista() {
            const vista = document.querySelector('input[name="tipoVista"]:checked').value;
            const seccionContextos = document.getElementById('seccionContextos');
            const seccionConversaciones = document.getElementById('seccionConversaciones');

            switch (vista) {
                case 'contextos':
                    seccionContextos.style.display = 'block';
                    seccionConversaciones.style.display = 'none';
                    seccionContextos.className = 'col-span-2 space-y-6';
                    break;
                case 'conversaciones':
                    seccionContextos.style.display = 'none';
                    seccionConversaciones.style.display = 'block';
                    seccionConversaciones.className = 'col-span-2 space-y-6';
                    break;
                case 'ambos':
                    seccionContextos.style.display = 'block';
                    seccionConversaciones.style.display = 'block';
                    seccionContextos.className = 'space-y-6';
                    seccionConversaciones.className = 'space-y-6';
                    break;
            }

            // Reinicializar la grilla
            const container = document.querySelector('.grid.grid-cols-1.lg\\:grid-cols-2');
            if (vista === 'contextos' || vista === 'conversaciones') {
                container.className = 'grid grid-cols-1 gap-8';
            } else {
                container.className = 'grid grid-cols-1 lg:grid-cols-2 gap-8';
            }
        }

        function verDetallesContexto(id) {
            const contexto = contextosOriginales[id];
            if (!contexto) return;

            const esTemporal = contexto.es_temporal;
            const fecha = contexto.timestamp ? new Date(contexto.timestamp).toLocaleString() : 'No especificada';
            const palabrasClave = contexto.palabras_clave || [];
            const tipoContexto = contexto.tipo_contexto || 'general';

            document.getElementById('modalTitulo').innerHTML = `
                📋 Contexto: ${contexto.titulo}
            `;

            document.getElementById('modalContenido').innerHTML = `
                <div class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Información General</h4>
                            <div class="space-y-2 text-sm">
                                <div><strong>ID:</strong> ${id}</div>
                                <div><strong>Tipo:</strong> ${tipoContexto}</div>
                                <div><strong>Temporal:</strong> ${esTemporal ? '✅ Sí' : '❌ No'}</div>
                                <div><strong>Creado:</strong> ${new Date(contexto.created_at).toLocaleString()}</div>
                                ${esTemporal ? `<div><strong>Fecha referencia:</strong> ${fecha}</div>` : ''}
                            </div>
                        </div>
                        
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Palabras Clave (${palabrasClave.length})</h4>
                            <div class="flex flex-wrap gap-1">
                                ${palabrasClave.map(palabra => 
                                    `<span class="tag">#${palabra}</span>`
                                ).join('')}
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-gray-50 p-4 rounded-lg">
                        <h4 class="font-semibold text-gray-700 mb-2">Contenido Completo</h4>
                        <div class="bg-white p-4 rounded border text-gray-700 whitespace-pre-wrap max-h-64 overflow-y-auto">
${contexto.texto}</div>
                    </div>
                </div>
            `;

            document.getElementById('modalDetalles').classList.remove('hidden');
        }

        function verDetallesConversacion(id) {
            const conversacion = conversacionesOriginales[id];
            if (!conversacion) return;

            const tipo = conversacion.metadata?.tipo || 'general';
            const fecha = conversacion.fecha ? new Date(conversacion.fecha).toLocaleString() : 'Fecha no disponible';
            const participantes = conversacion.participantes || [];
            const totalFragmentos = conversacion.total_fragmentos || 0;
            const metadata = conversacion.metadata || {};

            document.getElementById('modalTitulo').innerHTML = `
                💬 Conversación: ${conversacion.titulo || 'Sin título'}
            `;

            document.getElementById('modalContenido').innerHTML = `
                <div class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Información General</h4>
                            <div class="space-y-2 text-sm">
                                <div><strong>ID:</strong> ${id.substring(0, 16)}...</div>
                                <div><strong>Tipo:</strong> ${tipo}</div>
                                <div><strong>Fragmentos:</strong> ${totalFragmentos}</div>
                                <div><strong>Fecha:</strong> ${fecha}</div>
                                <div><strong>Creada:</strong> ${new Date(conversacion.created_at || conversacion.fecha).toLocaleString()}</div>
                            </div>
                        </div>
                        
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Participantes (${participantes.length})</h4>
                            <div class="space-y-1">
                                ${participantes.length > 0 ? 
                                    participantes.map(p => `<div class="tag">${p}</div>`).join('') :
                                    '<div class="text-gray-500 text-sm">No especificados</div>'
                                }
                            </div>
                        </div>
                    </div>
                    
                    ${Object.keys(metadata).length > 0 ? `
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Metadatos</h4>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                                ${Object.entries(metadata).map(([key, value]) => 
                                    `<div><strong>${key}:</strong> ${typeof value === 'object' ? JSON.stringify(value) : value}</div>`
                                ).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="bg-blue-50 p-4 rounded-lg border border-blue-200">
                        <h4 class="font-semibold text-blue-800 mb-2">Acciones</h4>
                        <div class="space-y-2">
                            <button onclick="verFragmentosConversacion('${id}')" 
                                    class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors text-sm">
                                Ver ${totalFragmentos} Fragmentos
                            </button>
                            <p class="text-blue-700 text-xs">Los fragmentos son las partes individuales en las que se dividió esta conversación para procesamiento.</p>
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('modalDetalles').classList.remove('hidden');
        }

        async function verFragmentosConversacion(conversacionId) {
            try {
                const response = await axios.get(`/conversacion/${conversacionId}/fragmentos`);
                const fragmentos = response.data;

                document.getElementById('modalTitulo').innerHTML = `
                    Fragmentos de Conversación (${fragmentos.length})
                `;

                const fragmentosHTML = fragmentos.map((fragmento, index) => {
                    const meta = fragmento.metadata;
                    const esTemporal = meta.es_temporal;
                    const tipoContexto = meta.tipo_contexto || 'general';
                    const palabrasClave = meta.palabras_clave || [];
                    const fecha = meta.timestamp ? new Date(meta.timestamp).toLocaleString() : null;

                    return `
                        <div class="border border-gray-200 rounded-lg p-4 bg-white">
                            <div class="flex justify-between items-start mb-2">
                                <h5 class="font-semibold text-gray-800">
                                    Fragmento ${meta.posicion_en_conversacion} de ${meta.total_fragmentos_conversacion}
                                </h5>
                                <div class="flex space-x-1">
                                    <span class="tag ${esTemporal ? 'tag-temporal' : 'tag-atemporal'}">
                                        ${esTemporal ? '🕒(Temporal) - ' : '📋(No Temporal) - '} ${tipoContexto}
                                    </span>
                                </div>
                            </div>
                            
                            <p class="text-gray-600 text-sm mb-3 bg-gray-50 p-3 rounded">
                                ${meta.texto}
                            </p>
                            
                            ${fecha ? `<p class="text-xs text-gray-500 mb-2">📅 ${fecha}</p>` : ''}
                            
                            <div class="flex flex-wrap gap-1 text-xs">
                                ${palabrasClave.slice(0, 8).map(palabra => 
                                    `<span class="tag">#${palabra}</span>`
                                ).join('')}
                                ${palabrasClave.length > 8 ? `<span class="tag">+${palabrasClave.length - 8}</span>` : ''}
                            </div>
                        </div>
                    `;
                }).join('');

                document.getElementById('modalContenido').innerHTML = `
                    <div class="space-y-4 max-h-96 overflow-y-auto">
                        ${fragmentosHTML}
                    </div>
                `;

            } catch (error) {
                console.error('Error cargando fragmentos:', error);
                mostrarError('Error cargando fragmentos de la conversación');
            }
        }

        function cerrarModal() {
            document.getElementById('modalDetalles').classList.add('hidden');
        }

        async function actualizarTodo() {
            const boton = event.target;
            const textoOriginal = boton.textContent;
            
            boton.textContent = 'Actualizando...';
            boton.disabled = true;
            
            try {
                await cargarTodosDatos();
                mostrarExito('Datos actualizados correctamente');
            } catch (error) {
                mostrarError('Error al actualizar los datos');
            } finally {
                boton.textContent = textoOriginal;
                boton.disabled = false;
            }
        }

        function mostrarError(mensaje) {
            const toast = document.createElement('div');
            toast.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
            toast.textContent = mensaje;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 5000);
        }

        function mostrarExito(mensaje) {
            const toast = document.createElement('div');
            toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
            toast.textContent = mensaje;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }

        // Cerrar modal con Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                cerrarModal();
            }
        });

        // Cerrar modal clickeando fuera
        document.getElementById('modalDetalles').addEventListener('click', function(e) {
            if (e.target === this) {
                cerrarModal();
            }
        });