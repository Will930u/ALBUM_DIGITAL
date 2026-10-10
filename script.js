// CONFIGURACIÓN DE SUPABASE Y API
const SUPABASE_URL = "https://dxicbitnnesjsqzxisea.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR4aWNiaXRubmVzanNxenhpc2VhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE0MTQzMTMsImV4cCI6MjEwNjk5MDMxM30.0xUXIa0Bby7xpJAF_N3y-n_H3SPwVlUBb9m630AFPtw"; 
const API_URL = "https://album-digital.onrender.com";

let supabaseClient = null;
let currentUser = null;

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  // Inicializar Supabase
  try {
    if (window.supabase && typeof window.supabase.createClient === 'function') {
      supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    }
  } catch (err) {
    console.error("Error al conectar con Supabase en cliente:", err);
  }

  // Verificar sesión activa en localStorage
  const savedUser = localStorage.getItem('album_user');
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser);
      onUserLoggedIn(currentUser);
    } catch (e) {
      console.error("Error al leer sesión:", e);
      localStorage.removeItem('album_user');
    }
  }

  cargarTasaBCV();
});

// 1. GESTIÓN DE AUTENTICACIÓN (LOGIN)
async function handleLogin(event) {
  event.preventDefault();
  
  const usernameInput = document.getElementById('loginUsername');
  const passwordInput = document.getElementById('loginPassword');

  if (!usernameInput || !passwordInput) {
    return alert("⚠️ Error en los campos del formulario de inicio de sesión.");
  }

  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    return alert("⚠️ Por favor ingresa tu usuario y contraseña.");
  }

  try {
    const res = await fetch(`${API_URL}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (res.ok && data.status === "success") {
      currentUser = data.user;
      localStorage.setItem('album_user', JSON.stringify(currentUser));
      alert(`✅ ¡Bienvenido de nuevo, ${currentUser.nombre || currentUser.username}!`);
      onUserLoggedIn(currentUser);
    } else {
      alert(`Error: ${data.message || 'Usuario o contraseña incorrectos.'}`);
    }
  } catch (err) {
    console.error("Error al conectar con el servidor para el login:", err);
    alert("❌ Error de conexión al intentar iniciar sesión con el servidor.");
  }
}

// 2. GESTIÓN DE REGISTRO
async function handleRegister(event) {
  event.preventDefault();
  
  const username = document.getElementById('regUsername').value.trim();
  const password = document.getElementById('regPassword').value.trim();
  const gmail = document.getElementById('regGmail').value.trim();
  const banco = document.getElementById('regBanco').value.trim();
  const cedula = document.getElementById('regCedula').value.trim();
  const telefono = document.getElementById('regTelefono').value.trim();

  if (!all([username, password, gmail, banco, cedula, telefono])) {
    return alert("⚠️ Todos los campos de registro son obligatorios.");
  }

  try {
    const res = await fetch(`${API_URL}/api/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, gmail, banco, cedula, telefono })
    });

    const data = await res.json();

    if (res.ok && data.status === "success") {
      alert("✅ ¡Cuenta creada con éxito! Ya puedes iniciar sesión.");
      document.getElementById('formRegister').reset();
      // Opcional: alternar vista a login
    } else {
      alert(`Error: ${data.message || 'No se pudo completar el registro.'}`);
    }
  } catch (err) {
    console.error("Error en registro:", err);
    alert("❌ Error de conexión con el servidor.");
  }
}

// 3. ESTADO POST-LOGIN (Manejo de UI del Álbum)
function onUserLoggedIn(user) {
  const loginSection = document.getElementById('loginSection');
  const albumSection = document.getElementById('albumSection');

  if (loginSection) loginSection.classList.add('hidden');
  if (albumSection) albumSection.classList.remove('hidden');

  // Actualizar datos del usuario en la interfaz si existen los elementos
  const userNameDisplay = document.getElementById('userNameDisplay');
  if (userNameDisplay) userNameDisplay.innerText = user.nombre || user.username;

  const userBarajitasDisplay = document.getElementById('userBarajitasDisplay');
  if (userBarajitasDisplay) userBarajitasDisplay.innerText = user.cantidad_barajitas || 0;

  const userSaldoDisplay = document.getElementById('userSaldoDisplay');
  if (userSaldoDisplay) userSaldoDisplay.innerText = `Bs. ${parseFloat(user.saldo_bs || 0).toFixed(2)}`;

  cargarBarajitasColeccion();
}

// 4. CONSULTAR TASA BCV
async function cargarTasaBCV() {
  try {
    const res = await fetch(`${API_URL}/api/bcv`);
    const data = await res.json();
    if (res.ok && data.status === "success") {
      window.tasaBcvActual = data.promedio;
      const bcvDisplay = document.getElementById('tasaBcvDisplay');
      if (bcvDisplay) bcvDisplay.innerText = `Tasa BCV: Bs. ${data.promedio}`;
    }
  } catch (e) {
    console.error("Error al obtener tasa BCV:", e);
  }
}

// 5. CARGAR BARAJITAS EN EL ÁLBUM
async function cargarBarajitasColeccion() {
  const container = document.getElementById('albumGridContainer');
  if (!container || !supabaseClient) return;

  try {
    const { data, error } = await supabaseClient.from('barajitas').select('*').order('numero', { ascending: true });
    if (error) throw error;

    if (!data || data.length === 0) {
      container.innerHTML = `<p class="text-slate-400 text-center col-span-full">No hay barajitas registradas aún en el sistema.</p>`;
      return;
    }

    container.innerHTML = data.map(b => `
      <div class="bg-slate-900 border border-purple-500/30 rounded-xl p-3 text-center shadow-lg">
        <span class="text-xs font-mono text-purple-400 font-bold">#${b.numero}</span>
        <div class="my-2 h-32 bg-slate-950 rounded-lg overflow-hidden flex items-center justify-center">
          <img src="${b.imagen_url}" alt="${b.nombre}" class="object-cover h-full w-full" onerror="this.src='https://via.placeholder.com/150/1e1b4b/ffffff?text=Cromo+#${b.numero}'">
        </div>
        <p class="text-sm font-semibold text-white truncate">${b.nombre}</p>
      </div>
    `).join('');
  } catch (err) {
    console.error("Error cargando colección:", err);
    container.innerHTML = `<p class="text-red-400 text-center col-span-full">Error al cargar las barajitas del álbum.</p>`;
  }
}

// 6. NOTIFICAR COMPRA AL BACKEND Y TELEGRAM
async function enviarNotificacionCompra(referencia, barajitasQty, montoBs, montoUsd, bancoEmisor, telefonoEmisor) {
  if (!currentUser) return alert("Debes iniciar sesión para reportar un pago.");

  try {
    const res = await fetch(`${API_URL}/api/notificar-compra`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        usuario_id: currentUser.id,
        barajitas_qty: parseInt(barajitasQty),
        monto_bs: parseFloat(montoBs),
        monto_usd: parseFloat(montoUsd),
        banco_emisor: bancoEmisor,
        telefono_emisor: telefonoEmisor,
        referencia: referencia
      })
    });

    const data = await res.json();
    if (res.ok && data.status === "success") {
      alert("✅ ¡Pago reportado con éxito! Notificación enviada al administrador.");
    } else {
      alert(`Error al reportar: ${data.message || 'Intente nuevamente'}`);
    }
  } catch (err) {
    console.error("Error enviando notificación de compra:", err);
    alert("❌ Error de red al reportar el pago.");
  }
}

// 7. CERRAR SESIÓN
function handleLogout() {
  localStorage.removeItem('album_user');
  currentUser = null;
  window.location.reload();
}
