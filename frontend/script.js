
const $ = (id) => document.getElementById(id);

let cleanedRows = [];
let priorityRows = [];
let priorityMap = null;
let heatLayer = null;
let markerLayer = null;

const SURAT_CENTER = [21.17, 72.83];
const SURAT_ZOOM = 12;

// =========================
// 1. CSV PARSER
// =========================

function parseCSV(text) {
    const lines = text
        .replace(/^\uFEFF/, "")
        .split(/\r?\n/)
        .filter(line => line.trim());

    if (!lines.length) return [];

    function parseLine(line) {
        const cells = [];
        let current = "";
        let quoted = false;

        for (let i = 0; i < line.length; i++) {
            const ch = line[i];

            if (ch === '"' && line[i + 1] === '"' && quoted) {
                current += '"';
                i++;
            } else if (ch === '"') {
                quoted = !quoted;
            } else if (ch === "," && !quoted) {
                cells.push(current);
                current = "";
            } else {
                current += ch;
            }
        }

        cells.push(current);
        return cells;
    }

    const headers = parseLine(lines[0]).map(h => h.trim());

    return lines.slice(1).map(line => {
        const cells = parseLine(line);

        return Object.fromEntries(
            headers.map((header, index) => [
                header,
                (cells[index] ?? "").trim()
            ])
        );
    });
}

// =========================
// 2. HELPERS
// =========================

function number(row, key) {
    const value = row[key];

    if (value == null || String(value).trim() === "") {
        return null;
    }

    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function display(value) {
    return value == null
        ? "—"
        : value.toLocaleString(undefined, {
            maximumFractionDigits: 2
        });
}

function coordinatesOf(row) {
    const lat = number(row, "latitude_group")
        ?? number(row, "latitude");

    const lon = number(row, "longitude_group")
        ?? number(row, "longitude");

    if (
        lat == null || lon == null ||
        lat < -90 || lat > 90 ||
        lon < -180 || lon > 180
    ) {
        return null;
    }

    return [lat, lon];
}

function priorityColour(priority) {
    const level = String(priority ?? "").trim().toLowerCase();

    if (level === "high") return "#dc2626";
    if (level === "medium") return "#f59e0b";
    if (level === "low") return "#16a34a";

    return "#64748b";
}

// Normalise values to a 0–1 range for heatmap intensity.
function normalise(value, min, max) {
    if (value == null) return 0;

    if (max === min) return 1;

    return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

// =========================
// 3. INITIALISE SURAT MAP
// =========================

function initialiseMap() {
    if (priorityMap) return;

    if (typeof L === "undefined") {
        $("mapStatus").textContent =
            "Leaflet failed to load. Check your internet connection.";
        return;
    }

    priorityMap = L.map("priorityMap").setView(
        SURAT_CENTER,
        SURAT_ZOOM
    );

    
    L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        {
            maxZoom: 19,
            attribution: "Tiles &copy; Esri"
        }
    ).addTo(priorityMap);


    heatLayer = L.heatLayer([], {
        radius: 28,
        blur: 22,
        maxZoom: 16,
        minOpacity: 0.35,
        max: 1
    }).addTo(priorityMap);

    markerLayer = L.layerGroup().addTo(priorityMap);

    $("mapStatus").textContent =
        "Surat map loaded. Upload your intervention priority CSV to display hotspots.";

    $("resetMap").addEventListener("click", () => {
        priorityMap.setView(SURAT_CENTER, SURAT_ZOOM);
    });

    $("mapMode").addEventListener("change", renderHeatmap);

    setTimeout(() => priorityMap.invalidateSize(), 250);
}

// =========================
// 4. RENDER HEATMAP
// =========================

function renderHeatmap() {
    if (!priorityMap || !heatLayer || !markerLayer) return;

    const mode = $("mapMode").value;

    markerLayer.clearLayers();

    const validRows = priorityRows
        .map(row => ({
            row,
            coords: coordinatesOf(row),
            value: mode === "ips"
                ? number(row, "ips")
                : number(row, "average_pm25")
        }))
        .filter(item => item.coords && item.value != null);

    if (!validRows.length) {
        heatLayer.setLatLngs([]);

        $("mapStatus").textContent =
            mode === "ips"
                ? "No valid coordinates and IPS values found in the CSV."
                : "No valid coordinates and average PM2.5 values found in the CSV.";

        return;
    }

    const values = validRows.map(item => item.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);

    const heatPoints = validRows.map(item => {
        const intensity = normalise(item.value, minValue, maxValue);

        // Keep small positive intensity visible while preserving rankings.
        return [
            item.coords[0],
            item.coords[1],
            Math.max(0.08, intensity)
        ];
    });

    heatLayer.setLatLngs(heatPoints);

    // Add clickable circles so users can inspect exact values.
    validRows.forEach(item => {
        const row = item.row;
        const [lat, lon] = item.coords;

        const priority = String(row.priority ?? "Unclassified").trim();

        const circle = L.circleMarker([lat, lon], {
            radius: 5,
            color: priorityColour(priority),
            fillColor: priorityColour(priority),
            fillOpacity: 0.85,
            weight: 1
        });

        const popup = document.createElement("div");

        const title = document.createElement("strong");
        title.textContent = `${priority} Priority`;
        popup.appendChild(title);

        const details = [
            `Latitude: ${display(lat)}`,
            `Longitude: ${display(lon)}`,
            `IPS: ${display(number(row, "ips"))}`,
            `Average PM2.5: ${display(number(row, "average_pm25"))}`,
            `Maximum PM2.5: ${display(number(row, "max_pm25"))}`,
            `Readings: ${display(number(row, "readings"))}`
        ];

        details.forEach(detail => {
            const line = document.createElement("div");
            line.textContent = detail;
            popup.appendChild(line);
        });

        circle.bindPopup(popup);
        circle.addTo(markerLayer);
    });

    $("mapStatus").textContent =
        `Showing ${validRows.length.toLocaleString()} locations across the Surat map. ` +
        (mode === "ips"
            ? "Heat intensity represents relative IPS values."
            : "Heat intensity represents relative average PM2.5 values.") +
        " Click a point for details.";

    setTimeout(() => priorityMap.invalidateSize(), 100);
}

// =========================
// 5. LOAD CLEANED DATA
// =========================

$("dataFile").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;

    try {
        cleanedRows = parseCSV(await file.text());

        const pmValues = cleanedRows
            .map(row => number(row, "PM2.5"))
            .filter(value => value != null);

        const uniqueLocations = new Set(
            cleanedRows
                .filter(row =>
                    number(row, "latitude") != null &&
                    number(row, "longitude") != null
                )
                .map(row =>
                    `${Number(row.latitude).toFixed(4)},${Number(row.longitude).toFixed(4)}`
                )
        );

        const average = pmValues.length
            ? pmValues.reduce((sum, value) => sum + value, 0) /
              pmValues.length
            : null;

        const peak = pmValues.length
            ? Math.max(...pmValues)
            : null;

        $("average").textContent = display(average);
        $("peak").textContent = display(peak);
        $("locations").textContent =
            uniqueLocations.size.toLocaleString();

        $("status").textContent =
            `Loaded ${cleanedRows.length.toLocaleString()} rows from ${file.name}.`;
    } catch (error) {
        console.error(error);

        $("status").textContent =
            "Could not read the cleaned CSV. Please check the file format.";
    }
});

// =========================
// 6. LOAD PRIORITY DATA
// =========================

$("priorityFile").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;

    try {
        priorityRows = parseCSV(await file.text());

        const body = $("priorityRows");
        body.replaceChildren();

        const highCount = priorityRows.filter(row =>
            String(row.priority ?? "").trim().toLowerCase() === "high"
        ).length;

        $("highPriority").textContent = highCount.toLocaleString();

        priorityRows
            .slice()
            .sort((a, b) =>
                (number(b, "ips") ?? -Infinity) -
                (number(a, "ips") ?? -Infinity)
            )
            .slice(0, 100)
            .forEach(row => {
                const tr = document.createElement("tr");

                const values = [
                    row.latitude_group ?? row.latitude,
                    row.longitude_group ?? row.longitude,
                    display(number(row, "average_pm25")),
                    display(number(row, "readings")),
                    display(number(row, "ips"))
                ];

                values.forEach(value => {
                    const td = document.createElement("td");
                    td.textContent = value ?? "—";
                    tr.appendChild(td);
                });

                const td = document.createElement("td");
                const badge = document.createElement("span");

                const priority = String(row.priority ?? "").trim();
                const validLevel = ["High", "Medium", "Low"].find(
                    level => level.toLowerCase() === priority.toLowerCase()
                );

                badge.className = `priority ${validLevel ?? ""}`;
                badge.textContent = priority || "Unclassified";

                td.appendChild(badge);
                tr.appendChild(td);
                body.appendChild(tr);
            });

        if (!priorityRows.length) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");

            td.colSpan = 6;
            td.textContent = "No priority records found.";

            tr.appendChild(td);
            body.appendChild(tr);
        }

        renderHeatmap();

        $("status").textContent =
            `Loaded ${priorityRows.length.toLocaleString()} priority records from ${file.name}.`;
    } catch (error) {
        console.error(error);

        $("status").textContent =
            "Could not read the priority CSV. Please check the file format.";
    }
});

// =========================
// 7. START DASHBOARD
// =========================

initialiseMap();
