// 검색 모달 HTML을 body에 즉시 주입 (stt.js의 DOMContentLoaded 초기화보다 먼저 DOM에 삽입되도록)
(function injectSearchModal() {
    const el = document.createElement("div");
    el.innerHTML = `
        <div id="search-modal" class="diary-modal hidden">
            <div class="diary-modal-backdrop" onclick="closeSearchModal()"></div>
            <div class="diary-modal-card">
                <div class="flex items-start justify-between gap-4 mb-8">
                    <div>
                        <p class="font-script text-xl text-white/70 mb-1">AI memory search</p>
                        <h2 class="text-2xl md:text-3xl font-semibold text-white">AI로 기억 찾기</h2>
                    </div>
                    <button type="button" class="diary-close-btn" onclick="closeSearchModal()">✕</button>
                </div>
                <div class="space-y-5">
                    <div>
                        <div class="flex items-center justify-between mb-1">
                            <label class="persona-label translate-x-2 translate-y-6">찾고 싶은 기억</label>
                            <div class="flex flex-col items-end gap-0 -translate-x-4 translate-y-0">
                                <button type="button" id="voice-btn" class="voice-btn-modal">음성으로 입력</button>
                                <div class="flex items-center gap-1 text-xs text-white/40">
                                    <span>모드:</span>
                                    <button type="button" id="stt-mode-toggle" class="text-xs text-white/60 underline underline-offset-2 hover:text-white transition-colors bg-transparent border-none cursor-pointer p-0"></button>
                                </div>
                                <span id="stt-status" class="hidden text-xs text-white/60 text-right max-w-[200px] leading-snug"></span>
                            </div>
                        </div>
                        <textarea id="diary-search-input" class="persona-textarea diary-search-textarea" placeholder="예: 친구랑 카페 갔던 날, 비슷한 내용의 일기 찾아줘"></textarea>
                    </div>
                    <button type="button" id="diary-search-button" onclick="DiarySearch()" class="diary-main-btn w-full sm:w-auto">
                        검색하기
                    </button>
                    <div id="diary-search-result" class="diary-search-result">
                        아직 검색한 내용이 없어요.
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(el.firstElementChild);
})();

// ── 모달 열기/닫기 ────────────────────────────────
function openSearchModal() {
    const modal = document.getElementById("search-modal");
    if (modal) modal.classList.remove("hidden");
}

function closeSearchModal() {
    const modal = document.getElementById("search-modal");
    if (modal) modal.classList.add("hidden");
}

// ── AI 검색 ───────────────────────────────────────
async function DiarySearch() {
    const input = document.getElementById("diary-search-input");
    const result = document.getElementById("diary-search-result");
    const searchButton = document.getElementById("diary-search-button");

    if (!input || !result) return;

    const keyword = input.value.trim();
    if (!keyword) {
        showAppToast("검색하고 싶은 내용을 입력해주세요.", "info", "입력 확인");
        return;
    }

    if (searchButton) {
        searchButton.disabled = true;
        searchButton.textContent = "검색 중...";
    }
    result.innerHTML = "검색 중이에요...";

    try {
        const response = await apiRequest("/search/", {
            method: "POST",
            body: getJsonBody({ query: keyword }),
        });

        let html = `<p class="mb-3">${escapeHtml(response.answer).replace(/\n/g, "<br>")}</p>`;

        if (response.results && response.results.length > 0) {
            html += `<div class="space-y-2 mt-3">`;
            response.results.forEach((diary) => {
                html += `
                    <div class="search-result-item cursor-pointer hover:opacity-80"
                         onclick="window.location.href='diary_read.html?id=${encodeURIComponent(diary.id)}'">
                        <div class="text-sm text-white/50">${escapeHtml(diary.diary_date)}</div>
                        <div class="text-sm text-white/80 mt-1">${escapeHtml(diary.content.slice(0, 80))}${diary.content.length > 80 ? "..." : ""}</div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        result.innerHTML = html;
    } catch (_) {
        result.innerHTML = "검색 중 오류가 발생했어요. 다시 시도해주세요.";
    } finally {
        if (searchButton) {
            searchButton.disabled = false;
            searchButton.textContent = "검색하기";
        }
    }
}
