const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const uploadProgress = document.getElementById("upload-progress");
const progressFill = document.getElementById("progress-fill");
const progressText = document.getElementById("progress-text");
const fileList = document.getElementById("file-list");
const emptyState = document.getElementById("empty-state");
const qrModal = document.getElementById("qr-modal");
const qrImage = document.getElementById("qr-image");
const qrFilename = document.getElementById("qr-filename");
const toast = document.getElementById("toast");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const publicUrlInput = document.getElementById("public-url");

function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2500);
}

function formatSize(bytes) {
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
    return bytes.toFixed(1) + " " + units[i];
}

function getFileIcon(name) {
    const ext = name.split(".").pop().toLowerCase();
    const icons = {
        pdf: "fa-file-pdf", doc: "fa-file-word", docx: "fa-file-word",
        xls: "fa-file-excel", xlsx: "fa-file-excel",
        zip: "fa-file-zipper", rar: "fa-file-zipper",
        mp3: "fa-file-audio", wav: "fa-file-audio",
        mp4: "fa-file-video", avi: "fa-file-video",
        jpg: "fa-file-image", jpeg: "fa-file-image", png: "fa-file-image",
        gif: "fa-file-image", svg: "fa-file-image",
        py: "fa-file-code", js: "fa-file-code", html: "fa-file-code",
    };
    return icons[ext] || "fa-file";
}

function updateStats() {
    fetch("/stats")
        .then(r => r.json())
        .then(data => {
            document.getElementById("stat-files").textContent = data.files;
            document.getElementById("stat-size").textContent = data.total_size;
            document.getElementById("stat-downloads").textContent = data.total_downloads;
        });
}

function createFileCard(file) {
    const card = document.createElement("div");
    card.className = "file-card";
    card.dataset.id = file.id;
    card.innerHTML = `
        <div class="file-icon"><i class="fa-solid ${getFileIcon(file.name)}"></i></div>
        <div class="file-info">
            <span class="file-name" title="${file.name}">${file.name}</span>
            <span class="file-meta">${file.size} &middot; just now &middot; 0 downloads</span>
        </div>
        <div class="file-actions">
            <button class="btn-icon" onclick="showQR('${file.id}', '${file.name}')" title="QR Code">
                <i class="fa-solid fa-qrcode"></i>
            </button>
            <a href="/preview/${file.id}" target="_blank" class="btn-icon" title="Preview">
                <i class="fa-solid fa-eye"></i>
            </a>
            <a href="/download/${file.id}" class="btn-icon btn-download" title="Download">
                <i class="fa-solid fa-download"></i>
            </a>
            <button class="btn-icon btn-delete" onclick="deleteFile('${file.id}')" title="Delete">
                <i class="fa-solid fa-xmark"></i>
            </button>
        </div>
    `;
    return card;
}

async function uploadFiles(files) {
    if (files.length === 0) return;
    const formData = new FormData();
    for (const f of files) formData.append("file", f);

    uploadProgress.style.display = "block";
    progressFill.style.width = "0%";
    progressText.textContent = `Uploading ${files.length} file(s)...`;

    try {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload");

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                progressFill.style.width = pct + "%";
                progressText.textContent = `Uploading... ${pct}%`;
            }
        };

        const result = await new Promise((resolve, reject) => {
            xhr.onload = () => resolve(JSON.parse(xhr.responseText));
            xhr.onerror = () => reject(new Error("Upload failed"));
            xhr.send(formData);
        });

        progressFill.style.width = "100%";
        progressText.textContent = "Upload complete!";

        if (emptyState) emptyState.style.display = "none";

        if (!fileList) {
            const section = document.createElement("div");
            section.className = "files-section";
            section.innerHTML = `
                <div class="section-header">
                    <h3><i class="fa-solid fa-clock-rotate-left"></i> Shared Files</h3>
                    <button class="btn-clear" onclick="clearAll()" title="Delete all files">
                        <i class="fa-solid fa-trash"></i> Clear All
                    </button>
                </div>
                <div class="file-list" id="file-list"></div>
            `;
            document.querySelector("main").appendChild(section);
        }

        const list = document.getElementById("file-list");
        for (const file of result.files) {
            list.prepend(createFileCard(file));
        }

        updateStats();
        showToast(`${result.files.length} file(s) uploaded`);
        setTimeout(() => { uploadProgress.style.display = "none"; }, 1500);
    } catch (err) {
        progressText.textContent = "Upload failed";
        progressFill.style.width = "0%";
        showToast("Upload failed");
    }
}

async function deleteFile(id) {
    try {
        await fetch(`/delete/${id}`, { method: "DELETE" });
        const card = document.querySelector(`.file-card[data-id="${id}"]`);
        if (card) {
            card.style.opacity = "0";
            card.style.transform = "translateX(20px)";
            setTimeout(() => card.remove(), 200);
        }
        updateStats();
        showToast("File deleted");
    } catch {
        showToast("Delete failed");
    }
}

async function clearAll() {
    const cards = document.querySelectorAll(".file-card");
    const ids = [...cards].map(c => c.dataset.id);
    for (const id of ids) {
        await fetch(`/delete/${id}`, { method: "DELETE" });
    }
    cards.forEach(c => c.remove());
    if (emptyState) emptyState.style.display = "block";
    updateStats();
    showToast("All files cleared");
}

function showQR(id, name) {
    qrImage.src = `/qr/${id}`;
    qrFilename.textContent = name;
    qrModal.classList.add("active");
}

function closeQR() {
    qrModal.classList.remove("active");
}

qrModal.addEventListener("click", (e) => {
    if (e.target === qrModal) closeQR();
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeQR();
});

dropZone.addEventListener("click", (e) => {
    if (e.target.closest(".btn-browse")) return;
    fileInput.click();
});

fileInput.addEventListener("change", () => {
    uploadFiles(fileInput.files);
    fileInput.value = "";
});

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    uploadFiles(e.dataTransfer.files);
});

document.addEventListener("paste", (e) => {
    const items = e.clipboardData?.files;
    if (items && items.length > 0) uploadFiles(items);
});

function copyUrl() {
    publicUrlInput.select();
    navigator.clipboard.writeText(publicUrlInput.value).then(() => {
        showToast("Link copied!");
    }).catch(() => {
        document.execCommand("copy");
        showToast("Link copied!");
    });
}

publicUrlInput.addEventListener("click", copyUrl);

function checkTunnel() {
    fetch("/tunnel-status")
        .then(r => r.json())
        .then(data => {
            if (data.online) {
                statusDot.className = "status-dot online";
                statusText.textContent = "Public (internet)";
                publicUrlInput.value = data.public_url;
            } else {
                statusDot.className = "status-dot local";
                statusText.textContent = "Local network only";
            }
        })
        .catch(() => {
            statusDot.className = "status-dot offline";
            statusText.textContent = "Offline";
        });
}

checkTunnel();
setInterval(checkTunnel, 10000);
updateStats();
