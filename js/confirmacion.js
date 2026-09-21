/* Vista de resultado/confirmación.
   Lee directamente de los parámetros de la URL que arma pedido.js
   y los pinta en el DOM. [Implementación sin backend.] */

const contenidoConDatos = document.querySelector('[data-confirm-content]');
const contenidoSinDatos = document.querySelector('[data-empty-order]');

function generarNumeroPedido() {
  const aleatorio = Math.floor(1000 + Math.random() * 9000);
  return `FV-${new Date().getFullYear()}-${aleatorio}`;
}

function formatearFecha(valor) {
  if (!valor) return '—';
  const fecha = new Date(`${valor}T00:00:00`);
  return fecha.toLocaleDateString('es-CL', { day: 'numeric', month: 'long', year: 'numeric' });
}

function pintarResumen() {
  const params = new URLSearchParams(window.location.search);
  const nombre = params.get('nombre');
  const email = params.get('email');

  // Si faltan los datos mínimos, probablemente se llegó a esta
  // página escribiendo la URL a mano, no desde el formulario.
  if (!nombre || !email) {
    contenidoConDatos.hidden = true;
    contenidoSinDatos.hidden = false;
    return;
  }

  document.querySelector('[data-order-number]').textContent = generarNumeroPedido();
  document.querySelector('[data-nombre]').textContent = nombre;
  document.querySelector('[data-email]').textContent = email;
  document.querySelector('[data-telefono]').textContent = params.get('telefono') || '—';
  document.querySelector('[data-producto]').textContent = params.get('producto') || '—';
  document.querySelector('[data-fecha]').textContent = formatearFecha(params.get('fecha'));
  document.querySelector('[data-direccion]').textContent = params.get('direccion') || '—';

  const mensaje = params.get('mensaje');
  const mensajeFila = document.querySelector('[data-mensaje-fila]');
  if (mensaje) {
    document.querySelector('[data-mensaje]').textContent = mensaje;
  } else {
    mensajeFila.hidden = true;
  }
}

pintarResumen();
