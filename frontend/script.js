
const $ = (id) => document.getElementById(id);

let cleanedRows = [];
let priorityRows = [];
let priorityMap = null;
let markerLayer = null;



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

function getCoordinates(row) {
    const latitude = number(row, "latitude_group")
        ?? number(row, "latitude");

    const longitude = number(row, "longitude_group")
        ?? number(row, "longitude");

    if (
        latitude == null ||
        longitude == null ||
        latitude < -90 ||
        latitude > 90 ||
        longitude < -180 ||
        longitude > 180
    ) {
        return null;
    }

    return [latitude, longitude];
}

function getPriorityColour(priority) {
    const level = String(priority ?? "").trim().toLowerCase();

    if (level === "high") return "#dc2626";
    if (level === "medium") return "#f59e0b";
    if (level === "low") return "#16a34a";

    return "#64748b";
}


function initialiseMap() {
    const mapElement = $("priorityMap");

    if (!mapElement) {
        console.error("Could not find the priorityMap element.");
        return;
    }

    if (typeof L === "undefined") {
        $("mapStatus").textContent =
            "Leaflet could not load. Check your internet connection.";
        return;
    }

    if (priorityMap) return;

    priorityMap = L.map("priorityMap").setView([20.5937, 78.9629], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(priorityMap);

    markerLayer = L.layerGroup().addTo(priorityMap);

    $("mapStatus").textContent =
        "Map ready. Upload your intervention priority CSV to plot locations.";

    // Helps Leaflet calculate the correct size after rendering.
    setTimeout(() => {
        priorityMap.invalidateSize();
    }, 200);
}


function displayPriorityMap(rows) {
    if (!priorityMap || !markerLayer) {
        initialiseMap();
    }

    if (!priorityMap || !markerLayer) return;

    markerLayer.clearLayers();

    const bounds = [];
    let plotted = 0;
    let skipped = 0;

    rows.forEach(row => {
        const coordinates = getCoordinates(row);

        if (!coordinates) {
            skipped++;
            return;
        }

        const [latitude, longitude] = coordinates;
        const priority = String(row.priority ?? "Unclassified").trim();
        const colour = getPriorityColour(priority);

        const circle = L.circleMarker([latitude, longitude], {
            radius: priority.toLowerCase() === "high" ? 10 : 7,
            color: colour,
            fillColor: colour,
            fillOpacity: 0.75,
            weight: 2
        });

        const popup = document.createElement("div");

        const heading = document.createElement("strong");
        heading.textContent = `${priority} Priority`;
        popup.appendChild(heading);

        const details = [
            `Latitude: ${display(latitude)}`,
            `Longitude: ${display(longitude)}`,
            `Average PM2.5: ${display(number(row, "average_pm25"))}`,
            `Maximum PM2.5: ${display(number(row, "max_pm25"))}`,
            `Readings: ${display(number(row, "readings"))}`,
            `Intervention Priority Score: ${display(number(row, "ips"))}`
        ];

        details.forEach(detail => {
            const line = document.createElement("div");
            line.textContent = detail;
            popup.appendChild(line);
        });

        circle.bindPopup(popup);
        circle.addTo(markerLayer);

        bounds.push(coordinates);
        plotted++;
    });

    if (bounds.length === 1) {
        priorityMap.setView(bounds[0], 13);
    } else if (bounds.length > 1) {
        priorityMap.fitBounds(bounds, {
            padding: [30, 30],
            maxZoom: 13
        });
    }

    $("mapStatus").textContent = plotted
        ? `Showing ${plotted} priority locations on the map.${skipped ? ` Skipped ${skipped} rows with invalid or missing coordinates.` : ""} Click a marker for details.`
        : "No valid coordinates found. Check the latitude_group and longitude_group columns in your priority CSV.";

    setTimeout(() => priorityMap.invalidateSize(), 100);
}


$("dataFile").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;

    try {
        cleanedRows = parseCSV(await file.text());

        const pmValues = cleanedRows
            .map(row => number(row, "PM2.5"))
            .filter(value => value != null);

        const coordinates = new Set(
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
            ? pmValues.reduce((sum, value) => sum + value, 0) / pmValues.length
            : null;

        const peak = pmValues.length
            ? Math.max(...pmValues)
            : null;

        $("average").textContent = display(average);
        $("peak").textContent = display(peak);
        $("locations").textContent = coordinates.size.toLocaleString();

        $("status").textContent =
            `Loaded ${cleanedRows.length.toLocaleString()} rows from ${file.name}.`;
    } catch (error) {
        console.error(error);
        $("status").textContent =
            "Could not read the cleaned CSV. Check that it is a valid CSV file.";
    }
});



$("priorityFile").addEventListener("change", async event => {
    const file = event.target.files[0];
    if (!file) return;

    try {
        priorityRows = parseCSV(await file.text());

        const body = $("priorityRows");
        body.replaceChildren();

        let high = 0;

        priorityRows.slice(0, 100).forEach(row => {
            const priority = String(row.priority ?? "").trim();

            if (priority.toLowerCase() === "high") {
                high++;
            }

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

            const priorityCell = document.createElement("td");
            const badge = document.createElement("span");

            const validPriority = ["High", "Medium", "Low"].find(
                level => level.toLowerCase() === priority.toLowerCase()
            );

            badge.className = `priority ${validPriority ?? ""}`;
            badge.textContent = priority || "Unclassified";

            priorityCell.appendChild(badge);
            tr.appendChild(priorityCell);
            body.appendChild(tr);
        });

        if (!priorityRows.length) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");

            td.colSpan = 6;
            td.textContent = "No priority rows found.";

            tr.appendChild(td);
            body.appendChild(tr);
        }

        $("highPriority").textContent = high.toLocaleString();

        // Update the map using the same priority CSV.
        displayPriorityMap(priorityRows);

        $("status").textContent =
            `Loaded ${priorityRows.length.toLocaleString()} priority rows from ${file.name}.`;
    } catch (error) {
        console.error(error);
        $("status").textContent =
            "Could not read the priority CSV. Check the file format.";
    }
});



document.addEventListener("DOMContentLoaded", initialiseMap);
