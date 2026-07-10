// CONFIGURATION SUPABASE (À remplacer avec tes accès)
const SUPABASE_URL = "https://pothhxmdapkoctoygtcs.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvdGhoeG1kYXBrb2N0b3lndGNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM1ODk3MzMsImV4cCI6MjA5OTE2NTczM30.m4hn6cFhwT38SUiCW8C8Ft5eNWI8IpBQ0OE8sCtHd28";


const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Variables globales pour le filtrage
let allIpos = [];
let currentFilter = 'All';

// Éléments du DOM
const ipoContainer = document.getElementById('ipoContainer');
const totalIposEl = document.getElementById('totalIpos');
const highRiskCountEl = document.getElementById('highRiskCount');

// Boutons d'onglets
const tabs = {
    'All': document.getElementById('tab-all'),
    'À venir': document.getElementById('tab-avenir'),
    'En cours de listing': document.getElementById('tab-cours'),
    'Récemment listée': document.getElementById('tab-liste')
};

// Fonction pour filtrer visuellement les onglets
function updateTabStyles(activeFilter) {
    Object.keys(tabs).forEach(filter => {
        if (!tabs[filter]) return;
        if (filter === activeFilter) {
            tabs[filter].className = "px-4 py-2 text-sm font-semibold rounded-lg bg-emerald-500 text-slate-950 shadow-lg cursor-pointer transition-all";
        } else {
            tabs[filter].className = "px-4 py-2 text-sm font-semibold rounded-lg bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800 cursor-pointer transition-all";
        }
    });
}

// Rendu des cartes sur l'écran
function renderIPOs() {
    // Filtrer les données selon l'onglet actif
    const filteredIpos = currentFilter === 'All' 
        ? allIpos 
        : allIpos.filter(ipo => ipo.status === currentFilter);

    if (filteredIpos.length === 0) {
        ipoContainer.innerHTML = `<div class="text-center py-12 text-slate-500 col-span-full">Aucune IPO dans cette catégorie pour le moment.</div>`;
        return;
    }

    ipoContainer.innerHTML = '';

    filteredIpos.forEach((ipo, index) => {
        const card = document.createElement('div');
        card.className = "bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-xl hover:border-slate-700 transition-all space-y-4 flex flex-col justify-between";
        
        // Couleur des scores de risque
        const getRiskBadgeColor = (score) => {
            if (score >= 8) return 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
            if (score >= 5) return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
            return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        };

        // Badge de statut stylisé
        const getStatusBadge = (status) => {
            if (status === 'À venir') return '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">📋 À VENIR</span>';
            if (status === 'En cours de listing') return '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">⏳ EN LISTING</span>';
            return '<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">✅ COTÉE</span>';
        };

        const dateOption = { year: 'numeric', month: 'short', day: 'numeric' };
        const formattedDate = ipo.ipo_date ? new Date(ipo.ipo_date).toLocaleDateString('fr-FR', dateOption) : 'En attente';

        const textId = `report-${index}`;
        const btnId = `btn-${index}`;

        card.innerHTML = `
            <div>
                <div class="flex justify-between items-start gap-2">
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-xs font-bold text-slate-400 tracking-wider">${ipo.market || 'US MARKET'}</span>
                            <span class="text-xs text-slate-500">•</span>
                            <span class="text-xs text-slate-400 font-medium">${ipo.country || 'USA'}</span>
                        </div>
                        <h3 class="text-xl font-bold text-slate-100 flex items-center gap-2">
                            ${ipo.ticker}
                            ${getStatusBadge(ipo.status)}
                        </h3>
                        <p class="text-xs text-slate-400 line-clamp-1 mt-0.5">${ipo.company_name}</p>
                    </div>
                    <div class="flex gap-2">
                        <div class="flex flex-col gap-0.5 items-end">
                            <span class="text-[9px] uppercase text-slate-500 font-bold">Risque CT</span>
                            <span class="px-2 py-0.5 text-xs font-bold rounded-md ${getRiskBadgeColor(ipo.risk_score_short_term)}">
                                ${ipo.risk_score_short_term ?? '?'}/10
                            </span>
                        </div>
                        <div class="flex flex-col gap-0.5 items-end">
                            <span class="text-[9px] uppercase text-slate-500 font-bold">Risque LT</span>
                            <span class="px-2 py-0.5 text-xs font-bold rounded-md ${getRiskBadgeColor(ipo.risk_score_long_term)}">
                                ${ipo.risk_score_long_term ?? '?'}/10
                            </span>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-3 gap-2 bg-slate-900/50 border border-slate-900 rounded-lg p-2.5 mt-3 text-center">
                    <div>
                        <div class="text-[10px] text-slate-500 uppercase font-bold">Prix Offre</div>
                        <div class="text-xs font-semibold text-slate-200 mt-0.5">${ipo.price_range || '-'}</div>
                    </div>
                    <div>
                        <div class="text-[10px] text-slate-500 uppercase font-bold">Levée max</div>
                        <div class="text-xs font-semibold text-emerald-400 mt-0.5">${ipo.amount_raised || '-'}</div>
                    </div>
                    <div>
                        <div class="text-[10px] text-slate-500 uppercase font-bold">Valorisation</div>
                        <div class="text-xs font-semibold text-blue-400 mt-0.5">${ipo.valuation || '-'}</div>
                    </div>
                </div>
                
                <div id="${textId}" class="mt-4 text-sm text-slate-300 line-clamp-4 whitespace-pre-line border-t border-slate-900 pt-3 transition-all">
                    ${ipo.ai_report}
                </div>
                
                <button id="${btnId}" class="mt-2 text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 cursor-pointer">
                    Voir le rapport complet ⬇️
                </button>
            </div>

            <div class="flex justify-between items-center text-xs text-slate-500 pt-3 border-t border-slate-900 mt-4">
                <span>📅 Date : ${formattedDate}</span>
                ${ipo.sec_filing_url ? `<a href="${ipo.sec_filing_url}" target="_blank" class="text-emerald-400 hover:underline">Prospectus ↗</a>` : ''}
            </div>
        `;
        
        ipoContainer.appendChild(card);

        // Gestion de l'ouverture du texte
        const textElement = card.querySelector(`#${textId}`);
        const btnElement = card.querySelector(`#${btnId}`);

        btnElement.addEventListener('click', () => {
            if (textElement.classList.contains('line-clamp-4')) {
                textElement.classList.remove('line-clamp-4');
                btnElement.innerHTML = 'Réduire le rapport ⬆️';
            } else {
                textElement.classList.add('line-clamp-4');
                btnElement.innerHTML = 'Voir le rapport complet ⬇️';
            }
        });
    });
}

// Récupération des données depuis Supabase
async function fetchAndDisplayIPOs() {
    try {
        const { data: ipos, error } = await supabaseClient
            .from('ipos')
            .select('*')
            .order('analyzed_at', { ascending: false });

        if (error) throw error;

        allIpos = ipos || [];

        // Mise à jour des compteurs globaux du Header
        totalIposEl.textContent = allIpos.length;
        const highRisk = allIpos.filter(i => (i.risk_score_short_term >= 9 || i.risk_score_long_term >= 9)).length;
        highRiskCountEl.textContent = highRisk;

        // Mettre à jour les labels des onglets avec les vrais comptes
        if(tabs['All']) tabs['All'].textContent = `🌍 Toutes (${allIpos.length})`;
        if(tabs['À venir']) tabs['À venir'].textContent = `📋 À venir (${allIpos.filter(i => i.status === 'À venir').length})`;
        if(tabs['En cours de listing']) tabs['En cours de listing'].textContent = `⏳ En listing (${allIpos.filter(i => i.status === 'En cours de listing').length})`;
        if(tabs['Récemment listée']) tabs['Récemment listée'].textContent = `✅ Cotées (${allIpos.filter(i => i.status === 'Récemment listée').length})`;

        renderIPOs();

    } catch (err) {
        console.error(err);
        ipoContainer.innerHTML = `<div class="text-center py-12 text-rose-400 col-span-full">❌ Erreur de chargement : ${err.message}</div>`;
    }
}

// Écouteurs d'événements sur les onglets de filtrage
Object.keys(tabs).forEach(filter => {
    if (!tabs[filter]) return;
    tabs[filter].addEventListener('click', () => {
        currentFilter = filter;
        updateTabStyles(filter);
        renderIPOs();
    });
});

// Lancement global au chargement
document.addEventListener('DOMContentLoaded', fetchAndDisplayIPOs);

// --- SERVICE WORKER PWA ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('sw.js').catch(err => console.log('Erreur SW:', err));
    });
}

// --- BANNIÈRE D'INSTALLATION PWA ---
let deferredPrompt;
const installBtn = document.getElementById('installBtn');

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (installBtn) installBtn.classList.remove('hidden');
});

if (installBtn) {
    installBtn.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') installBtn.classList.add('hidden');
            deferredPrompt = null;
        }
    });
}