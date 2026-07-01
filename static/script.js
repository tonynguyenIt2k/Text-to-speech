document.addEventListener("DOMContentLoaded", () => {
    // State management
    let voices = [];
    let selectedVoice = null;
    let selectedFile = null;
    let sttProgressInterval = null;
    let rawUtterances = [];

    // DOM Elements
    const navItems = document.querySelectorAll(".nav-item");
    const mobileNavItems = document.querySelectorAll(".mobile-nav-item");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const apiStatusText = document.getElementById("api-status-text");
    const apiStatusDot = document.querySelector(".status-indicator .dot");

    // Custom API Base URL settings
    let apiBaseUrl = localStorage.getItem("api_base_url");
    if (apiBaseUrl === null) {
        const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
        apiBaseUrl = isLocal ? "" : "https://tony2k-ai-voice-studio.hf.space";
    }

    function getApiUrl(path) {
        if (!apiBaseUrl) return path;
        const base = apiBaseUrl.endsWith("/") ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
        return `${base}${path}`;
    }

    const apiBaseInput = document.getElementById("api-base-input");
    const apiBaseInputDocs = document.getElementById("api-base-input-docs");
    const btnSaveApiBase = document.getElementById("btn-save-api-base");

    // Theme Switcher Elements
    const themeCheckbox = document.getElementById("theme-toggle-checkbox");

    // Sidebar Collapsible Elements
    const toggleSidebarBtn = document.getElementById("sidebar-toggle");
    const sidebarElement = document.querySelector("aside");
    const mainCanvasElement = document.querySelector("main");
    const brandTextElement = document.getElementById("brand-text");
    const navLabelElements = document.querySelectorAll(".nav-label");

    // TTS Elements
    const ttsText = document.getElementById("tts-text");
    const charCount = document.getElementById("tts-char-count");
    const ttsRateSlider = document.getElementById("tts-rate-slider");
    const rateVal = document.getElementById("rate-val");
    const speedPresets = document.getElementById("speed-presets");
    const btnGenerateTts = document.getElementById("btn-generate-tts");
    
    // TTS Custom Player elements (Desktop)
    const ttsOutputCard = document.getElementById("tts-output-card");
    const previewVoiceName = document.getElementById("preview-voice-name");
    const previewTimeDisplay = document.getElementById("preview-time-display");
    const btnPlayPause = document.getElementById("btn-play-pause");
    const waveformVisualizer = document.getElementById("waveform-visualizer");
    const ttsAudio = document.getElementById("tts-audio");
    const btnDownloadAudio = document.getElementById("btn-download-audio");
    const btnCopyAudioUrl = document.getElementById("btn-copy-audio-url");

    // TTS Custom Player elements (Mobile)
    const mobilePreviewBar = document.getElementById("mobile-preview-bar");
    const mobilePreviewVoiceName = document.getElementById("mobile-preview-voice-name");
    const mobilePreviewTimeDisplay = document.getElementById("mobile-preview-time-display");
    const mobileWaveformVisualizer = document.getElementById("mobile-waveform-visualizer");
    const btnMobilePlayPause = document.getElementById("btn-mobile-play-pause");
    const btnMobileClose = document.getElementById("btn-mobile-close");

    // TTS Voice List elements
    const voiceSearch = document.getElementById("voice-search");
    const langSelect = document.getElementById("lang-select");
    const voiceListContainer = document.getElementById("voice-list-container");

    // STT Elements
    const sttDropzone = document.getElementById("stt-dropzone");
    const sttFileInput = document.getElementById("stt-file-input");
    const fileInfoContainer = document.getElementById("file-info-container");
    const dropzoneContent = document.querySelector(".dropzone-content");
    const selectedFileName = document.getElementById("selected-file-name");
    const selectedFileSize = document.getElementById("selected-file-size");
    const btnRemoveFile = document.getElementById("btn-remove-file");
    const sttLanguage = document.getElementById("stt-language");
    const sttUseTranslation = document.getElementById("stt-use-translation");
    const translationLangGroup = document.getElementById("translation-lang-group");
    const sttTranslationLanguage = document.getElementById("stt-translation-language");
    const btnGenerateStt = document.getElementById("btn-generate-stt");
    
    const sttProgress = document.getElementById("stt-progress");
    const sttStatusLabel = document.getElementById("stt-status-label");
    const sttPercentLabel = document.getElementById("stt-percent-label");
    const sttProgressFill = document.getElementById("stt-progress-fill");
    
    const transcriptContainer = document.getElementById("transcript-container");
    const sttActionsContainer = document.getElementById("stt-actions-container");
    const btnCopyTranscript = document.getElementById("btn-copy-transcript");
    const btnDownloadSrt = document.getElementById("btn-download-srt");

    // Portrait Avatars matching user design style
    const avatars = [
        "https://lh3.googleusercontent.com/aida-public/AB6AXuB7l3c3XjyTQpFOVJwqhZZ80FtgpBXdaew1b0WkbVX_CFLVeHtVu5YwqeyofX76jyTjZan44TBiE7ZFiAlQQrrlPaqQ2cvQLI9oZZ5lrmZsI0GYOXwsnLGtzidijpfHTnzl6ebRnVG_mF2WuBgUyoGWBcUL6GwRfM2g-m8v8QXQquy-wNmHZ3dBTSCwk7RR3Um5eVLJpM5htAdDIr-oG_Jh5mIRf1lHAI69zIqutk-Wllt1u2GFiI65", // female 1
        "https://lh3.googleusercontent.com/aida-public/AB6AXuDtl2mSmpCmtWx5PSqi492gRLjEHnXkxot3fdhPnmHkguo-5MQnimGJytRr53DRP8n4z6avKhHyKlgdglqTCp1Gpyk1N2hug6VmiIjGpBMmvuRfSNBN_M0DDgIAwE6t5MdOLPXMl4hA_2bldeYKMtiRDHV5YRr-Pi5PuqIQDP7rgZchnVOPfPfOLrXDbo9BHwT-xgrVHhJ3ApgWPVveuObz78uhmAjUuQ0ahHd0xX1bYEzHw2QqBOOp", // male 1
        "https://lh3.googleusercontent.com/aida-public/AB6AXuAOpweueGZzU6N8ygd0xN17peLpYDVsk6IJXtD1_pgAxgk1wHV_FZ8QJ1838zw-FPXjCUmmoHvYSvJbZSWnff0W6_LBwErtg7czC-Ov0b4x8gmx9-WKrhaKX4px2cCRvku1OXoiQPOo1F2XcfvEkDFVNXmTWSosqms7gCQkf45PVAYG38jw-7SggRYT7n7WyT8JXU24vTh_HbxtM16brEj6N8Nbg7Zm4rJw9ejJ-s0I2fgaw-Aip6gJ", // male 2
        "https://lh3.googleusercontent.com/aida-public/AB6AXuDiIMR0GwcMXJ2eDWwfkVQMbFc-VZiQhCfrbBEhC_Ws3t1BDbnTxBwQIKbzQQnLotCcWwJZUoRGxCLRLI_O1mwjcYIMcBPNr7v6CcDNFHg3ojeZyARElFf0rAO0v6xhVEq6J_kRNMDH2ADTbKP3ASNbUR5Z6JaCuWor_q2gZ9-NgIyHch1p8Mr-MhnpU0ercm19uHDqwWtP6JPbDtPMfS0wv47wu3Oyqfr7aHJs0M_hsm8V-82PU4Fu"  // female 2
    ];

    function getAvatarForVoice(voice, index) {
        const name = voice.display_name.toLowerCase();
        const lang = voice.lang.toLowerCase();
        
        if (lang.includes("vi")) {
            if (name.includes("nam") || name.includes("bản tin") || name.includes("thanh niên") || name.includes("kenny") || name.includes("đại đế") || name.includes("méo")) {
                return avatars[1]; // Minh Quân (male)
            }
            return avatars[0]; // Thanh Vy (female)
        } else if (lang.includes("en")) {
            return avatars[2]; // James (male)
        } else if (lang.includes("ja") || lang.includes("jp")) {
            return avatars[3]; // Sakura (female)
        }
        return avatars[index % avatars.length];
    }

    // Theme Management Logic (Checkbox Switch)
    let currentTheme = localStorage.getItem("theme");
    if (!currentTheme) {
        // Fallback to system OS preference
        const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        currentTheme = systemPrefersDark ? "dark" : "light";
    }

    function applyTheme(theme) {
        const html = document.documentElement;
        if (theme === "dark") {
            html.classList.add("dark");
            themeCheckbox.checked = true;
        } else {
            html.classList.remove("dark");
            themeCheckbox.checked = false;
        }
    }

    // Initialize theme on load
    applyTheme(currentTheme);

    // Toggle listener
    themeCheckbox.addEventListener("change", () => {
        if (themeCheckbox.checked) {
            applyTheme("dark");
            localStorage.setItem("theme", "dark");
        } else {
            applyTheme("light");
            localStorage.setItem("theme", "light");
        }
    });

    // Initialize API Base inputs
    if (apiBaseInput) {
        apiBaseInput.value = apiBaseUrl;
        apiBaseInput.addEventListener("input", () => {
            const val = apiBaseInput.value.trim();
            localStorage.setItem("api_base_url", val);
            apiBaseUrl = val;
            if (apiBaseInputDocs) apiBaseInputDocs.value = val;
            checkServerStatus();
        });
    }

    if (apiBaseInputDocs && btnSaveApiBase) {
        apiBaseInputDocs.value = apiBaseUrl;
        btnSaveApiBase.addEventListener("click", () => {
            const val = apiBaseInputDocs.value.trim();
            localStorage.setItem("api_base_url", val);
            apiBaseUrl = val;
            if (apiBaseInput) apiBaseInput.value = val;
            alert(`Đã lưu cấu hình API Server: ${val || "Mặc định (Relative)"}`);
            checkServerStatus();
        });
    }

    // Sidebar Collapsible Control
    let isCollapsed = false;

    // Responsive initializer: set correct margin on page load
    function updateResponsiveLayout() {
        const isDesktop = window.matchMedia("(min-width: 768px)").matches;
        if (isDesktop) {
            const sidebarWidth = isCollapsed ? "80px" : "280px";
            sidebarElement.style.width = sidebarWidth;
            mainCanvasElement.style.marginLeft = sidebarWidth;
        } else {
            mainCanvasElement.style.marginLeft = "0";
        }
    }
    updateResponsiveLayout();
    window.addEventListener("resize", updateResponsiveLayout);

    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener("click", () => {
            isCollapsed = !isCollapsed;
            
            if (isCollapsed) {
                sidebarElement.style.width = "80px";
                sidebarElement.classList.replace("p-6", "p-4");
                mainCanvasElement.style.marginLeft = "80px";
                brandTextElement.classList.add("hidden");
                navLabelElements.forEach(label => label.classList.add("hidden"));
                toggleSidebarBtn.querySelector("span").textContent = "chevron_right";
                toggleSidebarBtn.classList.remove("ml-auto");
                toggleSidebarBtn.classList.add("mx-auto");
            } else {
                sidebarElement.style.width = "280px";
                sidebarElement.classList.replace("p-4", "p-6");
                mainCanvasElement.style.marginLeft = "280px";
                brandTextElement.classList.remove("hidden");
                navLabelElements.forEach(label => label.classList.remove("hidden"));
                toggleSidebarBtn.querySelector("span").textContent = "chevron_left";
                toggleSidebarBtn.classList.add("ml-auto");
                toggleSidebarBtn.classList.remove("mx-auto");
            }
        });
    }

    // Check backend server status
    async function checkServerStatus() {
        try {
            const res = await fetch(getApiUrl("/api/status"));
            if (res.ok) {
                apiStatusText.textContent = "Server: Online";
                apiStatusDot.className = "material-symbols-outlined text-green-400 status-pulse dot";
            } else {
                throw new Error();
            }
        } catch {
            apiStatusText.textContent = "Server: Offline";
            apiStatusDot.className = "material-symbols-outlined status-pulse dot text-red-500";
        }
    }
    checkServerStatus();
    setInterval(checkServerStatus, 15000);

    // Tab Navigation switching (Desktop sidebar)
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const tabId = item.getAttribute("data-tab");
            switchTab(tabId);
        });
    });

    // Tab Navigation switching (Mobile bottom menu)
    mobileNavItems.forEach(item => {
        item.addEventListener("click", () => {
            const tabId = item.getAttribute("data-tab");
            switchTab(tabId);
        });
    });

    function switchTab(tabId) {
        // Reset scroll position of main canvas to top on tab switch
        if (mainCanvasElement) {
            mainCanvasElement.scrollTop = 0;
        }

        // Toggle Desktop active visual states
        navItems.forEach(nav => {
            const navTabId = nav.getAttribute("data-tab");
            if (navTabId === tabId) {
                nav.className = "nav-item w-full flex items-center gap-4 px-4 py-3 bg-primary-container/20 text-primary font-bold rounded-xl transition-all scale-100 active:scale-95 text-left";
            } else {
                nav.className = "nav-item w-full flex items-center gap-4 px-4 py-3 text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 rounded-xl transition-all scale-100 active:scale-95 text-left";
            }
        });

        // Toggle Mobile active visual states
        mobileNavItems.forEach(nav => {
            const navTabId = nav.getAttribute("data-tab");
            if (navTabId === tabId) {
                nav.className = "mobile-nav-item flex flex-col items-center justify-center text-primary font-bold scale-105 transition-all duration-300";
                nav.querySelector("span").style.fontVariationSettings = "'FILL' 1";
            } else {
                nav.className = "mobile-nav-item flex flex-col items-center justify-center text-on-surface-variant hover:text-primary transition-all duration-300";
                nav.querySelector("span").style.fontVariationSettings = "'FILL' 0";
            }
        });

        // Switch layout panels
        tabPanels.forEach(panel => {
            panel.classList.remove("active");
            panel.classList.add("hidden");
            if (panel.id === `panel-${tabId}`) {
                panel.classList.remove("hidden");
                // Add micro delay for transition animation
                setTimeout(() => panel.classList.add("active"), 50);
            }
        });
    }

    // TTS: Character count monitor
    ttsText.addEventListener("input", () => {
        charCount.textContent = `${ttsText.value.length} ký tự`;
    });

    // TTS: Rate multiplier slider & Presets
    ttsRateSlider.addEventListener("input", () => {
        const val = parseFloat(ttsRateSlider.value).toFixed(1);
        rateVal.textContent = val;
        updateSpeedPresetsActive(val);
    });

    if (speedPresets) {
        speedPresets.addEventListener("click", (e) => {
            const btn = e.target.closest(".preset-btn");
            if (btn) {
                const presetVal = btn.getAttribute("data-value");
                ttsRateSlider.value = presetVal;
                rateVal.textContent = parseFloat(presetVal).toFixed(1);
                updateSpeedPresetsActive(presetVal);
            }
        });
    }

    function updateSpeedPresetsActive(currentVal) {
        const numVal = parseFloat(currentVal);
        if (!speedPresets) return;
        speedPresets.querySelectorAll(".preset-btn").forEach(btn => {
            const btnVal = parseFloat(btn.getAttribute("data-value"));
            if (Math.abs(numVal - btnVal) < 0.05) {
                btn.className = "preset-btn px-3 py-1 rounded-lg bg-primary/10 text-primary text-label-sm font-bold hover:bg-primary/20 transition-all border border-primary/30";
            } else {
                btn.className = "preset-btn px-3 py-1 rounded-lg bg-surface-variant/50 text-on-surface-variant text-label-sm font-bold hover:bg-primary/20 hover:text-primary transition-all border border-transparent";
            }
        });
    }

    // TTS: Retrieve voices catalog
    async function loadVoices() {
        try {
            const res = await fetch(getApiUrl("/api/voices"));
            if (!res.ok) throw new Error("Failed to load voices list");
            voices = await res.json();
            renderVoices();
        } catch (err) {
            console.error(err);
            voiceListContainer.innerHTML = `<div class="voices-loader text-center py-20 text-red-400 font-body-md">Không thể tải danh sách giọng đọc</div>`;
        }
    }
    loadVoices();

    function renderVoices() {
        voiceListContainer.innerHTML = "";
        
        const searchQuery = voiceSearch.value.toLowerCase().trim();
        const activeLangFilter = langSelect ? langSelect.value : "all";

        const filteredVoices = voices.filter(v => {
            const matchesSearch = v.display_name.toLowerCase().includes(searchQuery) || v.voice_type.toLowerCase().includes(searchQuery);
            let matchesLang = activeLangFilter === "all";
            if (!matchesLang) {
                // Check if voice language matches filter prefix (e.g. vi-VN matches vi-VN, or vi matches vi-VN)
                matchesLang = v.lang.toLowerCase().includes(activeLangFilter.toLowerCase());
            }
            return matchesSearch && matchesLang;
        });

        if (filteredVoices.length === 0) {
            voiceListContainer.innerHTML = `<div class="voices-loader text-center py-20 text-outline/40 font-body-md">Không tìm thấy giọng đọc phù hợp</div>`;
            return;
        }

        filteredVoices.forEach((v, index) => {
            const isSelected = selectedVoice && selectedVoice.voice_type === v.voice_type;
            
            const card = document.createElement("div");
            card.className = `p-4 rounded-2xl flex items-center gap-4 cursor-pointer transition-all group ${
                isSelected 
                ? "bg-primary-container/10 border border-primary/30" 
                : "bg-surface-variant/20 border border-transparent hover:border-outline-variant/50"
            }`;
            
            const avatarUrl = getAvatarForVoice(v, index);
            
            card.innerHTML = `
                <div class="w-12 h-12 rounded-full overflow-hidden border-2 ${isSelected ? "border-primary/50" : "border-transparent group-hover:border-outline-variant/30"}">
                    <img class="w-full h-full object-cover" src="${avatarUrl}" alt="${v.display_name}"/>
                </div>
                <div class="flex-grow">
                    <h4 class="font-body-md font-bold text-on-surface">${v.display_name}</h4>
                    <p class="text-xs ${isSelected ? "text-primary/70" : "text-outline"} font-label-sm">${v.lang.split('-')[0].toUpperCase()} • ${v.voice_type.includes("female") ? "Nữ" : "Nam"} • CapCut</p>
                </div>
                <div class="w-8 h-8 rounded-full flex items-center justify-center ${isSelected ? "text-primary" : "text-outline group-hover:text-primary transition-colors"}">
                    <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' ${isSelected ? '1' : '0'};">
                        ${isSelected ? 'volume_up' : 'play_arrow'}
                    </span>
                </div>
            `;

            card.addEventListener("click", () => {
                selectedVoice = v;
                renderVoices();
            });

            // Select default voice on initial load
            if (!selectedVoice && v.voice_type === "BV074_streaming") {
                selectedVoice = v;
                card.className = "p-4 rounded-2xl bg-primary-container/10 border border-primary/30 flex items-center gap-4 cursor-pointer hover:bg-primary-container/20 transition-all group";
            }

            voiceListContainer.appendChild(card);
        });
    }

    // Filter controls
    voiceSearch.addEventListener("input", renderVoices);
    if (langSelect) {
        langSelect.addEventListener("change", renderVoices);
    }

    // TTS: Generate Voice API submission
    btnGenerateTts.addEventListener("click", async () => {
        const text = ttsText.value.trim();
        if (!text) {
            alert("Vui lòng nhập văn bản cần đọc!");
            return;
        }
        if (!selectedVoice) {
            alert("Vui lòng chọn một giọng đọc từ danh sách!");
            return;
        }

        // Show spinner state
        btnGenerateTts.disabled = true;
        btnGenerateTts.querySelector(".btn-text").textContent = "Đang tạo giọng nói...";
        btnGenerateTts.querySelector(".btn-icon-symbol").classList.add("hidden");
        btnGenerateTts.querySelector(".loader-spinner").classList.remove("hidden");
        
        // Hide preview elements initially
        ttsOutputCard.classList.add("hidden");
        mobilePreviewBar.classList.add("hidden");
        mobilePreviewBar.classList.add("translate-y-full");
        
        // Reset player UI
        waveformVisualizer.classList.remove("playing");
        mobileWaveformVisualizer.classList.remove("playing");
        btnPlayPause.querySelector("span").textContent = "play_arrow";
        btnMobilePlayPause.querySelector("span").textContent = "play_arrow";

        try {
            const response = await fetch(getApiUrl("/api/tts"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: text,
                    voice: selectedVoice.voice_type,
                    resource_id: selectedVoice.resource_id,
                    rate: parseFloat(ttsRateSlider.value)
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || "Synthesis request failed");
            }

            // Sync audio source
            ttsAudio.src = result.speech_url;
            btnDownloadAudio.href = result.speech_url;
            
            // Set text labels
            previewVoiceName.textContent = `PREVIEWING: ${result.display_name}`;
            mobilePreviewVoiceName.textContent = `${result.display_name} đang đọc...`;
            
            // Display Output widgets (desktop card and mobile bottom player bar)
            ttsOutputCard.classList.remove("hidden");
            mobilePreviewBar.classList.remove("hidden");
            // Micro delay to trigger browser entry transition
            setTimeout(() => {
                mobilePreviewBar.classList.remove("translate-y-full");
            }, 50);
            
            // Play immediately
            ttsAudio.play();

            // Copy direct link trigger
            btnCopyAudioUrl.onclick = () => {
                navigator.clipboard.writeText(result.speech_url);
                const originalContent = btnCopyAudioUrl.innerHTML;
                btnCopyAudioUrl.innerHTML = `<span class="material-symbols-outlined text-xs">done</span>Đã chép`;
                setTimeout(() => btnCopyAudioUrl.innerHTML = originalContent, 2000);
            };

        } catch (err) {
            console.error(err);
            alert(`Lỗi: ${err.message}`);
        } finally {
            // Restore generating buttons
            btnGenerateTts.disabled = false;
            btnGenerateTts.querySelector(".btn-text").textContent = "Bắt đầu tạo giọng nói";
            btnGenerateTts.querySelector(".btn-icon-symbol").classList.remove("hidden");
            btnGenerateTts.querySelector(".loader-spinner").classList.add("hidden");
        }
    });

    // Custom Player controls (Desktop)
    btnPlayPause.addEventListener("click", () => {
        if (ttsAudio.paused) {
            ttsAudio.play();
        } else {
            ttsAudio.pause();
        }
    });

    // Custom Player controls (Mobile)
    btnMobilePlayPause.addEventListener("click", () => {
        if (ttsAudio.paused) {
            ttsAudio.play();
        } else {
            ttsAudio.pause();
        }
    });

    btnMobileClose.addEventListener("click", () => {
        ttsAudio.pause();
        mobilePreviewBar.classList.add("translate-y-full");
        setTimeout(() => {
            mobilePreviewBar.classList.add("hidden");
        }, 300);
    });

    // Native audio binding syncs
    ttsAudio.addEventListener("play", () => {
        waveformVisualizer.classList.add("playing");
        mobileWaveformVisualizer.classList.add("playing");
        btnPlayPause.querySelector("span").textContent = "pause";
        btnMobilePlayPause.querySelector("span").textContent = "pause";
    });

    ttsAudio.addEventListener("pause", () => {
        waveformVisualizer.classList.remove("playing");
        mobileWaveformVisualizer.classList.remove("playing");
        btnPlayPause.querySelector("span").textContent = "play_arrow";
        btnMobilePlayPause.querySelector("span").textContent = "play_arrow";
    });

    ttsAudio.addEventListener("ended", () => {
        waveformVisualizer.classList.remove("playing");
        mobileWaveformVisualizer.classList.remove("playing");
        btnPlayPause.querySelector("span").textContent = "play_arrow";
        btnMobilePlayPause.querySelector("span").textContent = "play_arrow";
        const finalTime = formatAudioTime(ttsAudio.duration);
        previewTimeDisplay.textContent = finalTime + " / " + finalTime;
        mobilePreviewTimeDisplay.textContent = finalTime;
    });

    ttsAudio.addEventListener("timeupdate", () => {
        const current = formatAudioTime(ttsAudio.currentTime);
        const duration = ttsAudio.duration ? formatAudioTime(ttsAudio.duration) : "00:00";
        previewTimeDisplay.textContent = `${current} / ${duration}`;
        mobilePreviewTimeDisplay.textContent = `${current} / ${duration}`;
    });

    function formatAudioTime(secs) {
        if (isNaN(secs)) return "00:00";
        const minutes = Math.floor(secs / 60);
        const seconds = Math.floor(secs % 60);
        return `${padZero(minutes)}:${padZero(seconds)}`;
    }

    function padZero(num) {
        return num < 10 ? "0" + num : num;
    }


    // STT: Drag & Drop file selectors
    sttDropzone.addEventListener("click", () => sttFileInput.click());

    sttDropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        sttDropzone.classList.add("dragover");
    });

    sttDropzone.addEventListener("dragleave", () => {
        sttDropzone.classList.remove("dragover");
    });

    sttDropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        sttDropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleSTTFile(e.dataTransfer.files[0]);
        }
    });

    sttFileInput.addEventListener("change", () => {
        if (sttFileInput.files.length > 0) {
            handleSTTFile(sttFileInput.files[0]);
        }
    });

    function handleSTTFile(file) {
        selectedFile = file;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);

        // Swap dropzone display
        dropzoneContent.classList.add("hidden");
        fileInfoContainer.classList.remove("hidden");
        btnGenerateStt.disabled = false;
    }

    btnRemoveFile.addEventListener("click", (e) => {
        e.stopPropagation(); // Avoid uploader dialog popup
        selectedFile = null;
        sttFileInput.value = "";
        
        dropzoneContent.classList.remove("hidden");
        fileInfoContainer.classList.add("hidden");
        btnGenerateStt.disabled = true;
    });

    // STT: Toggle target translation lang selector
    sttUseTranslation.addEventListener("change", () => {
        if (sttUseTranslation.checked) {
            translationLangGroup.classList.remove("hidden");
        } else {
            translationLangGroup.classList.add("hidden");
        }
    });

    // STT: Execute recognition transcription
    btnGenerateStt.addEventListener("click", async () => {
        if (!selectedFile) return;

        // Reset UI Panels
        transcriptContainer.innerHTML = "";
        sttActionsContainer.classList.add("hidden");
        sttProgress.classList.remove("hidden");
        
        btnGenerateStt.disabled = true;
        btnGenerateStt.querySelector(".btn-text").textContent = "Đang nhận diện...";
        btnGenerateStt.querySelector(".loader-spinner").classList.remove("hidden");
        rawUtterances = [];

        // Progress bar simulation animation
        let percent = 5;
        updateSTTProgressBar("Đang tải file lên máy chủ...", percent);
        
        sttProgressInterval = setInterval(() => {
            if (percent < 95) {
                percent += Math.floor(Math.random() * 6) + 1;
                if (percent > 95) percent = 95;
                
                let label = "Đang trích xuất âm thanh...";
                if (percent > 35) label = "Đang gửi yêu cầu nhận diện lên CapCut...";
                if (percent > 70) label = "Chờ máy chủ CapCut căn chỉnh phụ đề...";
                
                updateSTTProgressBar(label, percent);
            }
        }, 1100);

        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("language", sttLanguage.value);
        formData.append("use_translation", sttUseTranslation.checked);
        formData.append("translation_language", sttTranslationLanguage.value);

        try {
            const response = await fetch(getApiUrl("/api/stt"), {
                method: "POST",
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || "Speech to Text processing failed");
            }

            clearInterval(sttProgressInterval);
            updateSTTProgressBar("Hoàn thành!", 100);
            setTimeout(() => sttProgress.classList.add("hidden"), 1000);

            rawUtterances = result.utterances || [];
            renderSubtitles(rawUtterances);

        } catch (err) {
            console.error(err);
            clearInterval(sttProgressInterval);
            sttProgress.classList.add("hidden");
            transcriptContainer.innerHTML = `
                <div class="transcript-empty flex flex-col items-center justify-center h-full py-20 text-center text-red-400 space-y-3">
                    <span class="material-symbols-outlined text-5xl">error</span>
                    <p class="font-body-md text-sm">Lỗi: ${err.message}</p>
                </div>
            `;
        } finally {
            btnGenerateStt.disabled = false;
            btnGenerateStt.querySelector(".btn-text").textContent = "Bắt đầu nhận diện";
            btnGenerateStt.querySelector(".loader-spinner").classList.add("hidden");
        }
    });

    function updateSTTProgressBar(status, percent) {
        sttStatusLabel.textContent = status;
        sttPercentLabel.textContent = `${percent}%`;
        sttProgressFill.style.width = `${percent}%`;
    }

    function renderSubtitles(utterances) {
        transcriptContainer.innerHTML = "";

        if (utterances.length === 0) {
            transcriptContainer.innerHTML = `
                <div class="transcript-empty flex flex-col items-center justify-center h-full py-20 text-center text-outline/30 space-y-3">
                    <span class="material-symbols-outlined text-5xl">search_off</span>
                    <p class="font-body-md text-sm">Không phát hiện thấy âm thanh lời nói trong tệp này.</p>
                </div>
            `;
            return;
        }

        sttActionsContainer.classList.remove("hidden");

        utterances.forEach(u => {
            const formattedTime = `${formatTime(u.start_time)} → ${formatTime(u.end_time)}`;
            const block = document.createElement("div");
            block.className = "flex gap-4 p-4 rounded-xl hover:bg-surface-variant/20 transition-all border border-transparent";
            block.innerHTML = `
                <span class="font-mono text-xs text-primary font-bold w-24 shrink-0 pt-0.5">${formattedTime}</span>
                <span class="text-on-surface text-sm flex-grow">${u.text}</span>
            `;
            transcriptContainer.appendChild(block);
        });

        // Sync action clicks
        btnCopyTranscript.onclick = () => {
            const fullText = utterances.map(u => u.text).join("\n");
            navigator.clipboard.writeText(fullText);
            
            const originalHTML = btnCopyTranscript.innerHTML;
            btnCopyTranscript.innerHTML = `<span class="material-symbols-outlined text-xs">done</span><span>Đã sao chép</span>`;
            setTimeout(() => btnCopyTranscript.innerHTML = originalHTML, 2000);
        };

        btnDownloadSrt.onclick = () => {
            const srtContent = convertToSRT(utterances);
            const blob = new Blob([srtContent], { type: "text/srt;charset=utf-8;" });
            const url = URL.createObjectURL(blob);
            const downloadLink = document.createElement("a");
            downloadLink.href = url;
            downloadLink.download = `${selectedFile.name.split('.')[0]}_subtitles.srt`;
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            URL.revokeObjectURL(url);
        };
    }

    // SRT conversion logic
    function convertToSRT(utterances) {
        let srt = "";
        utterances.forEach((item, index) => {
            const start = formatSRTTime(item.start_time);
            const end = formatSRTTime(item.end_time);
            srt += `${index + 1}\n${start} --> ${end}\n${item.text}\n\n`;
        });
        return srt;
    }

    function formatSRTTime(ms) {
        const hours = Math.floor(ms / 3600000);
        const minutes = Math.floor((ms % 3600000) / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        const milliseconds = ms % 1000;
        
        return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)},${pad(milliseconds, 3)}`;
    }

    // Helper padding
    function pad(num, size) {
        let s = num + "";
        while (s.length < size) s = "0" + s;
        return s;
    }

    // Time conversion formatting (ms -> MM:SS)
    function formatTime(ms) {
        const totalSecs = Math.floor(ms / 1000);
        const mins = Math.floor(totalSecs / 60);
        const secs = totalSecs % 60;
        return `${padZero(mins)}:${padZero(secs)}`;
    }

    // Helper to format bytes to human readable format
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
});
