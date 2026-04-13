// 렌더링 전 토큰 확인 — 없으면 즉시 로그인 페이지로 이동
// 이 파일은 반드시 <head> 최상단에 동기 로드되어야 합니다.
(function () {
    if (!localStorage.getItem("access_token")) {
        location.replace("login.html");
    }
})();
