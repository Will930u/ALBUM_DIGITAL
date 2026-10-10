// CONFIGURACIÓN DE SUPABASE
const SUPABASE_URL = "https://dxicbitnnesjsqzxisea.supabase.co";
// Reemplaza esta cadena con tu anon key de Supabase (Project Settings -> API -> anon public key)
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR4aWNiaXRubmVzanNxenhpc2VhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE0MTQzMTMsImV4cCI6MjEwNjk5MDMxM30.0xUXIa0Bby7xpJAF_N3y-n_H3SPwVlUBb9m630AFPtw"; 

let supabaseClient = null;
let deduccionAcumuladaBs = parseFloat(localStorage.getItem('admin_deduccion_bs') || 0);

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  
  // Inicialización segura del cliente Supabase
  try {
    if (window.supabase && typeof window.supabase.createClient === 'function') {
      supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    }
  } catch (err) {
    console.error("Error al conectar con Supabase:", err);
  }

  loadAdminConfig();
});

// NAVEGACIÓN ENTRE PESTAÑAS
function switchTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.admin-tab-btn').forEach(btn => {
    btn.classList.remove('active', 'bg-purple-600', 'text-white');
    btn.classList.add('bg-slate-900', 'text-slate-400');
  });

  const targetTab = document.getElementById(`tab-${tabName}`);
  if (targetTab) {
    targetTab.classList.remove('hidden');
  }

  const activeBtn = document.getElementById(`tabBtn-${tabName}`);
  if (activeBtn) {
    activeBtn.classList.add('active', 'bg-purple-600', 'text-white');
    activeBtn.classList.remove('bg-slate-900', 'text-slate-400');
  }

  if (tabName === 'compras') loadAdminCompras();
  if (tabName === 'finanzas') calcularEstadisticasFinancieras();
  if (tabName === 'premios') loadAdminPremios();
}

// 1. CONFIGURACIÓN Y PAGO MÓVIL
function loadAdminConfig() {
  const saved = localStorage.getItem('album_app_config');
  const config = saved ? JSON.parse(saved) : {
    logoUrl: 'https://via.placeholder.com/120/581c87/ffffff?text=ALBUM',
    banco: '0134',
    cedula: '21101658',
    telefono: '+584129830982',
    titular: 'ÁLBUM DIGITAL'
  };

  const favicon = document.getElementById('faviconTag');
  if (favicon && config.logoUrl) favicon.href = config.logoUrl;

  const preview = document.getElementById('adminLogoPreview');
  if (preview && config.logoUrl) preview.src = config.logoUrl;

  if (document.getElementById('adminLogoUrlInput')) document.getElementById('adminLogoUrlInput').value = config.logoUrl || '';
  if (document.getElementById('adminBancoInput')) document.getElementById('adminBancoInput').value = config.banco || '';
  if (document.getElementById('adminCedulaInput')) document.getElementById('adminCedulaInput').value = config.cedula || '';
  if (document.getElementById('adminTelefonoInput')) document.getElementById('adminTelefonoInput').value = config.telefono || '';
  if (document.getElementById('adminTitularInput')) document.getElementById('adminTitularInput').value = config.titular || '';
}

function saveAdminConfig() {
  const config = {
    logoUrl: document.getElementById('adminLogoUrlInput').value.trim(),
    banco: document.getElementById('adminBancoInput').value.trim(),
    cedula: document.getElementById('adminCedulaInput').value.trim(),
    telefono: document.getElementById('adminTelefonoInput').value.trim(),
    titular: document.getElementById('adminTitularInput').value.trim()
  };

  localStorage.setItem('album_app_config', JSON.stringify(config));
  loadAdminConfig();
  alert("✅ Configuración de Pago Móvil y Logo guardada con éxito.");
}

// 2. COMPRAS Y VERIFICACIÓN
async function loadAdminCompras() {
  const tbody = document.getElementById('adminComprasTableBody');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">Cargando transacciones...</td></tr>`;

  if (!supabaseClient) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-amber-400">Verifica la API key de Supabase en admin-script.js.</td></tr>`;
    return;
  }

  try {
    const { data, error } = await supabaseClient.from('transacciones').select('*').order('created_at', { ascending: false });
    if (error || !data) throw error;

    if (data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">No hay compras registradas.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.map(tx => `
      <tr class="hover:bg-slate-950/50">
        <td class="p-3 font-mono text-purple-400 font-bold">${tx.usuario_id}</td>
        <td class="p-3 font-mono">${tx.referencia}</td>
        <td class="p-3">${tx.barajitas_qty}</td>
        <td class="p-3 font-bold text-white">Bs. ${parseFloat(tx.monto_bs).toFixed(2)} <span class="text-[10px] text-slate-400">($${tx.monto_usd})</span></td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${
            tx.estado === 'aprobado' ? 'bg-emerald-500/20 text-emerald-400' :
            tx.estado === 'rechazado' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
          }">${tx.estado ? tx.estado.toUpperCase() : 'PENDIENTE'}</span>
        </td>
        <td class="p-3 text-center space-x-1">
          ${tx.estado === 'pendiente' ? `
            <button onclick="procesarEstadoCompra('${tx.referencia}', '${tx.usuario_id}', ${tx.barajitas_qty}, ${tx.monto_bs}, 'aprobado')" class="bg-emerald-600 text-white px-2 py-1 rounded text-[10px] font-bold">Aprobar</button>
            <button onclick="procesarEstadoCompra('${tx.referencia}', '${tx.usuario_id}', 0, 0, 'rechazado')" class="bg-red-600 text-white px-2 py-1 rounded text-[10px] font-bold">Rechazar</button>
          ` : '<span class="text-slate-600">-</span>'}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-red-400">Error al consultar Supabase.</td></tr>`;
  }
}

const API_URL = "https://album-digital.onrender.com";

async function procesarEstadoCompra(referencia, usuarioId, barajitasQty, montoBs, nuevoEstado) {
  try {
    const res = await fetch(`${API_URL}/api/admin/procesar-compra`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        referencia: referencia,
        usuario_id: usuarioId,
        barajitas_qty: barajitasQty,
        monto_bs: montoBs,
        estado: nuevoEstado
      })
    });

    const data = await res.json();
    if (res.ok && data.status === "success") {
      alert(`✅ Compra marcada como ${nuevoEstado.toUpperCase()} con éxito.`);
      loadAdminCompras();
    } else {
      alert(`Error: ${data.message || 'No se pudo actualizar'}`);
    }
  } catch (err) {
    console.error("Error al procesar la compra desde admin:", err);
    alert("Ocurrió un error al conectar con el servidor.");
  }
}

// 3. ESTADÍSTICAS FINANCIERAS (30% GANANCIA)
async function calcularEstadisticasFinancieras() {
  if (!supabaseClient) return;
  try {
    const { data } = await supabaseClient.from('transacciones').select('monto_bs').eq('estado', 'aprobado');
    const totalVentasBs = (data || []).reduce((acc, curr) => acc + parseFloat(curr.monto_bs || 0), 0);

    const gananciaPlataformaBs = totalVentasBs * 0.30;
    const fondoPremiosBs = totalVentasBs * 0.70;
    const saldoBancoReal = totalVentasBs - deduccionAcumuladaBs;

    if (document.getElementById('statTotalVentas')) document.getElementById('statTotalVentas').innerText = `Bs. ${totalVentasBs.toFixed(2)}`;
    if (document.getElementById('statFondoPremios')) document.getElementById('statFondoPremios').innerText = `Bs. ${fondoPremiosBs.toFixed(2)}`;
    if (document.getElementById('statGananciaPlataforma')) document.getElementById('statGananciaPlataforma').innerText = `Bs. ${gananciaPlataformaBs.toFixed(2)}`;
    if (document.getElementById('statSaldoBancoReal')) document.getElementById('statSaldoBancoReal').innerText = `Bs. ${saldoBancoReal.toFixed(2)}`;
  } catch (e) {
    console.error("Error calculando estadísticas:", e);
  }
}

function aplicarDeduccionBancaria() {
  const monto = parseFloat(document.getElementById('adminDeduccionInput').value || 0);
  if (monto <= 0) return alert("Ingresa un monto válido");
  deduccionAcumuladaBs += monto;
  localStorage.setItem('admin_deduccion_bs', deduccionAcumuladaBs);
  document.getElementById('adminDeduccionInput').value = '';
  document.getElementById('adminDeduccionNota').value = '';
  calcularEstadisticasFinancieras();
  alert(`Deducción aplicada. Total deducido: Bs. ${deduccionAcumuladaBs.toFixed(2)}`);
}

// 4. SOLICITUDES DE PREMIOS
async function loadAdminPremios() {
  const tbody = document.getElementById('adminPremiosTableBody');
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-500">Cargando solicitudes...</td></tr>`;

  if (!supabaseClient) return;

  try {
    const { data } = await supabaseClient.from('retiros_premios').select('*').order('created_at', { ascending: false });
    if (!data || data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-500">No hay solicitudes de premios.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.map(r => `
      <tr class="hover:bg-slate-950/50">
        <td class="p-3 font-mono">${r.id}</td>
        <td class="p-3 font-bold text-white">${r.usuario_id}</td>
        <td class="p-3">Hito #${r.milestone}</td>
        <td class="p-3 font-bold text-amber-400">$${r.monto_usd} USD (Bs. ${r.monto_bs})</td>
        <td class="p-3">${r.datos_pago}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${r.estado === 'aprobado' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}">${r.estado}</span></td>
        <td class="p-3 text-center">
          ${r.estado === 'pendiente' ? `<button onclick="marcarPremioPagado('${r.id}')" class="bg-emerald-600 text-white px-2 py-1 rounded text-[10px] font-bold">Marcar Pagado</button>` : '-'}
        </td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-red-400">Error al consultar retiros.</td></tr>`;
  }
}

async function marcarPremioPagado(id) {
  if (!supabaseClient) return;
  await supabaseClient.from('retiros_premios').update({ estado: 'aprobado' }).eq('id', id);
  loadAdminPremios();
}

// 5. CARGA MASIVA DE BARAJITAS
async function ejecutarCargaMasivaBarajitas() {
  if (!supabaseClient) return alert("Cliente de Supabase no conectado.");
  const rawText = document.getElementById('adminMasivoInput').value.trim();
  if (!rawText) return alert("Ingresa datos válidos.");

  const lines = rawText.split('\n');
  const payload = lines.map(line => {
    const parts = line.split('|');
    return {
      numero: parseInt(parts[0]),
      nombre: parts[1],
      imagen_url: parts[2]
    };
  }).filter(item => item.numero && item.nombre && item.imagen_url);

  try {
    const { error } = await supabaseClient.from('barajitas').upsert(payload);
    if (error) throw error;
    alert(`✅ ¡${payload.length} barajitas guardadas en Supabase!`);
    document.getElementById('adminMasivoInput').value = '';
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}
