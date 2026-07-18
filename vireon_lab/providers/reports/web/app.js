let currentMode = 'eeg';
let securityActive = false;
let nspActive = false;
let activeAttack = 'none';

let confidenceHistory = Array(100).fill(1.0);
let timeStep = 0;

// Oscilloscope and Chart Canvas references
const oscCanvas = document.getElementById('oscilloscope');
const oscCtx = oscCanvas.getContext('2d');
const chartCanvas = document.getElementById('confidence-chart');
const chartCtx = chartCanvas.getContext('2d');

// Colors matching Tailwind config in index.html
const COLORS = {
    slate900: '#0f172a',
    slate800: '#1e293b',
    slate700: '#334155',
    slate500: '#64748b',
    blue500: '#3b82f6',
    blue400: '#60a5fa',
    emerald500: '#10b981',
    amber500: '#f59e0b',
    rose500: '#f43f5e',
    rose400: '#fb7185'
};

// Resize canvases dynamically
function resizeCanvases() {
    oscCanvas.width = oscCanvas.parentElement.clientWidth;
    oscCanvas.height = oscCanvas.parentElement.clientHeight;
    chartCanvas.width = chartCanvas.parentElement.clientWidth;
    chartCanvas.height = chartCanvas.parentElement.clientHeight;
}
window.addEventListener('resize', resizeCanvases);
resizeCanvases();

// REST API calls
async function postControl(params) {
    try {
        const response = await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        const data = await response.json();
        updateControlButtons(data.context);
        syncSliders(null, data.context); // sync slider contexts immediately
    } catch (e) {
        console.error("Control API write error:", e);
    }
}

function setMode(mode) {
    currentMode = mode;
    postControl({ dbs_mode: mode === 'dbs' });
}

function setHardwareMode(hw_mode) {
    postControl({ hardware_mode: hw_mode });
}

function toggleSecurity() {
    securityActive = !securityActive;
    postControl({ secure_mode: securityActive });
}

function toggleNSP() {
    nspActive = !nspActive;
    postControl({ nsp_mode: nspActive });
}

function injectAttack(attack) {
    activeAttack = attack;
    postControl({ active_attack: attack });
}

async function compileNeuroDSL() {
    const code = document.getElementById('neuro_dsl-code').value;
    try {
        const response = await fetch('/api/neuro_dsl/compile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: code })
        });
        const data = await response.json();
        if (data.status === 'success') {
            console.log('NeuroDSL Code Compiled:', data.bytecode);
            alert('NeuroDSL bytecode execution dispatched! Hex: ' + data.bytecode + '\nMonitoring coherence...');
        } else {
            console.error('NeuroDSL Compile Error:', data.error);
            alert('Compile Error:\n' + data.error);
        }
    } catch (e) {
        console.error('NeuroDSL compilation failed:', e);
    }
}

let paramTimeout = null;
let paramUpdates = {};

function updateParam(name, value) {
    const numericVal = parseFloat(value);
    
    // Update local label readout immediately to avoid lag
    const mapping = {
        'stimulation_amplitude_ma': 'lbl-stim-amp',
        'stimulation_frequency_hz': 'lbl-stim-freq',
        'impedance_kohm': 'lbl-impedance',
        'noise_intensity': 'lbl-noise',
        'attenuation_factor': 'lbl-attenuation',
        'battery_level': 'lbl-battery'
    };
    const labelId = mapping[name];
    if (labelId) {
        const precision = name.includes('freq') || name.includes('battery') ? 0 : (name.includes('attenuation') ? 2 : 1);
        document.getElementById(labelId).textContent = numericVal.toFixed(precision);
    }

    paramUpdates[name] = numericVal;
    if (paramTimeout) {
        clearTimeout(paramTimeout);
    }
    paramTimeout = setTimeout(() => {
        postControl(paramUpdates);
        paramUpdates = {};
    }, 100);
}

function updateControlButtons(context) {
    currentMode = context.dbs_mode ? 'dbs' : 'eeg';
    securityActive = context.secure_mode;
    nspActive = context.nsp_mode;
    activeAttack = context.active_attack;
    
    // Update mode buttons
    const btnEeg = document.getElementById('btn-mode-eeg');
    const btnDbs = document.getElementById('btn-mode-dbs');
    if (!context.dbs_mode) {
        btnEeg.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium bg-slate-800 text-white transition-colors';
        btnDbs.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium text-slate-400 hover:text-white transition-colors';
    } else {
        btnEeg.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium text-slate-400 hover:text-white transition-colors';
        btnDbs.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium bg-slate-800 text-white transition-colors';
    }

    // Update hardware mode buttons
    const hwMode = context.hardware_mode || false;
    const btnSim = document.getElementById('btn-mode-sim');
    const btnHw = document.getElementById('btn-mode-hw');
    if (!hwMode) {
        btnSim.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium bg-slate-800 text-white transition-colors';
        btnHw.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium text-slate-400 hover:text-white transition-colors';
    } else {
        btnSim.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium text-slate-400 hover:text-white transition-colors';
        btnHw.className = 'flex-1 py-1.5 px-3 rounded-md text-xs font-medium bg-slate-800 text-white transition-colors';
    }

    // Update active attack dropdown
    activeAttack = context.active_attack || 'none';
    const dropdown = document.getElementById('attack-dropdown');
    if (dropdown) {
        dropdown.value = activeAttack;
    }

    // 2. Security Shield button styling
    const secureBtn = document.getElementById('btn-secure');
    const secureLbl = document.getElementById('lbl-secure-status');
    if (context.secure_mode) {
        secureBtn.className = 'w-full py-2.5 px-4 rounded-lg font-semibold tracking-wide transition-colors bg-blue-500/10 border border-blue-500 text-blue-400';
        secureLbl.textContent = 'ON';
    } else {
        secureBtn.className = 'w-full py-2.5 px-4 rounded-lg font-semibold tracking-wide transition-colors bg-slate-950 border border-slate-800 text-slate-400 hover:bg-slate-800';
        secureLbl.textContent = 'OFF';
    }

    const nspBtn = document.getElementById('btn-nsp');
    const nspLbl = document.getElementById('lbl-nsp-status');
    if (context.nsp_mode) {
        nspBtn.className = 'w-full mt-2 py-2.5 px-4 rounded-lg font-semibold tracking-wide transition-colors bg-blue-500/10 border border-blue-500 text-blue-400';
        nspLbl.textContent = 'ON';
    } else {
        nspBtn.className = 'w-full mt-2 py-2.5 px-4 rounded-lg font-semibold tracking-wide transition-colors bg-slate-950 border border-slate-800 text-slate-400 hover:bg-slate-800';
        nspLbl.textContent = 'OFF';
    }
}

function syncSliders(state, context) {
    const activeEl = document.activeElement;
    
    const mapping = [];
    if (state) {
        mapping.push({ id: 'slide-stim-amp', lbl: 'lbl-stim-amp', val: state.stimulation_amplitude_ma, precision: 1 });
        mapping.push({ id: 'slide-stim-freq', lbl: 'lbl-stim-freq', val: state.stimulation_frequency_hz, precision: 0 });
        mapping.push({ id: 'slide-battery', lbl: 'lbl-battery', val: state.battery_level, precision: 0 });
    }
    if (context) {
        mapping.push({ id: 'slide-impedance', lbl: 'lbl-impedance', val: context.impedance_kohm, precision: 1 });
        mapping.push({ id: 'slide-noise', lbl: 'lbl-noise', val: context.noise_intensity, precision: 1 });
        mapping.push({ id: 'slide-attenuation', lbl: 'lbl-attenuation', val: context.attenuation_factor, precision: 2 });
    }

    for (const item of mapping) {
        const input = document.getElementById(item.id);
        const label = document.getElementById(item.lbl);
        if (input && label) {
            if (activeEl !== input) {
                input.value = item.val;
                label.textContent = item.val.toFixed(item.precision);
            }
        }
    }
}

// Telemetry & Waveform state
let ws = null;
let signalBuffer = [];

function handleTelemetryState(state) {
    // Update connection tag
    const connTag = document.getElementById('lbl-connection');
    const indicatorTag = document.getElementById('indicator-connection');
    if (state.connected) {
        connTag.className = 'text-xs font-semibold text-emerald-500 tracking-wide';
        connTag.textContent = 'CONNECTED';
        indicatorTag.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
    } else {
        connTag.className = 'text-xs font-semibold text-slate-500 tracking-wide';
        connTag.textContent = 'DISCONNECTED';
        indicatorTag.className = 'w-2 h-2 rounded-full bg-slate-600';
    }

    const nspChip = document.getElementById('lbl-nsp-chip');
    if (state.nsp_active) {
        nspChip.classList.remove('hidden');
    } else {
        nspChip.classList.add('hidden');
    }

    // Update Severity Risk card styles
    const severityCard = document.getElementById('card-severity');
    const severityVal = document.getElementById('val-severity');
    const hazardVal = document.getElementById('val-hazard-state');
    
    let sevCategory = state.iso_severity;
    
    if (state.niss_score !== undefined) {
        severityVal.textContent = sevCategory;
        hazardVal.textContent = `NISS: ${state.niss_score.toFixed(1)} | ${state.hazard_state}`;
    } else {
        severityVal.textContent = sevCategory;
        hazardVal.textContent = state.hazard_state;
    }

    severityCard.className = 'bg-slate-900 p-5 rounded-xl border border-slate-800 border-l-4 shadow-sm transition-colors';
    if (sevCategory === 'CATASTROPHIC' || sevCategory === 'CRITICAL') {
        severityCard.classList.add('border-l-rose-500');
        severityVal.className = 'text-xl font-bold text-rose-500 mb-1';
        if (sevCategory === 'CATASTROPHIC') severityCard.classList.add('animate-pulse');
    } else if (sevCategory === 'MARGINAL') {
        severityCard.classList.add('border-l-amber-500');
        severityVal.className = 'text-xl font-bold text-amber-500 mb-1';
    } else {
        severityCard.classList.add('border-l-emerald-500');
        severityVal.className = 'text-xl font-bold text-emerald-500 mb-1';
    }

    // Temperature Updates
    if (state.temperature_celsius !== undefined) {
        const tempVal = document.getElementById('val-temperature');
        const tempState = document.getElementById('val-temp-state');
        const tempCard = document.getElementById('card-temperature');
        if (tempVal && tempState && tempCard) {
            tempVal.textContent = `${state.temperature_celsius.toFixed(1)} °C`;
            tempCard.className = 'bg-slate-900 p-5 rounded-xl border border-slate-800 border-l-4 shadow-sm transition-colors';
            if (state.temperature_celsius >= 40.0) {
                tempCard.classList.add('border-l-rose-500', 'animate-pulse');
                tempState.textContent = "THERMAL HAZARD";
                tempVal.className = 'text-xl font-bold text-rose-500 mb-1';
            } else if (state.temperature_celsius >= 39.0) {
                tempCard.classList.add('border-l-amber-500');
                tempState.textContent = "ELEVATED";
                tempVal.className = 'text-xl font-bold text-amber-500 mb-1';
            } else {
                tempCard.classList.add('border-l-emerald-500');
                tempState.textContent = "NOMINAL";
                tempVal.className = 'text-xl font-bold text-emerald-500 mb-1';
            }
        }
    }

    // Update Stimulation Card
    const stimCard = document.getElementById('card-stimulation');
    const stimVal = document.getElementById('val-stimulation');
    const stimParams = document.getElementById('val-stimulation-params');
    
    if (state.stimulation_enabled) {
        stimVal.textContent = 'ACTIVE';
        stimVal.className = 'text-xl font-bold text-blue-500 mb-1';
        stimParams.textContent = `${state.stimulation_amplitude_ma.toFixed(1)} mA @ ${state.stimulation_frequency_hz.toFixed(1)} Hz`;
        stimCard.className = 'bg-slate-900 p-5 rounded-xl border border-slate-800 border-l-4 border-l-blue-500 shadow-sm transition-colors';
    } else {
        stimVal.textContent = 'SUSPENDED';
        stimVal.className = 'text-xl font-bold text-slate-500 mb-1';
        stimParams.textContent = '0.0 mA @ 0.0 Hz';
        stimCard.className = 'bg-slate-900 p-5 rounded-xl border border-slate-800 border-l-4 border-l-slate-700 shadow-sm transition-colors';
    }

    // Update Decoder Confidence Card
    const confVal = document.getElementById('val-confidence');
    confVal.textContent = state.decoder_confidence.toFixed(2);
    if (state.decoder_confidence < 0.7) {
        confVal.className = 'text-xl font-bold text-rose-500 mb-1';
    } else if (state.decoder_confidence < 0.9) {
        confVal.className = 'text-xl font-bold text-amber-500 mb-1';
    } else {
        confVal.className = 'text-xl font-bold text-blue-500 mb-1';
    }

    // Update electrode contact impedances
    if (state.electrode_impedances && state.num_channels) {
        const gridContainer = document.getElementById('electrode-grid-container');
        if (gridContainer && gridContainer.children.length !== state.num_channels) {
            // Rebuild the grid
            gridContainer.innerHTML = '';
            for (let ch = 0; ch < state.num_channels; ch++) {
                const elDiv = document.createElement('div');
                elDiv.className = 'bg-slate-950 border border-slate-800 rounded-lg p-3 flex flex-col items-center justify-center gap-1';
                elDiv.id = `el-${ch}`;
                elDiv.innerHTML = `
                    <span class="text-xs text-slate-400 font-medium">Ch ${ch}</span>
                    <span class="font-mono text-emerald-500 text-sm font-semibold el-val">5.0 kΩ</span>
                `;
                gridContainer.appendChild(elDiv);
            }
        }

        for (let ch = 0; ch < state.num_channels; ch++) {
            const el = document.getElementById(`el-${ch}`);
            if (el) {
                const valSpan = el.querySelector('.el-val');
                if (valSpan) {
                    const imp = state.electrode_impedances[ch] !== undefined ? state.electrode_impedances[ch] : 5.0;
                    valSpan.textContent = `${imp.toFixed(1)} kΩ`;
                    valSpan.className = 'font-mono text-sm font-semibold el-val '; 
                    if (imp < 15.0) {
                        valSpan.className += 'text-emerald-500';
                    } else if (imp < 50.0) {
                        valSpan.className += 'text-amber-500';
                    } else {
                        valSpan.className += 'text-rose-500';
                    }
                }
            }
        }
    }

    // Update Diagnostics stats
    document.getElementById('lbl-blocked-attacks').textContent = state.blocked_attacks_count;
    document.getElementById('lbl-blocked-mtu').textContent = state.blocked_mtu_abuses;
    document.getElementById('lbl-tissue-risk').textContent = state.tissue_damage_risk;
    
    const clampBadge = document.getElementById('lbl-clamp-active');
    if (state.clamping_active) {
        clampBadge.textContent = 'ACTIVE';
        clampBadge.className = 'px-2 py-1 rounded bg-rose-500/10 border border-rose-500/30 font-mono text-rose-500 font-medium text-xs';
    } else {
        clampBadge.textContent = 'INACTIVE';
        clampBadge.className = 'px-2 py-1 rounded bg-slate-950 border border-slate-800 font-mono text-slate-400 font-medium text-xs';
    }

    // Sync slider positions from live telemetry values
    syncSliders(state, null);

    // Accumulate confidence history
    confidenceHistory.push(state.decoder_confidence);
    if (confidenceHistory.length > 100) {
        confidenceHistory.shift();
    }

    // Accumulate streamed signal chunk for the oscilloscope visualizer
    if (state.signal_chunk && Array.isArray(state.signal_chunk)) {
        signalBuffer = signalBuffer.concat(state.signal_chunk);
        // Cap buffer to double the width of the oscilloscope to conserve RAM
        const maxSamples = oscCanvas.width * 2;
        if (signalBuffer.length > maxSamples) {
            signalBuffer.splice(0, signalBuffer.length - maxSamples);
        }
    }

    // Update Active Threat Intel
    const threatIntelContainer = document.getElementById('active-threat-intel');
    if (state.threat_intel && state.threat_intel.tara_id) {
        threatIntelContainer.classList.remove('hidden');
        document.getElementById('threat-tier').textContent = `Physics: ${state.threat_intel.physics_tier}`;
        document.getElementById('threat-name').textContent = state.threat_intel.name;
        document.getElementById('threat-desc').textContent = state.threat_intel.description;
        document.getElementById('threat-id').textContent = `TARA: ${state.threat_intel.tara_id}`;
        document.getElementById('threat-niss').textContent = `NISS Score: ${state.threat_intel.niss_score.toFixed(1)}`;
    } else {
        threatIntelContainer.classList.add('hidden');
    }

    // Process security logs
    const logsContainer = document.getElementById('security-logs-container');
    const logCountBadge = document.getElementById('log-count-badge');
    
    if (state.security_logs && state.security_logs.length > 0) {
        logCountBadge.textContent = `${state.security_logs.length} events`;
        logsContainer.innerHTML = '';
        
        state.security_logs.slice().reverse().forEach(log => {
            const entry = document.createElement('div');
            entry.className = 'bg-black/40 border-l-2 p-3 rounded text-xs log-entry-enter';
            
            let colorClass = 'border-amber-500 text-amber-400';
            if (log.severity === 'CRITICAL') {
                colorClass = 'border-rose-500 text-rose-400';
            } else if (log.severity === 'WARNING') {
                colorClass = 'border-amber-500 text-amber-400';
            } else if (log.severity === 'INFO') {
                colorClass = 'border-blue-400 text-blue-400';
            }
            entry.className = `bg-black/40 border-l-2 p-3 rounded text-xs log-entry-enter ${colorClass.split(' ')[0]}`;
            
            let html = `
                <div class="flex justify-between items-start mb-1">
                    <span class="font-bold tracking-wider uppercase ${colorClass.split(' ')[1]}">${log.type}</span>
                    <span class="text-[10px] text-slate-500 font-mono">${log.timestamp.toFixed(3)}s</span>
                </div>
                <div class="text-slate-300 font-mono">${log.details}</div>
            `;
            
            if (log.tara_id || log.brain_region) {
                html += `<div class="mt-2 flex flex-wrap gap-2">`;
                if (log.tara_id) {
                    html += `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400 border border-slate-700">TARA: ${log.tara_id}</span>`;
                }
                if (log.brain_region) {
                    html += `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400 border border-slate-700">Region: ${log.brain_region}</span>`;
                }
                html += `</div>`;
            }
            
            entry.innerHTML = html;
            logsContainer.appendChild(entry);
        });
    } else {
        logCountBadge.textContent = '0 events';
        logsContainer.innerHTML = `
            <div class="text-center text-slate-500 text-sm py-10 italic flex flex-col items-center">
                <svg class="w-8 h-8 opacity-20 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                No anomalies detected. System secure.
            </div>
        `;
    }
}

// WebSocket Connection Handlers
function connectWebSocket() {
    // Establish connection to adjacent port (location.port + 1)
    const wsPort = parseInt(location.port) + 1;
    const wsToken = window.WS_TOKEN || "";
    const wsUrl = `ws://${location.hostname}:${wsPort}/?token=${wsToken}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        const connTag = document.getElementById('lbl-connection');
        const indicatorTag = document.getElementById('indicator-connection');
        connTag.className = 'text-xs font-semibold text-emerald-500 tracking-wide';
        connTag.textContent = 'CONNECTED';
        indicatorTag.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
    };

    ws.onmessage = (event) => {
        try {
            const state = JSON.parse(event.data);
            handleTelemetryState(state);
        } catch (e) {
            console.error("Failed to parse telemetry event message:", e);
        }
    };

    ws.onclose = () => {
        const connTag = document.getElementById('lbl-connection');
        const indicatorTag = document.getElementById('indicator-connection');
        connTag.className = 'text-xs font-semibold text-slate-500 tracking-wide';
        connTag.textContent = 'DISCONNECTED';
        indicatorTag.className = 'w-2 h-2 rounded-full bg-slate-600';
        // Try reconnecting after 2 seconds
        setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (err) => {
        console.error("WebSocket server connection error:", err);
    };
}

// Oscilloscope Generator Waveform loop (Canvas animation)
function animateOscilloscope() {
    requestAnimationFrame(animateOscilloscope);
    
    oscCtx.clearRect(0, 0, oscCanvas.width, oscCanvas.height);
    
    // Draw background horizontal center line
    oscCtx.beginPath();
    oscCtx.strokeStyle = COLORS.slate800;
    oscCtx.lineWidth = 1;
    oscCtx.moveTo(0, oscCanvas.height / 2);
    oscCtx.lineTo(oscCanvas.width, oscCanvas.height / 2);
    oscCtx.stroke();

    oscCtx.beginPath();
    oscCtx.lineWidth = 2.0;
    
    // Select oscilloscope waveform styling based on active attacks
    if (activeAttack === 'suppression') {
        oscCtx.strokeStyle = COLORS.slate500;
        oscCtx.moveTo(0, oscCanvas.height / 2);
        oscCtx.lineTo(oscCanvas.width, oscCanvas.height / 2);
        oscCtx.stroke();
        return; // Flatline
    }
    
    if (activeAttack === 'noise' || activeAttack.startsWith('cpif-')) {
        oscCtx.strokeStyle = COLORS.rose500;
    } else if (activeAttack === 'phase_shift') {
        oscCtx.strokeStyle = COLORS.amber500;
    } else {
        oscCtx.strokeStyle = COLORS.blue400;
    }

    const midY = oscCanvas.height / 2;
    const w = oscCanvas.width;
    
    if (signalBuffer.length > 0) {
        // Draw real-time streamed signal points
        const samplesToShow = Math.min(signalBuffer.length, w);
        const startIndex = signalBuffer.length - samplesToShow;
        
        for (let x = 0; x < samplesToShow; x++) {
            const val = signalBuffer[startIndex + x];
            // Scale raw microvolts visually
            const y = val * 1.5;
            
            if (x === 0) {
                oscCtx.moveTo(x, midY + y);
            } else {
                oscCtx.lineTo(x, midY + y);
            }
        }
    } else {
        // Flatline placeholder if connection is dead/empty
        oscCtx.moveTo(0, midY);
        oscCtx.lineTo(w, midY);
    }
    
    oscCtx.stroke();
}

// Rolling Confidence Line Chart Loop
function animateConfidenceChart() {
    requestAnimationFrame(animateConfidenceChart);
    
    chartCtx.clearRect(0, 0, chartCanvas.width, chartCanvas.height);
    
    const w = chartCanvas.width;
    const h = chartCanvas.height;
    
    // Draw Y safety boundary limit line (0.70 threshold)
    const limitY = h - (0.70 * h);
    chartCtx.beginPath();
    chartCtx.strokeStyle = COLORS.amber500;
    chartCtx.lineWidth = 1.0;
    chartCtx.setLineDash([4, 4]);
    chartCtx.moveTo(0, limitY);
    chartCtx.lineTo(w, limitY);
    chartCtx.stroke();
    chartCtx.setLineDash([]); // Reset
    
    // Draw safety limit text
    chartCtx.fillStyle = COLORS.amber500;
    chartCtx.font = '10px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
    chartCtx.fillText('0.70 Safety Limit', 10, limitY - 5);

    // Draw Rolling confidence line
    chartCtx.beginPath();
    chartCtx.strokeStyle = COLORS.blue500;
    chartCtx.lineWidth = 2.0;
    
    const step = w / 99;
    for (let i = 0; i < confidenceHistory.length; i++) {
        const x = i * step;
        const y = h - (confidenceHistory[i] * h * 0.9 + h * 0.05); // Keep padding
        
        if (i === 0) {
            chartCtx.moveTo(x, y);
        } else {
            chartCtx.lineTo(x, y);
        }
    }
    chartCtx.stroke();
}

// Initial initialization loads the current server-side configurations
async function init() {
    // 1. Fetch CPIF data to populate attack dropdown
    try {
        const cpifRes = await fetch('/api/cpif.json');
        if (cpifRes.ok) {
            const cpifData = await cpifRes.json();
            const techniques = cpifData.threats?.techniques || [];
            const dropdown = document.getElementById('attack-dropdown');
            
            // Group by tactic/category
            const optgroups = {};
            
            techniques.forEach(tech => {
                const cat = tech.category || "Other";
                if (!optgroups[cat]) {
                    const group = document.createElement('optgroup');
                    group.label = `Category: ${cat}`;
                    optgroups[cat] = group;
                    dropdown.appendChild(group);
                }
                const option = document.createElement('option');
                option.value = tech.id.toLowerCase();
                option.textContent = `${tech.id} - ${tech.name}`;
                optgroups[cat].appendChild(option);
            });
        }
    } catch (e) {
        console.error("Failed to fetch CPIF data:", e);
    }

    // 2. Poll context initially to align buttons
    try {
        const res = await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        updateControlButtons(data.context);
        syncSliders(null, data.context); // Sync slider inputs initially
    } catch (e) {
        console.error("Failed to connect to BCI REST API server on launch:", e);
    }

    // Launch WebSockets and animations
    connectWebSocket();
    animateOscilloscope();
    animateConfidenceChart();
}

init();
