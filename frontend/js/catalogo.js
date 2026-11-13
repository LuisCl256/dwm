/* Vista de listado/consulta de información.
   Pinta las tarjetas de producto a partir de un arreglo de datos.
   Filtra por categoría y por texto de búsqueda (manipulación DOM).
   Al pedir un producto, agrega al carrito y navega a pedido.html
   pasando los datos por la URL (?producto=...&precio=...). */

const PRODUCTOS = [
  { id: 'ramo-aurora', nombre: 'Ramo Aurora', categoria: 'ramos', precio: 18990,
    desc: 'Rosas y ranúnculos en tonos coral, atados con lino natural.', color: '#E7B49A',
    imagen: 'img/ramo-aurora.jpg' },
  { id: 'ramo-silvestre', nombre: 'Ramo Silvestre', categoria: 'ramos', precio: 15990,
    desc: 'Flores de campo mixtas, estilo libre y espontáneo.', color: '#C9B98C',
    imagen: 'img/ramo-silvestre.jpeg' },
  { id: 'ramo-vida-nueva', nombre: 'Ramo Vida Nueva', categoria: 'ramos', precio: 21990,
    desc: 'Ideal para nacimientos y nuevos comienzos.', color: '#D9C7A8',
    imagen: 'img/ramo-vida-nueva.jpg' },
  { id: 'caja-terracota', nombre: 'Caja Terracota', categoria: 'cajas', precio: 24990,
    desc: 'Arreglo compacto presentado en cerámica artesanal.', color: '#C98B6B' },
  { id: 'caja-atardecer', nombre: 'Caja Atardecer', categoria: 'cajas', precio: 27990,
    desc: 'Girasoles y flores naranjas en caja de madera clara.', color: '#E0A45C' },
  { id: 'centro-boda-clasica', nombre: 'Centro de Mesa Boda Clásica', categoria: 'bodas', precio: 45990,
    desc: 'Centro de mesa en tonos blancos y verdes para recepciones.', color: '#AEBBA2' },
  { id: 'arco-ceremonia', nombre: 'Arco Floral Ceremonia', categoria: 'bodas', precio: 189990,
    desc: 'Arco decorativo completo para ceremonias al aire libre.', color: '#94A78C' },
  { id: 'suculenta-maceta', nombre: 'Suculenta en Maceta', categoria: 'plantas', precio: 9990,
    desc: 'Suculenta de bajo cuidado en maceta de cerámica.', color: '#8FA07E',
    imagen: 'img/suculenta.jpg' },
  { id: 'orquidea-phalaenopsis', nombre: 'Orquídea Phalaenopsis', categoria: 'plantas', precio: 32990,
    desc: 'Orquídea a elección en maceta decorativa, larga floración.', color: '#D8CFC2',
    imagen: 'img/orquidea.jpg'},
];

const CATEGORIAS = {
  todos: 'Todos',
  ramos: 'Ramos',
  cajas: 'Cajas florales',
  bodas: 'Bodas & Eventos',
  plantas: 'Plantas',
};

const grid = document.querySelector('[data-product-grid]');
const filterBar = document.querySelector('[data-filter-bar]');
const emptyState = document.querySelector('[data-empty-state]');
const searchInput = document.querySelector('[data-catalog-search]');

let categoriaActiva = 'todos';

function formatearPrecio(valor) {
  return valor.toLocaleString('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
}

function crearTarjeta(producto) {
  const article = document.createElement('article');
  article.className = 'card product-card';
  article.dataset.categoria = producto.categoria;
  article.dataset.nombre = producto.nombre.toLowerCase();

  const media = producto.imagen
    ? `<img src="${producto.imagen}" alt="${producto.nombre}" loading="lazy">`
    : `<svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <circle cx="32" cy="32" r="10" fill="${producto.color}" />
        <circle cx="18" cy="24" r="8" fill="${producto.color}99" />
        <circle cx="46" cy="24" r="8" fill="${producto.color}99" />
        <circle cx="18" cy="42" r="8" fill="${producto.color}66" />
        <circle cx="46" cy="42" r="8" fill="${producto.color}66" />
      </svg>`;

  article.innerHTML = `
    <div class="product-card__media" style="background:${producto.color}33;">
      ${media}
    </div>
    <div class="product-card__body">
      <span class="product-card__tag">${CATEGORIAS[producto.categoria]}</span>
      <h3 class="product-card__name">${producto.nombre}</h3>
      <p class="product-card__desc">${producto.desc}</p>
      <div class="product-card__footer">
        <span class="product-card__price">${formatearPrecio(producto.precio)}</span>
        <button type="button" class="btn btn--outline" data-pedir="${producto.id}">Pedir este</button>
      </div>
    </div>
  `;
  return article;
}

function pintarProductos(lista) {
  grid.innerHTML = '';
  lista.forEach((producto) => grid.appendChild(crearTarjeta(producto)));
  emptyState.classList.toggle('is-visible', lista.length === 0);
}

function aplicarFiltros() {
  const termino = (searchInput.value || '').trim().toLowerCase();
  const filtrados = PRODUCTOS.filter((producto) => {
    const coincideCategoria = categoriaActiva === 'todos' || producto.categoria === categoriaActiva;
    const coincideBusqueda = producto.nombre.toLowerCase().includes(termino);
    return coincideCategoria && coincideBusqueda;
  });
  pintarProductos(filtrados);
}

function initFiltros() {
  filterBar.addEventListener('click', (event) => {
    const chip = event.target.closest('[data-categoria]');
    if (!chip) return;

    categoriaActiva = chip.dataset.categoria;
    filterBar.querySelectorAll('[data-categoria]').forEach((el) => {
      el.setAttribute('aria-pressed', String(el === chip));
    });
    aplicarFiltros();
  });
}

function initBusqueda() {
  searchInput.addEventListener('input', aplicarFiltros);
}

// Al hacer clic en "Pedir este": se suma al carrito y se
// envía el producto elegido a pedido.html mediante la URL,
// que es la única forma de "recordar" el dato sin backend.
function initPedidos() {
  grid.addEventListener('click', (event) => {
    const boton = event.target.closest('[data-pedir]');
    if (!boton) return;

    const producto = PRODUCTOS.find((item) => item.id === boton.dataset.pedir);
    if (!producto) return;

    addToCart();

    const destino = new URL('pedido.html', window.location.href);
    destino.searchParams.set('producto', producto.nombre);
    destino.searchParams.set('precio', producto.precio);
    window.location.href = destino.toString();
  });
}

// Si se llega desde el buscador del header (?buscar=algo),
// se refleja en el campo de búsqueda de esta página.
function aplicarBusquedaDesdeURL() {
  const params = new URLSearchParams(window.location.search);
  const termino = params.get('buscar');
  if (termino) searchInput.value = termino;
}

aplicarBusquedaDesdeURL();
initFiltros();
initBusqueda();
initPedidos();
aplicarFiltros();
