class AppNav extends HTMLElement {
    connectedCallback() {
        const NAV_LINKS = [
            { href: "diary_write.html", label: "일기 작성하기" },
            { href: "my-diary.html",    label: "나의 일기장"   },
        ];

        const PROFILE_LINKS = [
            { href: "my_profile.html", label: "프로필"   },
            { href: "profile.html",    label: "나의 현황" },
            { href: "settings.html",   label: "설정"     },
        ];

        // localStorage에서 닉네임 읽기 (auth.js 로드 전이므로 직접 접근)
        function getNavNickname() {
            try {
                const raw = localStorage.getItem("auth_user");
                return raw ? (JSON.parse(raw).nickname || "") : "";
            } catch (_) { return ""; }
        }

        const current  = location.pathname.split("/").pop() || "";
        const nickname = getNavNickname();

        const links = NAV_LINKS.map(({ href, label }) => {
            const active = href === current ? " is-active" : "";
            return `<a href="${href}" class="nav-link${active}">${label}</a>`;
        }).join("");

        const dropdownItems = PROFILE_LINKS.map(({ href, label }) => {
            const active = href === current ? " is-active" : "";
            return `<a href="${href}" class="nav-dropdown-item${active}">${label}</a>`;
        }).join("");

        this.innerHTML = `
            <div class="nav-inner">
                <div class="nav-title-wrap">
                    <a href="index.html" class="nav-title-script">Write Down Your Day</a>
                </div>
                <div class="nav-divider"></div>
                <div class="nav-links">
                    ${links}
                    <button type="button" class="nav-search-btn" onclick="openSearchModal()">AI로 기억 찾기</button>
                    <div class="nav-profile-wrap" id="nav-profile-wrap">
                        <button type="button" class="nav-profile-btn" id="nav-profile-btn" aria-label="프로필 메뉴">
                            <span class="nav-profile-icon">👤</span>
                            ${nickname ? `<span class="nav-profile-nickname">${escapeHtml(nickname)}</span>` : ""}
                        </button>
                        <div class="nav-profile-dropdown" id="nav-profile-dropdown">
                            ${dropdownItems}
                            <div class="nav-dropdown-divider"></div>
                            <button type="button" class="nav-dropdown-item nav-dropdown-logout" id="nav-logout-btn">로그아웃</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 드롭다운 토글
        const wrap      = this.querySelector("#nav-profile-wrap");
        const btn       = this.querySelector("#nav-profile-btn");
        const logoutBtn = this.querySelector("#nav-logout-btn");

        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            wrap.classList.toggle("is-open");
        });

        // 로그아웃
        logoutBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (typeof logout === "function") {
                await logout();
            } else {
                localStorage.removeItem("access_token");
                localStorage.removeItem("auth_user");
            }
            window.location.href = "index.html";
        });

        // 외부 클릭 시 닫기
        document.addEventListener("click", () => {
            wrap.classList.remove("is-open");
        });
    }
}

customElements.define("app-nav", AppNav);
