/* Formulario para ingresar información (vista de captura).
   - Si el usuario viene del catálogo, prellena el producto elegido
     leyéndolo desde la URL (?producto=...&precio=...)
   - Valida los campos obligatorios, el formato de correo/teléfono
     y que la fecha de entrega no sea en el pasado
   - Si todo es válido, arma la URL de confirmación con los datos
     del pedido y navega hacia allá (interacción solo por URL,
     ya que todavía no se implementa el backend) */

const form = document.querySelector('#form-pedido');
const selectedBox = document.querySelector('[data-selected-product]');
const tipoArregloSelect = document.querySelector('#tipoArreglo');
const fechaInput = document.querySelector('#fechaEntrega');
const statusBox = document.querySelector('[data-form-status]');

const REGEX_EMAIL = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;
const REGEX_TELEFONO = /^(\+?56)?\s?9\s?\d{4}\s?\d{4}$/; // celular chileno, con o sin +56

// Prellenar con datos que vienen del catálogo
function prellenarDesdeURL() {
  const params = new URLSearchParams(window.location.search);
  const producto = params.get('producto');
  const precio = params.get('precio');

  if (producto && tipoArregloSelect) {
    const opcionExiste = Array.from(tipoArregloSelect.options).some((op) => op.value === producto);
    if (!opcionExiste) {
      const opcion = document.createElement('option');
      opcion.value = producto;
      opcion.textContent = producto;
      tipoArregloSelect.appendChild(opcion);
    }
    tipoArregloSelect.value = producto;
  }

  if (producto && selectedBox) {
    selectedBox.hidden = false;
    selectedBox.querySelector('[data-selected-name]').textContent = producto;
    selectedBox.querySelector('[data-selected-price]').textContent = precio
      ? Number(precio).toLocaleString('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 })
      : 'Precio a confirmar';
  }
}

// Fecha mínima = hoy
function limitarFechaMinima() {
  if (!fechaInput) return;
  const hoy = new Date().toISOString().split('T')[0];
  fechaInput.min = hoy;
}

// Utilidades de validación / mensajes
function marcarError(campo, mensaje) {
  const wrapper = campo.closest('.field');
  wrapper.classList.add('has-error');
  wrapper.querySelector('.error-msg').textContent = mensaje;
}

function limpiarError(campo) {
  const wrapper = campo.closest('.field');
  wrapper.classList.remove('has-error');
}

function validarCampo(campo) {
  limpiarError(campo);
  const valor = campo.value.trim();

  if (campo.hasAttribute('required')) {
    if (campo.type === 'checkbox' && !campo.checked) {
      marcarError(campo, 'Debes aceptar las condiciones para continuar.');
      return false;
    }
    if (campo.type !== 'checkbox' && valor === '') {
      marcarError(campo, 'Este campo es obligatorio.');
      return false;
    }
  }

  if (campo.id === 'nombre' && valor.length > 0 && valor.length < 3) {
    marcarError(campo, 'Ingresa un nombre de al menos 3 letras.');
    return false;
  }

  if (campo.id === 'email' && valor !== '' && !REGEX_EMAIL.test(valor)) {
    marcarError(campo, 'Ingresa un correo con formato válido (ej: nombre@correo.com).');
    return false;
  }

  if (campo.id === 'telefono' && valor !== '' && !REGEX_TELEFONO.test(valor)) {
    marcarError(campo, 'Ingresa un celular chileno válido (ej: +56 9 1234 5678).');
    return false;
  }

  if (campo.id === 'direccion' && valor.length > 0 && valor.length < 6) {
    marcarError(campo, 'Ingresa una dirección más específica.');
    return false;
  }

  if (campo.id === 'fechaEntrega' && valor !== '') {
    const hoy = new Date().toISOString().split('T')[0];
    if (valor < hoy) {
      marcarError(campo, 'La fecha de entrega no puede ser anterior a hoy.');
      return false;
    }
  }

  return true;
}

// Envío del formulario
function initValidacionEnVivo() {
  form.querySelectorAll('input, select, textarea').forEach((campo) => {
    campo.addEventListener('blur', () => validarCampo(campo));
  });
}

function initEnvio() {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    statusBox.classList.remove('is-visible');

    const campos = Array.from(form.querySelectorAll('input, select, textarea'));
    const resultados = campos.map((campo) => validarCampo(campo));
    const esValido = resultados.every(Boolean);

    if (!esValido) {
      statusBox.textContent = 'Revisa los campos marcados en rojo antes de continuar.';
      statusBox.classList.add('is-visible');
      const primerError = form.querySelector('.field.has-error input, .field.has-error select, .field.has-error textarea');
      if (primerError) primerError.focus();
      return;
    }

    // Se arman los datos del pedido y los pasamos por la URL hacia
    // la pantalla de confirmación (sin backend por ahora)
    const datos = new URLSearchParams({
      nombre: form.nombre.value.trim(),
      email: form.email.value.trim(),
      telefono: form.telefono.value.trim(),
      producto: form.tipoArreglo.value,
      fecha: form.fechaEntrega.value,
      direccion: form.direccion.value.trim(),
      mensaje: form.mensaje.value.trim(),
    });

    window.location.href = `confirmacion.html?${datos.toString()}`;
  });
}

prellenarDesdeURL();
limitarFechaMinima();
initValidacionEnVivo();
initEnvio();
