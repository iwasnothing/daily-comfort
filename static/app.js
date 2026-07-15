/**
 * Daily Comfort — SSE client
 *
 * Connects to /api/stream and populates the result table
 * as each workflow node finishes.
 */

const steps = [
    { key: "news",      label: "📰 今日新聞",     rows: 1 },
    { key: "feeling",   label: "💭 感受",          rows: 2 },
    { key: "comfort",   label: "✝️ 牧者安慰",     rows: 3 },
    { key: "animation", label: "🎨 動畫",         rows: 4 },
];

let es = null;

function setStatus(text) {
    document.getElementById("status-bar").innerHTML = text;
}

function setButtonEnabled(enabled) {
    document.getElementById("run-btn").disabled = !enabled;
}

function startStream() {
    const tableBody = document.getElementById("table-body");
    const table = document.getElementById("result-table");
    // Clear any previous animation iframe
    const animContainer = document.getElementById("animation-container");
    if (animContainer) animContainer.innerHTML = "";

    tableBody.innerHTML = "";
    table.style.display = "none";
    setButtonEnabled(false);

    // Close any previous connection
    if (es) es.close();

    es = new EventSource("/api/stream");

    // Mark the currently-processing row as active
    function activateRow(index) {
        table.style.display = "table";
        let rows = tableBody.querySelectorAll("tr");
        rows.forEach(r => r.classList.remove("active"));
        if (rows[index]) rows[index].classList.add("active");
    }

    // Insert or update a row
    function upsertRow(index, content, isHtml = false) {
        let rows = tableBody.querySelectorAll("tr");
        let row = rows[index];
        const step = steps[index];
        const label = step ? (step.label || `步驟 ${index + 1}`) : `步驟 ${index + 1}`;
        if (!row) {
            row = document.createElement("tr");
            const labelCell = document.createElement("td");
            labelCell.textContent = label;
            const contentCell = document.createElement("td");
            row.appendChild(labelCell);
            row.appendChild(contentCell);
            tableBody.appendChild(row);
        }
        // News row contains HTML (clickable titles); other rows get escaped text.
        row.querySelector("td:last-child").innerHTML =
            isHtml ? content : escapeHtml(content);
    }

    // Safely extract string content from SSE event data
    function extractContent(data) {
        if (typeof data === "string") return data;
        if (data && typeof data.content === "string" && data.content.length > 0) return data.content;
        return "(無內容)";
    }

    // Register dedicated handlers for each SSE event type.
    // The MessageEvent object does NOT have an `event` property, so
    // `es.onmessage` with `event.event` never matches custom types.
    // We use `es.addEventListener(name, handler)` instead.

    es.addEventListener("news", (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[SSE] Received event: news | data:", data);
            setStatus('<span class="spinner"></span> 正在获取新聞...');
            upsertRow(0, extractContent(data), true);
        } catch (e) {
            console.error("[SSE] Parse error for news:", e, event.data);
        }
    });

    es.addEventListener("feeling", (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[SSE] Received event: feeling | data:", data);
            activateRow(1);
            setStatus('<span class="spinner"></span> 正在生成感受...');
            upsertRow(1, extractContent(data));
        } catch (e) {
            console.error("[SSE] Parse error for feeling:", e, event.data);
        }
    });

    es.addEventListener("comfort", (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[SSE] Received event: comfort | data:", data);
            activateRow(2);
            setStatus('<span class="spinner"></span> 正在生成牧者安慰...');
            upsertRow(2, extractContent(data));
        } catch (e) {
            console.error("[SSE] Parse error for comfort:", e, event.data);
        }
    });

    es.addEventListener("animation", (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[SSE] Received event: animation | data:", data);
            activateRow(3);
            setStatus('<span class="spinner"></span> 正在生成動畫...');

            if (data.url) {
                // Show the animation URL as a clickable link in the table row
                const linkHtml = '<a href="' + data.url + '" target="_blank" class="animation-link">' + data.url + '</a>';
                upsertRow(3, linkHtml, true);
                // Render the animation as an iframe below the table
                showAnimationIframe(data.url);
            } else {
                upsertRow(3, extractContent(data));
            }
        } catch (e) {
            console.error("[SSE] Parse error for animation:", e, event.data);
        }
    });

    es.addEventListener("done", (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[SSE] Received event: done | data:", data);
            setStatus("✅ 完成");
            setButtonEnabled(true);
            es.close();
        } catch (e) {
            console.error("[SSE] Parse error for done:", e, event.data);
            setStatus("✅ 完成");
            setButtonEnabled(true);
            es.close();
        }
    });

    es.addEventListener("error", (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("[SSE] Received event: error | data:", data);
            setStatus(
                '<span style="color:#ff6b6b">⚠️ [' +
                    (data.node || "error") +
                    "] " +
                    (data.message || "未知錯誤") +
                    "</span>"
            );
            setButtonEnabled(true);
            es.close();
        } catch (e) {
            console.error("[SSE] Parse error for error event:", e, event.data);
            setStatus('<span style="color:#ff6b6b">⚠️ 未知錯誤</span>');
            setButtonEnabled(true);
            es.close();
        }
    });

    es.addEventListener("close", (event) => {
        console.log("[SSE] Received event: close");
        // Backend explicitly closed the connection — stop reconnection.
        es.close();
    });

    // Log when the SSE connection opens
    es.addEventListener("open", (event) => {
        console.log("[SSE] Connection opened");
        setStatus('<span class="spinner"></span> 正在获取新聞...');
    });

    // Global error handler for connection-level failures
    es.onerror = (err) => {
        try {
            if (es.readyState === EventSource.CLOSED) {
                // Connection closed normally (workflow done or intentional close).
                console.log("[SSE] Connection closed normally");
                return;
            }
            console.error("[SSE] Connection error:", err);
            setStatus('<span style="color:#ff6b6b">⚠️ 連接錯誤，請重試</span>');
            setButtonEnabled(true);
            es.close();
        } catch (e) {
            console.error("[SSE] Error handler error:", e);
        }
    };
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, "<br>");
}

/**
 * Render the generated animation HTML as an iframe below the result table.
 */
function showAnimationIframe(url) {
    let container = document.getElementById("animation-container");
    if (!container) return;

    container.innerHTML = `
        <div class="animation-header">🎨 動畫預覽</div>
        <iframe
            src="${url}"
            class="animation-iframe"
            sandbox="allow-scripts allow-same-origin"
            frameborder="0"
            scrolling="no"
        ></iframe>
    `;
    container.style.display = "block";
    console.log("[SSE] Animation iframe shown for:", url);
}
