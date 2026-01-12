const eventSelect = document.getElementById("event-select");
const reservationForm = document.getElementById("reservation-form");
const reservationResult = document.getElementById("reservation-result");
const listButton = document.getElementById("list-button");
const reservationsTable = document.getElementById("reservations-table");
const statusPanel = document.getElementById("status-panel");
const enableChaosButton = document.getElementById("enable-chaos");
const disableChaosButton = document.getElementById("disable-chaos");

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  return { response, data };
}

function showMessage(element, message, type) {
  element.textContent = message;
  element.className = `message ${type}`;
}

function clearMessage(element) {
  element.textContent = "";
  element.className = "message";
}

function renderReservations(reservations) {
  if (!reservations.length) {
    reservationsTable.innerHTML = "<p>No reservations yet.</p>";
    return;
  }

  const rows = reservations
    .map(
      (row) => `
        <tr>
          <td>${row.id}</td>
          <td>${row.user_name}</td>
          <td>${row.user_email}</td>
          <td>${row.event_name}</td>
          <td>${new Date(row.created_at).toLocaleString()}</td>
        </tr>
      `,
    )
    .join("");

  reservationsTable.innerHTML = `
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Name</th>
          <th>Email</th>
          <th>Event</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
  `;
}

function renderStatus(status) {
  statusPanel.innerHTML = `
    <div><strong>Chaos Enabled:</strong> ${status.chaos_enabled}</div>
    <div><strong>Active Store:</strong> ${status.active_store}</div>
    <div><strong>Last Error:</strong> ${status.last_error || "None"}</div>
  `;
}

async function loadEvents() {
  const { data } = await fetchJson("/api/events");
  const events = data.data.events;
  eventSelect.innerHTML = events
    .map((event) => `<option value="${event}">${event}</option>`)
    .join("");
}

async function refreshStatus() {
  const { data } = await fetchJson("/api/status");
  renderStatus(data.data);
}

reservationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage(reservationResult);

  const payload = {
    name: document.getElementById("name-input").value.trim(),
    email: document.getElementById("email-input").value.trim(),
    event: eventSelect.value,
  };

  const { response, data } = await fetchJson("/api/reservations", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (!response.ok || !data.ok) {
    showMessage(
      reservationResult,
      `Error: ${data.error.message} (${data.error.code})`,
      "error",
    );
    return;
  }

  const storedIn = data.data.reservation.stored_in;
  const message = `Reserved! ID #${data.data.reservation.id} (stored in ${storedIn}).`;
  showMessage(reservationResult, message, "success");
  reservationForm.reset();
  await refreshStatus();
});

listButton.addEventListener("click", async () => {
  const { response, data } = await fetchJson("/api/reservations");
  if (!response.ok || !data.ok) {
    reservationsTable.innerHTML = `<p>Error: ${data.error.message}</p>`;
    return;
  }

  renderReservations(data.data.reservations);
  await refreshStatus();
});

enableChaosButton.addEventListener("click", async () => {
  await fetchJson("/admin/chaos/enable", { method: "POST" });
  await refreshStatus();
});

disableChaosButton.addEventListener("click", async () => {
  await fetchJson("/admin/chaos/disable", { method: "POST" });
  await refreshStatus();
});

(async () => {
  await loadEvents();
  await refreshStatus();
})();
