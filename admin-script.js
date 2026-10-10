// CONFIGURACIÓN DE SUPABASE
const SUPABASE_URL = "https://ddbdemxrntjqncetyrnr.supabase.co";
const SUPABASE_ANON_KEY = "TU_SUPABASE_ANON_KEY_AQUI"; // Poner tu Anon Key real
const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

let deduccionAcumuladaBs = parseFloat(localStorage.getItem('admin_deduccion_bs') || 0);

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  loadAdminConfig();
});

// NAVEGACIÓN ENTRE PESTAÑAS
function switchTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.admin-tab-btn').forEach(btn => {
    btn.classList.remove('active', 'bg-purple-600', 'text-white');
    btn.classList.add('bg-slate-900', 'text-slate-400');
  });

  document.getElementById(`tab-${tabName}`).classList.remove('hidden');
  const activeBtn = document.getElementById(`tabBtn-${tabName}`);
  activeBtn.classList.add('active', 'bg-purple-600', 'text-white');
  activeBtn.classList.remove('bg-slate-900', 'text-slate-400');

  if (tabName === 'compras') loadAdminCompras();
  if (tabName === 'finanzas') calcularEstadisticasFinancieras();
  if (tabName === 'premios') loadAdminPremios();
}

// 1. CONFIGURACIÓN Y PAGO MÓVIL
function loadAdminConfig() {
  const saved = localStorage.getItem('album_app_config');
  const config = saved ? JSON.parse(saved) : {
    logoUrl: 'https://via.placeholder.com/120/581c87/ffffff?text=ALBUM',
    banco: 'Banesco (0134)',
    cedula: 'V-12345678',
    telefono: '04121234567',
    titular: 'Cuenta Principal'
  };

  document.getElementById('faviconTag').href = config.logoUrl;
  document.getElementById('adminLogoPreview').src = config.logoUrl;

  document.getElementById('adminLogoUrlInput').value = config.logoUrl;
  document.getElementById('adminBancoInput').value = config.banco;
  document.getElementById('adminCedulaInput').value = config.cedula;
  document.getElementById('adminTelefonoInput').value = config.telefono;
  document.getElementById('adminTitularInput').value = config.titular;
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
  alert("✅ Configuración de Pago Móvil y Logo guardada.");
}

// 2. COMPRAS Y VERIFICACIÓN
async function loadAdminCompras() {
  const tbody = document.getElementById('adminComprasTableBody');
  tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">Cargando transacciones...</td></tr>`;

  try {
    const { data, error } = await supabase.from('transacciones').select('*').order('created_at', { ascending: false });
    if (error || !data) throw error;

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
          }">${tx.estado.toUpperCase()}</span>
        </td>
        <td class="p-3 text-center space-x-1">
          ${tx.estado === 'pendiente' ? `
            <button onclick="procesarEstadoCompra('${tx.id}', 'aprobado')" class="bg-emerald-600 text-white px-2 py-1 rounded text-[10px] font-bold">Aprobar</button>
            <button onclick="procesarEstadoCompra('${tx.id}', 'rechazado')" class="bg-red-600 text-white px-2 py-1 rounded text-[10px] font-bold">Rechazar</button>
          ` : '<span class="text-slate-600">-</span>'}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-red-400">Error al consultar Supabase.</td></tr>`;
  }
}

async function procesarEstadoCompra(txId, nuevoEstado) {
  try {
    await supabase.from('transacciones').update({ estado: nuevoEstado }).eq('id', txId);
    loadAdminCompras();
  } catch (e) {
    alert("Error actualizando estado.");
  }
}

// 3. ESTADÍSTICAS FINANCIERAS (GANANCIA DEL 30%)
async function calcularEstadisticasFinancieras() {
  try {
    const { data } = await supabase.from('transacciones').select('monto_bs').eq('estado', 'aprobado');
    const totalVentasBs = (data || []).reduce((acc, curr) => acc + parseFloat(curr.monto_bs || 0), 0);

    const gananciaPlataformaBs = totalVentasBs * 0.30;
    const fondoPremiosBs = totalVentasBs * 0.70;
    const saldoBancoReal = totalVentasBs - deduccionAcumuladaBs;

    document.getElementById('statTotalVentas').innerText = `Bs. ${totalVentasBs.toFixed(2)}`;
    document.getElementById('statFondoPremios').innerText = `Bs. ${fondoPremiosBs.toFixed(2)}`;
    document.getElementById('statGananciaPlataforma').innerText = `Bs. ${gananciaPlataformaBs.toFixed(2)}`;
    document.getElementById('statSaldoBancoReal').innerText = `Bs. ${saldoBancoReal.toFixed(2)}`;
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
  tbody.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-500">Cargando solicitudes...</td></tr>`;

  try {
    const { data } = await supabase.from('retiros_premios').select('*').order('created_at', { ascending: false });
    tbody.innerHTML = (data || []).map(r => `
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
  await supabase.from('retiros_premios').update({ estado: 'aprobado' }).eq('id', id);
  loadAdminPremios();
}

// 5. CARGA MASIVA DE BARAJITAS
async function ejecutarCargaMasivaBarajitas() {
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
    const { error } = await supabase.from('barajitas').upsert(payload);
    if (error) throw error;
    alert(`✅ ¡${payload.length} barajitas guardadas en Supabase!`);
    document.getElementById('adminMasivoInput').value = '';
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}
