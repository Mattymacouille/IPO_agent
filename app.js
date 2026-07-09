// CONFIGURATION SUPABASE (À remplacer avec tes accès)
const SUPABASE_URL = "https://pothhxmdapkoctoygtcs.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvdGhoeG1kYXBrb2N0b3lndGNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM1ODk3MzMsImV4cCI6MjA5OTE2NTczM30.m4hn6cFhwT38SUiCW8C8Ft5eNWI8IpBQ0OE8sCtHd28";


// Initialisation du client Supabase
const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Éléments du DOM
const ipoContainer = document.getElementById('ipoContainer');
const totalIposEl = document.getElementById('totalIpos');
const highRiskCountEl = document.getElementById('highRiskCount');

// Fonction pour récupérer et afficher les IPO
async function fetchAndDisplayIPOs() {
    try {
        const { data: ipos, error } = await supabaseClient
            .from('ipo_analyses') // <-- Vérifie bien que c'est le nom exact de ta table
            .select('*')
            .order('analyzed_at', { ascending: false });

        if (error) throw error;

        if (!ipos || ipos.length === 0) {
            ipoContainer.innerHTML = `<div class="text-center py-12 text-slate-500 col-span-full">Aucune IPO analysée en base pour le moment.</div>`;
            return;
        }

        // Mise à jour des compteurs globaux
        totalIposEl.textContent = ipos.length;
        const highRisk = ipos.filter(i => (i.risk_score_short_term >= 9 || i.risk_score_long_term >= 9)).length;
        highRiskCountEl.textContent = highRisk;

        // Vider le loader
        ipoContainer.innerHTML = '';

        // Génération des cartes HTML
        ipos.forEach((ipo, index) => {
            const card = document.createElement('div');
            card.className = "bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-xl hover:border-slate-700 transition-all space-y-4 flex flex-col justify-between";
            
            const getRiskBadgeColor = (score) => {
                if (score >= 8) return 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
                if (score >= 5) return 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
                return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            };

            const dateOption = { year: 'numeric', month: 'short', day: 'numeric' };
            const formattedDate = ipo.ipo_date ? new Date(ipo.ipo_date).toLocaleDateString('fr-FR', dateOption) : 'En attente';

            // Identifiant unique pour le texte de cette carte
            const textId = `report-${index}`;
            const btnId = `btn-${index}`;

            card.innerHTML = `
                <div>
                    <div class="flex justify-between items-start gap-2">
                        <div>
                            <span class="text-xs font-bold text-emerald-400 tracking-wider">${ipo.exchange || 'US MARKET'}</span>
                            <h3 class="text-xl font-bold text-slate-100">${ipo.ticker}</h3>
                            <p class="text-xs text-slate-400 line-clamp-1">${ipo.company_name}</p>
                        </div>
                        <div class="flex gap-3">
                            <div class="flex flex-col gap-1 items-end">
                                <span class="text-[10px] uppercase text-slate-500">Risque CT</span>
                                <span class="px-2 py-0.5 text-xs font-bold rounded-md ${getRiskBadgeColor(ipo.risk_score_short_term)}">
                                    ${ipo.risk_score_short_term ?? '?'}/10
                                </span>
                            </div>
                            <div class="flex flex-col gap-1 items-end">
                                <span class="text-[10px] uppercase text-slate-500">Risque LT</span>
                                <span class="px-2 py-0.5 text-xs font-bold rounded-md ${getRiskBadgeColor(ipo.risk_score_long_term)}">
                                    ${ipo.risk_score_long_term ?? '?'}/10
                                </span>
                            </div>
                        </div>
                    </div>
                    
                    <div id="${textId}" class="mt-4 text-sm text-slate-300 line-clamp-4 whitespace-pre-line border-t border-slate-900 pt-3 transition-all duration-300">
                        ${ipo.ai_report}
                    </div>
                    
                    <button id="${btnId}" class="mt-2 text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors cursor-pointer">
                        Voir le rapport complet ⬇️
                    </button>
                </div>

                <div class="flex justify-between items-center text-xs text-slate-500 pt-3 border-t border-slate-900 mt-auto">
                    <span>📅 IPO : ${formattedDate}</span>
                    ${ipo.sec_filing_url ? `<a href="${ipo.sec_filing_url}" target="_blank" class="text-emerald-400 hover:underline">Source SEC ↗</a>` : ''}
                </div>
            `;
            
            ipoContainer.appendChild(card);

            // Logique de clic pour dérouler / enrouler le texte
            const textElement = card.querySelector(`#${textId}`);
            const btnElement = card.querySelector(`#${btnId}`);

            btnElement.addEventListener('click', () => {
                const isCollapsed = textElement.classList.contains('line-clamp-4');
                if (isCollapsed) {
                    textElement.classList.remove('line-clamp-4');
                    btnElement.innerHTML = 'Réduire le rapport ⬆️';
                } else {
                    textElement.classList.add('line-clamp-4');
                    btnElement.innerHTML = 'Voir le rapport complet ⬇️';
                }
            });
        });

    } catch (err) {
        console.error(err);
        ipoContainer.innerHTML = `<div class="text-center py-12 text-rose-400 col-span-full">❌ Erreur lors de la récupération des données : ${err.message}</div>`;
    }
}

// Lancement au chargement de la page
document.addEventListener('DOMContentLoaded', fetchAndDisplayIPOs);

// --- SERVICE WORKER PWA ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('sw.js')
            .then(reg => console.log('Service Worker enregistré !'))
            .catch(err => console.log('Échec SW :', err));
    });
}