// ── 날짜 포맷 헬퍼 ────────────────────────────────────────
function formatDate(isoString) {
    if (!isoString) return "—";
    const d = new Date(isoString);
    return d.toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
}

// ── 프로필 로드 ───────────────────────────────────────────
async function loadProfile() {
    try {
        const user = await apiRequest("/users/me", { method: "GET" });

        document.getElementById("display-nickname").textContent = user.nickname || "—";
        document.getElementById("display-username").textContent = `@${user.username}`;
        document.getElementById("display-created-at").textContent = formatDate(user.created_at);
        document.getElementById("display-last-login").textContent = formatDate(user.last_login_at);

        // 닉네임 인풋 초기값
        document.getElementById("edit-nickname").value = user.nickname || "";

        // 아바타: 이니셜
        const initial = (user.nickname || user.username || "?")[0].toUpperCase();
        const avatar = document.getElementById("profile-avatar");
        avatar.textContent = initial;
    } catch (err) {
        // 401은 api.js에서 리다이렉트 처리됨
    }
}

// ── 프로필 저장 ───────────────────────────────────────────
async function saveProfile() {
    const nickname = document.getElementById("edit-nickname").value.trim();
    const password = document.getElementById("edit-password").value;
    const passwordConfirm = document.getElementById("edit-password-confirm").value;
    const msg = document.getElementById("save-msg");
    const btn = document.getElementById("save-profile-btn");

    // 메시지 초기화
    msg.classList.add("hidden");
    msg.textContent = "";

    // 유효성 검사
    if (!nickname) {
        showMsg(msg, "닉네임을 입력해주세요.", true);
        return;
    }

    if (password || passwordConfirm) {
        if (password.length < 8) {
            showMsg(msg, "비밀번호는 8자 이상이어야 합니다.", true);
            return;
        }
        if (password !== passwordConfirm) {
            showMsg(msg, "비밀번호가 일치하지 않습니다.", true);
            return;
        }
    }

    // 변경 페이로드 구성 (변경된 값만)
    const body = { nickname };
    if (password) body.password = password;

    btn.disabled = true;
    btn.textContent = "저장 중...";

    try {
        const updated = await apiRequest("/users/me", {
            method: "PATCH",
            body: JSON.stringify(body),
        });

        // 로컬 스토리지 유저 정보 갱신
        const stored = getAuthUser();
        if (stored) {
            stored.nickname = updated.nickname;
            localStorage.setItem("auth_user", JSON.stringify(stored));
        }

        // 화면 갱신
        document.getElementById("display-nickname").textContent = updated.nickname;
        document.getElementById("profile-avatar").textContent = (updated.nickname || updated.username || "?")[0].toUpperCase();

        // 비밀번호 필드 초기화
        document.getElementById("edit-password").value = "";
        document.getElementById("edit-password-confirm").value = "";

        showMsg(msg, "저장되었습니다.", false);
    } catch (err) {
        showMsg(msg, err.message || "저장에 실패했습니다.", true);
    } finally {
        btn.disabled = false;
        btn.textContent = "저장하기";
    }
}

// ── 탈퇴 확인 토글 ───────────────────────────────────────
function toggleDeleteConfirm(show) {
    const box = document.getElementById("delete-confirm-box");
    const deleteMsg = document.getElementById("delete-msg");
    if (show) {
        box.classList.remove("hidden");
    } else {
        box.classList.add("hidden");
        deleteMsg.classList.add("hidden");
        deleteMsg.textContent = "";
    }
}

// ── 회원 탈퇴 ─────────────────────────────────────────────
async function deleteAccount() {
    const btn = document.getElementById("confirm-delete-btn");
    const msg = document.getElementById("delete-msg");

    btn.disabled = true;
    btn.textContent = "처리 중...";

    try {
        await apiRequest("/users/me", { method: "DELETE" });
        clearAuth();
        window.location.href = "index.html";
    } catch (err) {
        showMsg(msg, err.message || "탈퇴 처리에 실패했습니다.", true);
        btn.disabled = false;
        btn.textContent = "네, 탈퇴합니다";
    }
}

// ── 메시지 헬퍼 ──────────────────────────────────────────
function showMsg(el, text, isError) {
    el.textContent = text;
    el.style.color = isError ? "#ff6b6b" : "#7ec97e";
    el.classList.remove("hidden");
}

// ── 초기화 ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    if (!requireAuth()) return;
    loadProfile();
});
