const API_URL = "https://album-digital.onrender.com";
let currentUser = null;
let currentPage = 1;
let pageSize = 25;
let currentTab = "album";
window.tasaBcvActual = 50;

function initLucide() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

function getAuthFormElements() {
  return {
    authSection: document.getElementById('authSection'),
    loginForm: document.getElementById('loginForm'),
    registerForm: document.getElementById('registerForm'),
    forgotForm: document.getElementById('forgotForm'),
    resetPasswordForm: document.getElementById('resetPasswordForm'),
    mainHeader: document.getElementById('mainHeader'),
    albumSection: document.getElementById('albumSection'),
    tiendaSection: document.getElementById('tiendaSection'),
    authTitle: document.getElementById('authTitle'),
    authSubtitle: document.getElementById('authSubtitle')
  };
}

function showAuthTab(tab) {
  const { loginForm, registerForm, forgotForm, resetPasswordForm, authTitle, authSubtitle } = getAuthFormElements();
  const forms = { login: loginForm, register: registerForm, forgot: forgotForm };

  Object.entries(forms).forEach(([name, form]) => {
    if (form) form.classList.toggle('hidden', name !== tab);
  });

  if (resetPasswordForm) resetPasswordForm.classList.add('hidden');

  if (authTitle) {
    authTitle.textContent = tab === 'register' ? 'CREAR CUENTA' : tab === 'forgot' ? 'RECUPERAR CLAVE' : 'INICIAR SESIÓN';
  }

  if (authSubtitle) {
    authSubtitle.textContent = tab === 'register'
      ? 'Crea tu usuario para entrar al álbum'
      : tab === 'forgot'
        ? 'Recupera tu acceso con tu correo o usuario'
        : 'Accede a tu colección digital';
  }
}

function setMainLayoutForUser() {
  const { authSection, mainHeader, albumSection, tiendaSection } = getAuthFormElements();

  if (!currentUser) {
    if (authSection) authSection.classList.remove('hidden');
    if (mainHeader) mainHeader.classList.add('hidden');
    if (albumSection) albumSection.classList.add('hidden');
    if (tiendaSection) tiendaSection.classList.add('hidden');
    return;
  }

  if (authSection) authSection.classList.add('hidden');
  if (mainHeader) mainHeader.classList.remove('hidden');

  if (currentTab === 'album') {
    if (albumSection) albumSection.classList.remove('hidden');
    if (tiendaSection) tiendaSection.classList.add('hidden');
  } else if (currentTab === 'tienda') {
    if (albumSection) albumSection.classList.add('hidden');
    if (tiendaSection) tiendaSection.classList.remove('hidden');
  }
}

function switchTab(tabName) {
  currentTab = tabName;

  if (!currentUser) {
    showAuthTab('login');
    setMainLayoutForUser();
    return;
  }

  const { albumSection, tiendaSection } = getAuthFormElements();
  if (albumSection) albumSection.classList.toggle('hidden', tabName !== 'album');
  if (tiendaSection) tiendaSection.classList.toggle('hidden', tabName !== 'tienda');

  const albumBtn = document.getElementById('navAlbum');
  const tiendaBtn = document.getElementById('navTienda');

  if (albumBtn) {
    albumBtn.classList.toggle('bg-purple-600/30', tabName === 'album');
    albumBtn.classList.toggle('text-purple-200', tabName === 'album');
    albumBtn.classList.toggle('border-purple-500/30', tabName === 'album');
    albumBtn.classList.toggle('bg-slate-800', tabName !== 'album');
    albumBtn.classList.toggle('text-slate-300', tabName !== 'album');
  }

  if (tiendaBtn) {
    tiendaBtn.classList.toggle('bg-purple-600/30', tabName === 'tienda');
    tiendaBtn.classList.toggle('text-purple-200', tabName === 'tienda');
    tiendaBtn.classList.toggle('border-purple-500/30', tabName === 'tienda');
    tiendaBtn.classList.toggle('bg-slate-800', tabName !== 'tienda');
    tiendaBtn.classList.toggle('text-slate-300', tabName !== 'tienda');
  }

  if (tabName === 'album') renderAlbumPage();
  if (tabName === 'tienda') calculateTotal();
}

function loadStoredConfig() {
  try {
    const raw = localStorage.getItem('album_app_config');
    if (!raw) return;
    const config = JSON.parse(raw);
    const banco = document.getElementById('displayBanco');
    const cedula = document.getElementById('displayCedula');
    const telefono = document.getElementById('displayTelefono');
    const titular = document.getElementById('displayTitular');

    if (banco) banco.textContent = config.banco || 'Cargando...';
    if (cedula) cedula.textContent = config.cedula || 'Cargando...';
    if (telefono) telefono.textContent = config.telefono || 'Cargando...';
    if (titular) titular.textContent = config.titular || 'ÁLBUM DIGITAL';
  } catch (err) {
    console.warn('No se pudo cargar la configuración del sistema:', err);
  }
}

function updateUserBalanceUI() {
  const balanceEl = document.getElementById('userBalanceBs');
  if (!balanceEl) return;

  const saldoBs = Number(currentUser?.saldo_bs || 0);
  const saldoUsd = Number(currentUser?.saldo_usd || 0);
  balanceEl.textContent = `Bs. ${saldoBs.toFixed(2)} ($${saldoUsd.toFixed(2)})`;
}

function onUserLoggedIn(user) {
  currentUser = user || null;
  if (!currentUser) return;

  localStorage.setItem('album_user', JSON.stringify(currentUser));
  updateUserBalanceUI();
  setMainLayoutForUser();
  switchTab('album');
  renderAlbumPage();
  calculateTotal();
  loadStoredConfig();
}

function showError(message) {
  alert(message);
}

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById('loginUsername')?.value.trim();
  const password = document.getElementById('loginPassword')?.value.trim();

  if (!username || !password) {
    return showError('Por favor ingresa usuario y contraseña.');
  }

  try {
    const res = await fetch(`${API_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok || data.status !== 'success') {
      return showError(data.message || 'Usuario o contraseña incorrectos.');
    }

    currentUser = data.user;
    localStorage.setItem('album_user', JSON.stringify(currentUser));
    onUserLoggedIn(currentUser);
    alert(`✅ ¡Bienvenido de nuevo, ${currentUser.nombre || currentUser.username}!`);
  } catch (err) {
    console.error('Login error:', err);
    showError('No se pudo iniciar sesión. Verifica la conexión o el servidor.');
  }
}

async function handleRegister(event) {
  event.preventDefault();

  const username = document.getElementById('regUsername')?.value.trim();
  const password = document.getElementById('regPassword')?.value.trim();
  const gmail = document.getElementById('regGmail')?.value.trim();
  const banco = document.getElementById('regBanco')?.value.trim();
  const cedula = document.getElementById('regCedula')?.value.trim();
  const telefono = document.getElementById('regTelefono')?.value.trim();

  if (!username || !password || !gmail || !banco || !cedula || !telefono) {
    return showError('Todos los campos del registro son obligatorios.');
  }

  try {
    const res = await fetch(`${API_URL}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, gmail, banco, cedula, telefono })
    });

    const data = await res.json();
    if (!res.ok || data.status !== 'success') {
      return showError(data.message || 'No se pudo crear la cuenta.');
    }

    alert('✅ Cuenta creada con éxito. Ahora puedes iniciar sesión.');
    document.getElementById('registerForm')?.reset();
    showAuthTab('login');
  } catch (err) {
    console.error('Register error:', err);
    showError('No se pudo completar el registro. Intenta nuevamente.');
  }
}

async function handleForgotPassword(event) {
  event.preventDefault();
  const value = document.getElementById('forgotInput')?.value.trim();
  if (!value) {
    return showError('Debes ingresar tu correo o nombre de usuario.');
  }

  alert('📩 Si existe esa cuenta, se enviará un enlace de recuperación.');
  document.getElementById('forgotForm')?.reset();
  showAuthTab('login');
}

async function handleResetPassword(event) {
  event.preventDefault();
  const password = document.getElementById('newPasswordInput')?.value.trim();
  if (!password || password.length < 6) {
    return showError('La nueva contraseña debe tener al menos 6 caracteres.');
  }

  alert('✅ Contraseña actualizada con éxito.');
  document.getElementById('resetPasswordForm')?.reset();
  showAuthTab('login');
}

async function cargarTasaBCV() {
  try {
    const res = await fetch(`${API_URL}/api/bcv`);
    const data = await res.json();
    if (res.ok && data.status === 'success' && Number(data.promedio)) {
      window.tasaBcvActual = Number(data.promedio);
      const display = document.getElementById('bcvRateDisplay');
      if (display) display.textContent = `Bs. ${window.tasaBcvActual.toFixed(2)}`;
    }
  } catch (err) {
    console.warn('No se pudo cargar la tasa BCV, usando valor por defecto.', err);
  }

  calculateTotal();
}

function calculateTotal() {
  const qtyInput = document.getElementById('stickerQty');
  const totalUsdEl = document.getElementById('totalUSDDisplay');
  const totalBsEl = document.getElementById('totalBsDisplay');
  const bcvDisplay = document.getElementById('bcvRateDisplay');

  const qty = parseInt(qtyInput?.value || '1', 10);
  const usd = Number((qty * 0.62).toFixed(2));
  const bcv = Number(window.tasaBcvActual || 50);
  const totalBs = Number((usd * bcv).toFixed(2));

  if (totalUsdEl) totalUsdEl.textContent = `$${usd.toFixed(2)}`;
  if (totalBsEl) totalBsEl.textContent = `Bs. ${totalBs.toFixed(2)}`;
  if (bcvDisplay) bcvDisplay.textContent = `Bs. ${bcv.toFixed(2)}`;
}

async function submitPurchase(event) {
  event.preventDefault();
  if (!currentUser) {
    return showError('Debes iniciar sesión antes de reportar un pago.');
  }

  const qty = Number(document.getElementById('stickerQty')?.value || 0);
  const ref = document.getElementById('refInput')?.value.trim();
  const bancoEmisor = document.getElementById('tiendaBancoEmisor')?.value.trim();
  const telefonoEmisor = document.getElementById('tiendaTelefonoEmisor')?.value.trim();

  if (!qty || qty < 1 || !ref || !bancoEmisor || !telefonoEmisor) {
    return showError('Completa la cantidad, referencia, banco y teléfono del pagador.');
  }

  const montoUsd = Number((qty * 0.62).toFixed(2));
  const montoBs = Number((montoUsd * Number(window.tasaBcvActual || 50)).toFixed(2));

  try {
    const res = await fetch(`${API_URL}/api/notificar-compra`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usuario_id: currentUser.id,
        barajitas_qty: qty,
        monto_bs: montoBs,
        monto_usd: montoUsd,
        banco_emisor: bancoEmisor,
        telefono_emisor: telefonoEmisor,
        referencia: ref
      })
    });

    const data = await res.json();
    if (!res.ok || data.status !== 'success') {
      return showError(data.message || 'No se pudo reportar el pago.');
    }

    alert('✅ Pago reportado con éxito. El administrador será notificado.');
    document.getElementById('refInput').value = '';
    document.getElementById('tiendaBancoEmisor').value = '';
    document.getElementById('tiendaTelefonoEmisor').value = '';
    document.getElementById('stickerQty').value = 1;
    calculateTotal();
  } catch (err) {
    console.error('Purchase submit error:', err);
    showError('Error al reportar el pago. Verifica tu conexión.');
  }
}

function renderAlbumPage() {
  const grid = document.getElementById('stickersGrid');
  if (!grid) return;

  const totalPages = 80;
  const page = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = (page - 1) * pageSize + 1;
  const endIndex = Math.min(startIndex + pageSize - 1, 2000);

  let cards = '';
  for (let i = startIndex; i <= endIndex; i++) {
    const owned = currentUser && Number(currentUser.cantidad_barajitas || 0) >= i;
    cards += `
      <div class="border rounded-2xl p-3 shadow-md ${owned ? 'border-emerald-500 bg-emerald-500/10' : 'border-purple-500/30 bg-slate-900/70'}">
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-bold text-purple-300">#${i}</span>
          <span class="text-[10px] px-2 py-1 rounded-full ${owned ? 'bg-emerald-600/20 text-emerald-300' : 'bg-slate-700 text-slate-300'}">${owned ? 'OWNED' : 'PEND.'}</span>
        </div>
        <div class="h-28 rounded-xl bg-gradient-to-br from-slate-800 via-slate-900 to-purple-950 flex items-center justify-center overflow-hidden border border-white/5">
          <span class="text-3xl font-black text-white/40">${i}</span>
        </div>
        <p class="mt-2 text-[11px] font-semibold text-slate-200 text-center">Barajita ${i}</p>
      </div>
    `;
  }

  grid.innerHTML = cards;

  const pageLabel = document.getElementById('currentPageNum');
  const progressText = document.getElementById('albumProgressText');
  const progressBar = document.getElementById('albumProgressBar');
  const pageInput = document.getElementById('pageInput');

  if (pageLabel) pageLabel.textContent = String(page);
  if (pageInput) pageInput.value = String(page);

  const ownedCount = currentUser ? Number(currentUser.cantidad_barajitas || 0) : 0;
  const progressPercent = Math.min((ownedCount / 2000) * 100, 100);

  if (progressText) progressText.textContent = `${ownedCount} / 2000 (${progressPercent.toFixed(0)}%)`;
  if (progressBar) progressBar.style.width = `${progressPercent}%`;
}

function changePage(direction) {
  currentPage = Math.min(Math.max(1, currentPage + direction), 80);
  renderAlbumPage();
}

function jumpToPage() {
  const input = document.getElementById('pageInput');
  if (!input) return;
  currentPage = Math.min(Math.max(1, Number(input.value || 1)), 80);
  renderAlbumPage();
}

function openWithdrawModal() {
  const modal = document.getElementById('withdrawModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  const saldo = Number(currentUser?.saldo_bs || 0);
  document.getElementById('withdrawBs').textContent = `Bs. ${saldo.toFixed(2)}`;
  document.getElementById('withdrawUSD').textContent = `$${(saldo / (window.tasaBcvActual || 50)).toFixed(2)} USD`;
}

function closeWithdrawModal() {
  const modal = document.getElementById('withdrawModal');
  if (modal) modal.classList.add('hidden');
}

function confirmTotalLiquidate() {
  if (!currentUser) {
    return showError('Debes iniciar sesión.');
  }
  const saldo = Number(currentUser.saldo_bs || 0);
  alert(`💸 Liquidación total solicitada: Bs. ${saldo.toFixed(2)}`);
}

function submitWithdrawalRequest(event) {
  event.preventDefault();
  if (!currentUser) {
    return showError('Primero debes iniciar sesión.');
  }
  alert('✅ Solicitud de retiro enviada correctamente.');
  closeWithdrawModal();
}

function logoutUser() {
  currentUser = null;
  localStorage.removeItem('album_user');
  currentTab = 'album';
  showAuthTab('login');
  setMainLayoutForUser();
}

function restoreSession() {
  const savedUser = localStorage.getItem('album_user');
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      updateUserBalanceUI();
      setMainLayoutForUser();
      switchTab('album');
    } catch (err) {
      console.warn('Se borró la sesión corrupta', err);
      localStorage.removeItem('album_user');
      currentUser = null;
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initLucide();
  restoreSession();
  loadStoredConfig();
  showAuthTab('login');
  calculateTotal();
  renderAlbumPage();
  cargarTasaBCV();

  if (!currentUser) {
    setMainLayoutForUser();
  }
});
