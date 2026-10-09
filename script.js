// Configuración de Servidor Backend en Render
const API_URL = "https://album-digital.onrender.com";

const STATE = {
  currentPage: 1,
  totalPages: 80,
  stickersPerPage: 25,
  totalStickers: 2000,
  bcvRate: 0,
  user: null,
  userStickersCount: 0,
  userBalanceBs: 0,
  claimedMilestones: [],
  selectedMilestone: null,
  isProcessingWithdrawal: false,
  logoClicks: 0
};

document.addEventListener('DOMContentLoaded', async () => {
  lucide.createIcons();
  setupLogoClickCounter();
  await fetchBcvRate();
  checkSession();
});

async function fetchBcvRate() {
  try {
    const res = await fetch(`${API_URL}/api/bcv`);
    const data = await res.json();
    STATE.bcvRate = data.promedio || 0;
    document.getElementById('bcvRateDisplay').innerText = `Bs. ${STATE.bcvRate.toFixed(2)}`;
    calculateTotal();
  } catch (e) {
    document.getElementById('bcvRateDisplay').innerText = 'Bs. --.--';
  }
}

function checkSession() {
  const savedUser = localStorage.getItem('album_user');
  if (savedUser) {
    STATE.user = JSON.parse(savedUser);
    showAppMain();
  }
}

function showAuthTab(tab) {
  document.getElementById('loginForm').classList.add('hidden');
  document.getElementById('registerForm').classList.add('hidden');
  document.getElementById('forgotForm').classList.add('hidden');

  if (tab === 'login') {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('authTitle').innerText = 'INICIAR SESIÓN';
  } else if (tab === 'register') {
    document.getElementById('registerForm').classList.remove('hidden');
    document.getElementById('authTitle').innerText = 'REGISTRO DE USUARIO';
  } else if (tab === 'forgot') {
    document.getElementById('forgotForm').classList.remove('hidden');
    document.getElementById('authTitle').innerText = 'RECUPERAR CLAVE';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const payload = {
    username: document.getElementById('regUsername').value,
    password: document.getElementById('regPassword').value,
    gmail: document.getElementById('regGmail').value,
    banco: document.getElementById('regBanco').value,
    cedula: document.getElementById('regCedula').value,
    telefono: document.getElementById('regTelefono').value
  };

  try {
    const res = await fetch(`${API_URL}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert('¡Registro exitoso! Iniciando sesión...');
      STATE.user = data.user;
      localStorage.setItem('album_user', JSON.stringify(data.user));
      showAppMain();
    } else {
      alert(data.message || 'Error en el registro');
    }
  } catch (err) {
    alert('Error de conexión con el servidor');
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const payload = {
    username: document.getElementById('loginUsername').value,
    password: document.getElementById('loginPassword').value
  };

  try {
    const res = await fetch(`${API_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      STATE.user = data.user;
      localStorage.setItem('album_user', JSON.stringify(data.user));
      showAppMain();
    } else {
      alert(data.message || 'Usuario o contraseña incorrectos');
    }
  } catch (err) {
    alert('Error conectando al servidor');
  }
}

function handleForgotPassword(e) {
  e.preventDefault();
  alert('Se ha enviado la solicitud de recuperación a tu correo Gmail registrado.');
  showAuthTab('login');
}

function logoutUser() {
  localStorage.removeItem('album_user');
  STATE.user = null;
  location.reload();
}

function showAppMain() {
  document.getElementById('authSection').classList.add('hidden');
  document.getElementById('mainHeader').classList.remove('hidden');
  switchTab('album');
  loadUserData();
}

function switchTab(tab) {
  document.getElementById('albumSection').classList.add('hidden');
  document.getElementById('tiendaSection').classList.add('hidden');
  document.getElementById('adminSection').classList.add('hidden');

  if (tab === 'album') {
    document.getElementById('albumSection').classList.remove('hidden');
    renderAlbumPage();
  } else if (tab === 'tienda') {
    document.getElementById('tiendaSection').classList.remove('hidden');
  }
}

function loadUserData() {
  if (!STATE.user) return;
  STATE.userStickersCount = STATE.user.cantidad_barajitas || 0;
  STATE.userBalanceBs = STATE.user.saldo_bs || 0;
  updateUIHeader();
}

function updateUIHeader() {
  const balanceUSD = STATE.bcvRate > 0 ? (STATE.userBalanceBs / STATE.bcvRate).toFixed(2) : '0.00';
  document.getElementById('userBalanceBs').innerText = `Bs. ${STATE.userBalanceBs.toFixed(2)} ($${balanceUSD})`;
  const progressPct = ((STATE.userStickersCount / STATE.totalStickers) * 100).toFixed(1);
  document.getElementById('albumProgressText').innerText = `${STATE.userStickersCount} / ${STATE.totalStickers} (${progressPct}%)`;
  document.getElementById('albumProgressBar').style.width = `${progressPct}%`;
}

function renderAlbumPage() {
  const grid = document.getElementById('stickersGrid');
  grid.innerHTML = '';
  const startIndex = (STATE.currentPage - 1) * STATE.stickersPerPage + 1;
  const endIndex = startIndex + STATE.stickersPerPage - 1;

  for (let i = startIndex; i <= endIndex; i++) {
    const isUnlocked = i <= STATE.userStickersCount;
    const isMilestone = (i % 500 === 0);

    const slot = document.createElement('div');
    slot.className = `metal-slot aspect-[3/4] rounded-xl flex flex-col items-center justify-center p-2 relative ${isUnlocked ? 'filled' : ''} ${isMilestone ? 'milestone-slot' : ''}`;

    if (isUnlocked) {
      slot.innerHTML = `
        <img src="https://via.placeholder.com/150/581c87/ffffff?text=Cromo+${i}" class="w-full h-full object-cover rounded-lg">
        <span class="absolute bottom-1 right-1 bg-black/80 px-1 rounded text-[10px] font-bold text-purple-300">#${i}</span>
      `;
    } else {
      slot.innerHTML = `
        <i data-lucide="${isMilestone ? 'award' : 'lock'}" class="w-6 h-6 ${isMilestone ? 'text-amber-400' : 'text-purple-500/40'}"></i>
        <span class="text-xs font-bold text-slate-500">#${i}</span>
      `;
    }
    grid.appendChild(slot);
  }
  lucide.createIcons();
}

function changePage(delta) {
  const newPage = STATE.currentPage + delta;
  if (newPage >= 1 && newPage <= STATE.totalPages) {
    STATE.currentPage = newPage;
    document.getElementById('currentPageNum').innerText = STATE.currentPage;
    renderAlbumPage();
  }
}

function calculateTotal() {
  const qty = parseInt(document.getElementById('stickerQty').value) || 0;
  const totalUSD = qty * 0.62;
  const totalBs = totalUSD * STATE.bcvRate;
  document.getElementById('totalUSDDisplay').innerText = `$${totalUSD.toFixed(2)}`;
  document.getElementById('totalBsDisplay').innerText = `Bs. ${totalBs.toFixed(2)}`;
}

async function submitPurchase(e) {
  e.preventDefault();
  const qty = parseInt(document.getElementById('stickerQty').value);
  const ref = document.getElementById('refInput').value;
  const totalBs = (qty * 0.62) * STATE.bcvRate;
  const totalUSD = qty * 0.62;

  const btn = document.getElementById('btnSubmitPurchase');
  btn.disabled = true;
  btn.innerText = 'PROCESANDO PAGO...';

  try {
    const res = await fetch(`${API_URL}/api/notificar-compra`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usuario_id: STATE.user.id,
        barajitas_qty: qty,
        monto_bs: totalBs,
        monto_usd: totalUSD,
        referencia: ref
      })
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert('¡Pago reportado! Notificación con botones enviada a Telegram.');
      document.getElementById('refInput').value = '';
      switchTab('album');
    } else {
      alert('Error registrando el pago');
    }
  } catch (err) {
    alert('Error al conectar con el servidor');
  } finally {
    btn.disabled = false;
    btn.innerText = 'REPORTAR PAGO Y SOLICITAR BARAJITAS';
  }
}

function openWithdrawModal() {
  document.getElementById('withdrawModal').classList.remove('hidden');
}

function closeWithdrawModal() {
  document.getElementById('withdrawModal').classList.add('hidden');
}

async function submitWithdrawalRequest(e) {
  e.preventDefault();
  const usdVal = "200.00";
  const bsVal = (200 * STATE.bcvRate).toFixed(2);

  try {
    const res = await fetch(`${API_URL}/api/notificar-retiro`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        usuario_id: STATE.user.id,
        tipo: 'hito_parcial',
        milestone: 500,
        monto_bs: bsVal,
        monto_usd: usdVal,
        datos_pago: `${STATE.user.banco} | ${STATE.user.telefono} | ${STATE.user.cedula}`
      })
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert('Solicitud enviada a Telegram para verificación.');
      closeWithdrawModal();
    }
  } catch (err) {
    alert('Error enviando la solicitud');
  }
}

function setupLogoClickCounter() {
  const logo = document.getElementById('introLogo');
  if (!logo) return;
  logo.addEventListener('click', () => {
    STATE.logoClicks++;
    if (STATE.logoClicks >= 20) {
      STATE.logoClicks = 0;
      document.getElementById('adminSection').classList.remove('hidden');
      document.getElementById('albumSection').classList.add('hidden');
    }
  });
}

function exitAdmin() {
  switchTab('album');
}
