/* Comportamiento compartido por todas las páginas del sitio:
   - Menú de navegación en móvil (abrir/cerrar)
   - Panel de búsqueda desplegable
   - Contador del carrito (simulado con sessionStorage, ya que
     todavía no se implementa el backend)
   - Año automático y mini-formulario de newsletter en el footer */

document.addEventListener('DOMContentLoaded', () => {
  initNavToggle();
  initSearchPanel();
  renderCartBadge();
  initFooterExtras();
});

// Menú móvil
function initNavToggle() {
  const toggle = document.querySelector('.nav-toggle');
  const header = document.querySelector('.site-header');
  if (!toggle || !header) return;

  toggle.addEventListener('click', () => {
    const isOpen = header.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });
}

// Buscador
function initSearchPanel() {
  const searchBtn = document.querySelector('[data-action="toggle-search"]');
  const panel = document.querySelector('.search-panel');
  if (!searchBtn || !panel) return;

  searchBtn.addEventListener('click', () => {
    const isOpen = panel.classList.toggle('is-open');
    searchBtn.setAttribute('aria-expanded', String(isOpen));
    if (isOpen) {
      const input = panel.querySelector('input');
      if (input) input.focus();
    }
  });

  // Si el buscador del header envía texto, se manda al catálogo
  // como parámetro de URL para que esa página filtre los resultados.
  const form = panel.querySelector('form');
  if (form) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const term = form.querySelector('input').value.trim();
      const url = new URL('catalogo.html', window.location.href);
      if (term) url.searchParams.set('buscar', term);
      window.location.href = url.toString();
    });
  }
}

// Simulación de carrito
function getCartCount() {
  return Number(sessionStorage.getItem('florVidaCartCount') || 0);
}

function setCartCount(value) {
  sessionStorage.setItem('florVidaCartCount', String(value));
  renderCartBadge();
}

function addToCart() {
  setCartCount(getCartCount() + 1);
}

function renderCartBadge() {
  const badge = document.querySelector('[data-cart-count]');
  if (badge) badge.textContent = getCartCount();
}

// Footer: año y newsletter de ejemplo
function initFooterExtras() {
  const yearEl = document.querySelector('[data-current-year]');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  const newsletterForm = document.querySelector('.newsletter');
  const msg = document.querySelector('.newsletter-msg');
  if (!newsletterForm || !msg) return;

  newsletterForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const input = newsletterForm.querySelector('input');
    const email = input.value.trim();
    const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    if (!isValidEmail) {
      msg.textContent = 'Ingresa un correo válido para suscribirte.';
      return;
    }
    msg.textContent = `¡Gracias! Te escribiremos a ${email}.`;
    newsletterForm.reset();
  });
}
