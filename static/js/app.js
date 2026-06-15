// 1. Clock Initialization
function updateClock() {
    const now = new Date();
    document.getElementById('live-clock').innerText = now.toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// 2. Map Initialization (Leaflet)
const map = L.map('fleet-map').setView([32.92, -97.04], 12); // Centered on DFW

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
}).addTo(map);

// Custom Icons for Vans
const vanIcon = L.divIcon({
    className: 'custom-div-icon',
    html: `<div style='background-color:#3b82f6; width:15px; height:15px; border-radius:50%; border:2px solid white; box-shadow: 0 0 10px #3b82f6;'></div>`,
    iconSize: [15, 15],
    iconAnchor: [7, 7]
});

const markers = {
    "van_01": L.marker([0, 0], {icon: vanIcon}).addTo(map).bindPopup("<b>Van 01 (Sheraton)</b>"),
    "van_02": L.marker([0, 0], {icon: vanIcon}).addTo(map).bindPopup("<b>Van 02 (Gaylord)</b>"),
    "van_03": L.marker([0, 0], {icon: vanIcon}).addTo(map).bindPopup("<b>Van 03 (Hyatt)</b>")
};

// Auto-scroll to telemetry card when map marker is clicked
Object.keys(markers).forEach(vid => {
    markers[vid].on('click', () => {
        const card = document.getElementById(`card-${vid}`);
        if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Add a temporary highlight effect
            card.style.transition = 'box-shadow 0.3s, transform 0.3s';
            card.style.boxShadow = '0 0 20px #3b82f6';
            card.style.transform = 'scale(1.02)';
            card.style.zIndex = '10';
            
            setTimeout(() => {
                card.style.boxShadow = '';
                card.style.transform = '';
                card.style.zIndex = '';
            }, 1500);
        }
    });
});

// 3. WebSocket Connection
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    // Update Telemetry & Markers
    for (const [vid, state] of Object.entries(data.telemetry)) {
        // Update Cards
        const card = document.getElementById(`card-${vid}`);
        if (card) {
            document.getElementById(`speed-${vid}`).innerText = Math.round(state.speed);
            document.getElementById(`rpm-${vid}`).innerText = Math.round(state.rpm);
            document.getElementById(`temp-${vid}`).innerText = state.temp.toFixed(1);
            document.getElementById(`fuel-${vid}`).innerText = state.fuel.toFixed(1);
            
            const statusEl = document.getElementById(`status-${vid}`);
            statusEl.innerText = state.status;
            if (state.speed === 0) {
                statusEl.style.background = 'rgba(239, 68, 68, 0.2)'; // Red for Idle
                statusEl.style.color = '#ef4444';
            } else {
                statusEl.style.background = 'rgba(16, 185, 129, 0.2)'; // Green for Moving
                statusEl.style.color = '#10b981';
            }
        }
        
        // Update Markers
        if (markers[vid] && state.lat && state.lng) {
            markers[vid].setLatLng([state.lat, state.lng]);
        }
    }
    
    // Process Alerts
    if (data.alerts && data.alerts.length > 0) {
        const container = document.getElementById('alerts-container');
        const noAlerts = container.querySelector('.no-alerts');
        if (noAlerts) noAlerts.remove();
        
        data.alerts.forEach(msg => {
            const div = document.createElement('div');
            div.className = 'alert-item';
            div.innerText = msg;
            container.prepend(div); // Add to top
            
            // Optional: Keep only last 10 alerts
            if (container.children.length > 10) {
                container.lastElementChild.remove();
            }
        });
        
        const activeCount = container.children.length;
        document.getElementById('active-alerts-title').innerText = `Active Alerts (${activeCount})`;
    }
};

// 4. AI Terminal Logic
let savedPrompts = [];
let promptIndex = -1;

// Fetch saved prompts
fetch('/api/prompts')
    .then(res => res.json())
    .then(data => {
        savedPrompts = data.prompts;
    })
    .catch(err => console.error("Could not load prompts:", err));

const chatInput = document.getElementById('chat-input');
const chatOutput = document.getElementById('chat-output');

function appendChat(role, message) {
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    
    let prefix = '';
    if (role === 'user') prefix = '> ';
    if (role === 'ai') prefix = '🤖 [AI]: ';
    
    div.innerText = prefix + message;
    chatOutput.appendChild(div);
    chatOutput.scrollTop = chatOutput.scrollHeight;
}

chatInput.addEventListener('keydown', async (e) => {
    // Handle Shift+Tab cycling
    if (e.key === 'Tab' && e.shiftKey) {
        e.preventDefault();
        if (savedPrompts.length > 0) {
            promptIndex = (promptIndex + 1) % savedPrompts.length;
            chatInput.value = savedPrompts[promptIndex];
        }
        return;
    }
    
    // Handle Submission
    if (e.key === 'Enter' && chatInput.value.trim() !== '') {
        const query = chatInput.value.trim();
        chatInput.value = '';
        
        appendChat('user', query);
        appendChat('system', 'Thinking...');
        
        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: query })
            });
            const data = await res.json();
            
            // Remove the 'Thinking...' message
            chatOutput.lastElementChild.remove();
            
            appendChat('ai', data.reply);
        } catch (err) {
            chatOutput.lastElementChild.remove();
            appendChat('system', '❌ Error connecting to AI backend.');
        }
    }
});

// 5. Rules Management Modal
const rulesModal = document.getElementById('rules-modal');
const manageRulesBtn = document.getElementById('manage-rules-btn');
const closeModalBtn = document.getElementById('close-modal-btn');
const rulesTbody = document.getElementById('rules-tbody');

manageRulesBtn.addEventListener('click', () => {
    fetchRules();
    rulesModal.showModal();
});

closeModalBtn.addEventListener('click', () => {
    rulesModal.close();
});

async function fetchRules() {
    try {
        const res = await fetch('/api/rules');
        const data = await res.json();
        rulesTbody.innerHTML = '';
        
        data.rules.forEach(r => {
            const tr = document.createElement('tr');
            const checkedAttr = r.enabled ? 'checked' : '';
            tr.innerHTML = `
                <td>${r.vehicle_id}</td>
                <td>${r.metric}</td>
                <td>${r.operator}</td>
                <td><input type="number" step="0.1" id="thresh-${r.id}" value="${r.threshold}" onchange="updateRule(${r.id})"></td>
                <td><input type="text" class="msg-input" id="msg-${r.id}" value="${r.message}" onchange="updateRule(${r.id})"></td>
                <td>
                    <label class="switch">
                      <input type="checkbox" id="enable-${r.id}" ${checkedAttr} onchange="updateRule(${r.id})">
                      <span class="slider"></span>
                    </label>
                    <button class="action-btn delete" onclick="deleteRule(${r.id})">Delete</button>
                </td>
            `;
            rulesTbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Failed to fetch rules", err);
    }
}

async function updateRule(id) {
    const thresh = parseFloat(document.getElementById(`thresh-${id}`).value);
    const msg = document.getElementById(`msg-${id}`).value;
    const enabled = document.getElementById(`enable-${id}`).checked;
    
    try {
        await fetch(`/api/rules/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ threshold: thresh, message: msg, enabled: enabled })
        });
        // visually indicate save but no alert popup needed for auto-save
    } catch (err) {
        console.error('Error updating rule', err);
    }
}

async function deleteRule(id) {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    try {
        await fetch(`/api/rules/${id}`, { method: 'DELETE' });
        fetchRules(); // Refresh list
    } catch (err) {
        alert('Error deleting rule.');
    }
}
