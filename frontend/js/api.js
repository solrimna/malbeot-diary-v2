const API_BASE_URL = "/api/v1";

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        const detail = typeof payload === "object" && payload !== null
            ? payload.detail
            : payload;
        throw new Error(detail || "요청 처리 중 오류가 발생했습니다.");
    }

    return payload;
}
