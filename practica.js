// "compases" es un arreglo (array) de objetos.
// Cada objeto guarda los datos de un compás creado por el usuario.
let compases = [];

// Referencias a elementos que ya existen en el HTML
const btnAgregar = document.getElementById('btnAgregar');
const inputNombre = document.getElementById('nombreCompas');
const inputTiempos = document.getElementById('numTiempos');
const contenedor = document.getElementById('compasesGenerados');

btnAgregar.addEventListener('click', function () {
  const nombre = inputNombre.value.trim();
  const tiempos = parseInt(inputTiempos.value);

  // Validación simple antes de crear nada
  if (nombre === '' || isNaN(tiempos) || tiempos < 2) {
    alert('Ingresa un nombre y un número de tiempos válido (mínimo 2).');
    return;
  }

  // Objeto que representa el nuevo compás
  // Se usa Date.now() como id único para poder identificarlo después
  const nuevoCompas = {
    id: Date.now(),
    nombre: nombre,
    tiempos: tiempos
  };

  compases.push(nuevoCompas); // se guarda en el arreglo de objetos
  renderizarCompas(nuevoCompas); // se dibuja en pantalla

  // Limpiar formulario para el próximo ingreso
  inputNombre.value = '';
  inputTiempos.value = '';
});

// Esta función crea elementos HTML nuevos a partir de un objeto "compas"
function renderizarCompas(compas) {
  // Crear el título con document.createElement
  const titulo = document.createElement('p');
  titulo.textContent = compas.nombre + ' (creado por ti)';

  // Crear la fila que va a contener los bloques numerados
  const fila = document.createElement('div');
  fila.className = 'row';

  // Crear un bloque <div> por cada tiempo del compás
  for (let i = 1; i <= compas.tiempos; i++) {
    const bloque = document.createElement('div');
    bloque.textContent = i;
    bloque.className = 'col p-3 border-end border-dark ' +
      (i === 1 ? 'bg-danger text-white' : 'bg-warning text-black');

    // Manipulación: al hacer clic sobre un bloque ya existente,
    // le cambiamos las clases para elegir el acento del "beat"
    bloque.addEventListener('click', function () {
      bloque.classList.toggle('bg-danger');
      bloque.classList.toggle('bg-warning');
      bloque.classList.toggle('text-white');
      bloque.classList.toggle('text-black');
    });

    fila.appendChild(bloque); // se inserta el bloque dentro de la fila
  }

  // Botón para eliminar
  const btnEliminar = document.createElement('button');
  btnEliminar.textContent = 'Eliminar este compás';
  btnEliminar.className = 'btn btn-sm btn-outline-danger mt-2 mb-4';
  btnEliminar.addEventListener('click', function () {
    titulo.remove();
    fila.remove();
    btnEliminar.remove();
    // También lo sacamos del arreglo de objetos
    compases = compases.filter(function (c) {
      return c.id !== compas.id;
    });
  });

  // Insertar todo lo creado dentro del contenedor del HTML
  contenedor.appendChild(titulo);
  contenedor.appendChild(fila);
  contenedor.appendChild(btnEliminar);
}

// Manipulación de elementos que ya existían en el HTML original:
// Se hicieron clickeables los bloques de las cifras indicadoras originales.
// Esto permite, por ejemplo, acentuar el segundo "beat" en un compás de 4/4, si el usuario lo desea.
const bloquesExistentes = document.querySelectorAll('.container-fluid .row .col');
bloquesExistentes.forEach(function (bloque) {
  bloque.addEventListener('click', function () {
    bloque.classList.toggle('bg-danger');
    bloque.classList.toggle('bg-warning');
    bloque.classList.toggle('text-white');
    bloque.classList.toggle('text-black');
  });
});
