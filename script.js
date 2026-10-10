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
  logoClicks: 0,
  supabase: null
};

document.addEventListener('DOMContentLoaded', async () => {
  lucide.createIcons();
  setupLogoClickCounter();
  initSupabase();
  await fetchBcvRate();
  checkSession();
  cargarDatosPagoMovilTienda(); // <--- CARGA LOS DATOS DEL ADMIN EN LA TIENDA

  if (STATE.supabase) {
    STATE.supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY') {
        console.log("Modo recuperación de contraseña detectado");
        showAuthTab('reset');
      }
    });
  }
});

// FUNCIÓN PARA CARGAR DATOS DE PAGO MÓVIL EN LA TIENDA
function cargarDatosPagoMovilTienda() {
  const saved = localStorage.getItem('album_app_config');
  const config = saved ? JSON.parse(saved) : {
    banco: '0134',
    cedula: '21101658',
    telefono: '+584129830982',
    titular: 'ÁLBUM DIGITAL'
  };

  if (document.getElementById('displayBanco')) document.getElementById('displayBanco').innerText = config.banco;
  if (document.getElementById('displayCedula')) document.getElementById('displayCedula').innerText = config.cedula;
  if (document.getElementById('displayTelefono')) document.getElementById('displayTelefono').innerText = config.telefono;
  if (document.getElementById('displayTitular')) document.getElementById('displayTitular').innerText = config.titular;
}

// Inicialización de Supabase con ventana y seguridad
function initSupabase() {
  const SUPABASE_URL = "https://dxicbitnnesjsqzxisea.supabase.co";
  const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR4aWNiaXRubmVzanNxenhpc2VhIivaG9sZSI6ImFub24iLCJpYXQiOjE3OTE0MTQzMTMsImV4cCI6MjEwNjk5MDMxM30.0xUXIa0Bby7xpJAF_N3y-n_H3SPwVlUBb9m630AFPtw";

  if (window.supabase && SUPABASE_URL && SUPABASE_ANON_KEY) {
    try {
      STATE.supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      console.log("Supabase inicializado correctamente.");
    } catch (e) {
      console.error("Error al inicializar Supabase:", e);
    }
  } else {
    console.error("La librería de Supabase no se cargó correctamente desde el CDN.");
  }
}

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
  const resetForm = document.getElementById('resetPasswordForm');
  if (resetForm) resetForm.classList.add('hidden');

  if (tab === 'login') {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('authTitle').innerText = 'INICIAR SESIÓN';
  } else if (tab === 'register') {
    document.getElementById('registerForm').classList.remove('hidden');
    document.getElementById('authTitle').innerText = 'REGISTRO DE USUARIO';
  } else if (tab === 'forgot') {
    document.getElementById('forgotForm').classList.remove('hidden');
    document.getElementById('authTitle').innerText = 'RECUPERAR CLAVE';
  } else if (tab === 'reset') {
    if (resetForm) resetForm.classList.remove('hidden');
    document.getElementById('authTitle').innerText = 'NUEVA CONTRASEÑA';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.innerText = "REGISTRANDO...";

  const payload = {
    username: document.getElementById('regUsername').value.trim(),
    password: document.getElementById('regPassword').value,
    gmail: document.getElementById('regGmail').value.trim(),
    banco: document.getElementById('regBanco').value.trim(),
    cedula: document.getElementById('regCedula').value.trim(),
    telefono: document.getElementById('regTelefono').value.trim()
  };

  try {
    const res = await fetch(`${API_URL}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      alert('¡Registro exitoso! Iniciando sesión...');
      STATE.user = data.user;
      localStorage.setItem('album_user', JSON.stringify(data.user));
      showAppMain();
    } else {
      alert(data.message || 'Error en el registro');
    }
  } catch (err) {
    alert('Error de conexión con el servidor en Render');
  } finally {
    btn.disabled = false;
    btn.innerText = "CREAR CUENTA Y CONTINUAR";
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.innerText = "VERIFICANDO...";

  const payload = {
    username: document.getElementById('loginUsername').value.trim(),
    password: document.getElementById('loginPassword').value
  };

  try {
    const res = await fetch(`${API_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      STATE.user = data.user;
      localStorage.setItem('album_user', JSON.stringify(data.user));
      showAppMain();
    } else {
      alert(data.message || 'Usuario o contraseña incorrectos');
    }
  } catch (err) {
    alert('Error conectando al servidor');
  } finally {
    btn.disabled = false;
    btn.innerText = "INGRESAR AL ÁLBUM";
  }
}

async function handleForgotPassword(e) {
  e.preventDefault();
  const emailInput = document.getElementById('forgotInput').value.trim();
  const btn = e.target.querySelector('button[type="submit"]');

  if (!emailInput) {
    alert("Por favor ingresa tu correo Gmail registrado.");
    return;
  }

  if (!STATE.supabase) initSupabase();

  btn.disabled = true;
  btn.innerText = "ENVIANDO CORREO...";

  try {
    const { data, error } = await STATE.supabase.auth.resetPasswordForEmail(emailInput, {
      redirectTo: 'https://will930u.github.io/ALBUM_DIGITAL/'
    });

    if (error) {
      alert(`Error al enviar correo: ${error.message}`);
    } else {
      alert(`✅ Se ha enviado un enlace de recuperación a ${emailInput}. Revisa tu bandeja.`);
      showAuthTab('login');
    }
  } catch (err) {
    alert("Ocurrió un error inesperado al conectar con Supabase.");
  } finally {
    btn.disabled = false;
    btn.innerText = "ENVIAR ENLACE DE RECUPERACIÓN";
  }
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

// ----------------------------------------------------
// FUNCIÓN ACTUALIZADA CON BANCO, TELÉFONO Y REFERENCIA
// ----------------------------------------------------
async function submitPurchase(e) {
  e.preventDefault();
  const qty = parseInt(document.getElementById('stickerQty').value);
  const bancoEmisor = document.getElementById('tiendaBancoEmisor').value.trim();
  const telefonoEmisor = document.getElementById('tiendaTelefonoEmisor').value.trim();
  const ref = document.getElementById('refInput').value.trim();
  
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
        banco_emisor: bancoEmisor,
        telefono_emisor: telefonoEmisor,
        referencia: ref
      })
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      alert('¡Pago reportado con éxito! El administrador verificará la transferencia.');
      document.getElementById('refInput').value = '';
      document.getElementById('tiendaBancoEmisor').value = '';
      document.getElementById('tiendaTelefonoEmisor').value = '';
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
    if (res.ok && data.status === 'success') {
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

async function handleResetPassword(e) {
  e.preventDefault();
  const newPassword = document.getElementById('newPasswordInput').value.trim();
  const btn = e.target.querySelector('button[type="submit"]');

  if (!newPassword || newPassword.length < 6) {
    alert("La contraseña debe tener al menos 6 caracteres.");
    return;
  }

  btn.disabled = true;
  btn.innerText = "GUARDANDO...";

  try {
    const { data, error } = await STATE.supabase.auth.updateUser({
      password: newPassword
    });

    if (error) {
      alert(`Error al actualizar clave en Supabase: ${error.message}`);
      return;
    }

    const userEmail = data.user ? data.user.email : null;

    if (userEmail) {
      await fetch(`${API_URL}/api/update-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gmail: userEmail,
          new_password: newPassword
        })
      });
    }

    alert("✅ ¡Contraseña actualizada con éxito! Ya puedes iniciar sesión con tu nueva clave.");
    showAuthTab('login');
  } catch (err) {
    alert("Ocurrió un error inesperado al actualizar la contraseña.");
  } finally {
    btn.disabled = false;
    btn.innerText = "ACTUALIZAR CONTRASEÑA";
  }
}
