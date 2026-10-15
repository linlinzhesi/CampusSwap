/* ============================================================
   app.js - 前端逻辑
   作用：把页面上的按钮、输入框，和后端接口连接起来。
   核心思路：用户点按钮 → JS 发请求给后端 → 拿到数据 → 更新页面。
   ============================================================ */

// ------------------------------------------------------------------
// 全局状态
// ------------------------------------------------------------------
let token = localStorage.getItem("token") || null;   // 登录 token（存 localStorage，刷新页面不丢）
let currentUser = null;                              // 当前登录用户
let currentPage = 1;                                 // 当前页码
let categories = [];                                 // 分类列表（缓存）

// 后端接口地址（同源，直接用相对路径）
const API = "";

// ------------------------------------------------------------------
// 工具函数：发请求
// path: 接口路径；options: 请求配置（方法、请求体等）
// 会自动带上 token，并统一处理错误
// ------------------------------------------------------------------
async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (token) headers["Authorization"] = "Bearer " + token;

    const resp = await fetch(API + path, { ...options, headers });
    // 204 表示「成功但无内容」（如下架接口），直接返回 null
    if (resp.status === 204) return null;

    const data = await resp.json().catch(() => ({}));
    // 如果后端返回错误状态码，抛出一个带提示信息的错误
    if (!resp.ok) {
        throw new Error(data.detail || "请求失败");
    }
    return data;
}

// ------------------------------------------------------------------
// 页面加载完成后的初始化
// ------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    initCategories();      // 加载分类
    if (token) {           // 如果本地有 token，自动恢复登录状态
        fetchMe();
    }
    loadProducts();        // 加载商品列表

    // 绑定各种按钮事件
    bindEvents();
});

// ------------------------------------------------------------------
// 绑定按钮点击事件
// ------------------------------------------------------------------
function bindEvents() {
    // 登录
    document.getElementById("btn-login").addEventListener("click", doLogin);
    document.getElementById("login-password").addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });

    // 退出
    document.getElementById("btn-logout").addEventListener("click", doLogout);

    // 注册
    document.getElementById("btn-show-register").addEventListener("click", () => showModal("register-modal"));
    document.getElementById("btn-cancel-register").addEventListener("click", () => hideModal("register-modal"));
    document.getElementById("btn-do-register").addEventListener("click", doRegister);

    // 搜索 & 刷新
    document.getElementById("btn-search").addEventListener("click", () => { currentPage = 1; loadProducts(); });
    document.getElementById("btn-refresh").addEventListener("click", () => { currentPage = 1; loadProducts(); });
    document.getElementById("search-keyword").addEventListener("keydown", e => { if (e.key === "Enter") { currentPage = 1; loadProducts(); } });

    // 发布商品
    document.getElementById("btn-publish").addEventListener("click", doPublish);

    // 详情关闭
    document.getElementById("btn-close-detail").addEventListener("click", () => hideModal("detail-modal"));
}

// ------------------------------------------------------------------
// 登录 / 注册 / 退出
// ------------------------------------------------------------------
async function doLogin() {
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;
    if (!username || !password) { alert("请输入用户名和密码"); return; }

    try {
        const data = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ username, password }),
        });
        token = data.access_token;
        currentUser = data.user;
        localStorage.setItem("token", token);
        updateUserUI();
        alert("登录成功！");
        loadProducts();
        loadMyProducts();
    } catch (e) {
        alert(e.message);
    }
}

async function doRegister() {
    const username = document.getElementById("r-username").value.trim();
    const password = document.getElementById("r-password").value;
    if (username.length < 3 || password.length < 6) {
        document.getElementById("register-msg").textContent = "用户名至少3字符，密码至少6字符";
        return;
    }
    try {
        await api("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({ username, password }),
        });
        hideModal("register-modal");
        alert("注册成功，请登录");
        document.getElementById("login-username").value = username;
        document.getElementById("login-password").value = "";
    } catch (e) {
        document.getElementById("register-msg").textContent = e.message;
    }
}

function doLogout() {
    token = null;
    currentUser = null;
    localStorage.removeItem("token");
    updateUserUI();
    loadProducts();
    loadMyProducts();
}

// 获取当前用户信息（用 token 换用户）
async function fetchMe() {
    try {
        currentUser = await api("/api/users/me");
        updateUserUI();
        loadMyProducts();
    } catch (e) {
        // token 失效，清除本地状态
        token = null;
        localStorage.removeItem("token");
        updateUserUI();
    }
}

// 根据登录状态，切换顶部 UI（显示登录框 or 显示用户名）
function updateUserUI() {
    const loginArea = document.getElementById("login-area");
    const userArea = document.getElementById("user-area");
    const publishForm = document.getElementById("publish-form");
    const publishTip = document.getElementById("publish-tip");

    if (currentUser) {
        loginArea.style.display = "none";
        userArea.style.display = "flex";
        document.getElementById("current-username").textContent = currentUser.username;
        publishForm.style.display = "block";
        publishTip.style.display = "none";
    } else {
        loginArea.style.display = "flex";
        userArea.style.display = "none";
        publishForm.style.display = "none";
        publishTip.style.display = "block";
    }
}

// ------------------------------------------------------------------
// 分类
// ------------------------------------------------------------------
async function initCategories() {
    try {
        categories = await api("/api/categories");
        // 填充搜索栏的分类下拉
        const searchSel = document.getElementById("search-category");
        // 填充发布表单的分类下拉
        const publishSel = document.getElementById("p-category");
        categories.forEach(c => {
            const opt1 = document.createElement("option");
            opt1.value = c.id; opt1.textContent = c.name;
            searchSel.appendChild(opt1);
            const opt2 = document.createElement("option");
            opt2.value = c.id; opt2.textContent = c.name;
            publishSel.appendChild(opt2);
        });
    } catch (e) {
        console.error("加载分类失败", e);
    }
}

// ------------------------------------------------------------------
// 商品列表
// ------------------------------------------------------------------
async function loadProducts() {
    const keyword = document.getElementById("search-keyword").value.trim();
    const categoryId = document.getElementById("search-category").value;
    const listEl = document.getElementById("product-list");

    listEl.innerHTML = '<p class="empty-tip">加载中…</p>';

    // 拼查询参数
    let params = `page=${currentPage}&size=12`;
    if (categoryId) params += `&category_id=${categoryId}`;
    if (keyword) params += `&keyword=${encodeURIComponent(keyword)}`;

    try {
        const data = await api(`/api/products?${params}`);
        renderProducts(data);
    } catch (e) {
        listEl.innerHTML = `<p class="empty-tip">加载失败：${e.message}</p>`;
    }
}

function renderProducts(data) {
    const listEl = document.getElementById("product-list");
    if (data.items.length === 0) {
        listEl.innerHTML = '<p class="empty-tip">暂无商品，快发布一个吧～</p>';
    } else {
        listEl.innerHTML = data.items.map(p => `
            <div class="product-card" data-id="${p.id}">
                <div class="title">${escapeHtml(p.title)}</div>
                <div class="price">¥${p.price}</div>
                <div class="meta">
                    <span class="category-tag">${categoryName(p.category_id)}</span>
                    <span>${escapeHtml(p.seller_name || "未知")} · ${p.view_count}次浏览</span>
                </div>
            </div>
        `).join("");
        // 给每个卡片绑定点击事件（查看详情）
        listEl.querySelectorAll(".product-card").forEach(card => {
            card.addEventListener("click", () => showDetail(card.dataset.id));
        });
    }
    renderPagination(data);
}

function categoryName(id) {
    const c = categories.find(x => x.id === id);
    return c ? c.name : "其他";
}

// 分页控件
function renderPagination(data) {
    const pageEl = document.getElementById("pagination");
    const totalPages = Math.max(1, Math.ceil(data.total / data.size));
    pageEl.innerHTML = `
        <button class="btn btn-ghost" ${currentPage <= 1 ? "disabled" : ""} onclick="goPage(${currentPage - 1})">上一页</button>
        <span>第 ${currentPage} / ${totalPages} 页（共 ${data.total} 件）</span>
        <button class="btn btn-ghost" ${currentPage >= totalPages ? "disabled" : ""} onclick="goPage(${currentPage + 1})">下一页</button>
    `;
}

function goPage(p) {
    currentPage = p;
    loadProducts();
}

// ------------------------------------------------------------------
// 商品详情
// ------------------------------------------------------------------
async function showDetail(id) {
    try {
        const p = await api(`/api/products/${id}`);
        document.getElementById("d-title").textContent = p.title;
        document.getElementById("d-price").textContent = "¥" + p.price;
        document.getElementById("d-meta").innerHTML = `
            卖家：${escapeHtml(p.seller_name || "未知")}　分类：${categoryName(p.category_id)}<br>
            浏览量：${p.view_count}　发布时间：${new Date(p.created_at).toLocaleString()}
        `;
        document.getElementById("d-desc").textContent = p.description || "（无描述）";
        showModal("detail-modal");
        loadProducts(); // 刷新列表（浏览量 +1 了）
    } catch (e) {
        alert(e.message);
    }
}

// ------------------------------------------------------------------
// 发布商品
// ------------------------------------------------------------------
async function doPublish() {
    const title = document.getElementById("p-title").value.trim();
    const price = document.getElementById("p-price").value;
    const categoryId = document.getElementById("p-category").value;
    const desc = document.getElementById("p-desc").value.trim();

    if (!title || !price) { alert("请填写标题和价格"); return; }

    try {
        await api("/api/products", {
            method: "POST",
            body: JSON.stringify({
                title,
                price: parseFloat(price),
                category_id: categoryId ? parseInt(categoryId) : null,
                description: desc || null,
            }),
        });
        alert("发布成功！");
        // 清空表单
        document.getElementById("p-title").value = "";
        document.getElementById("p-price").value = "";
        document.getElementById("p-desc").value = "";
        currentPage = 1;
        loadProducts();
        loadMyProducts();
    } catch (e) {
        alert(e.message);
    }
}

// ------------------------------------------------------------------
// 我的商品（管理：下架）
// ------------------------------------------------------------------
async function loadMyProducts() {
    const el = document.getElementById("my-products");
    if (!currentUser) {
        el.innerHTML = '<p class="empty-tip">登录后可管理自己发布的商品</p>';
        return;
    }
    try {
        // 拿到全部商品，前端过滤出「我的」（后端列表接口暂不支持按卖家筛，这里简单处理）
        const data = await api(`/api/products?page=1&size=100`);
        const mine = data.items.filter(p => p.seller_id === currentUser.id);
        if (mine.length === 0) {
            el.innerHTML = '<p class="empty-tip">你还没有发布过商品</p>';
        } else {
            el.innerHTML = mine.map(p => `
                <div class="my-item">
                    <span class="my-title ${p.status === 0 ? 'status-off' : ''}">${escapeHtml(p.title)}</span>
                    <span class="my-actions">
                        ${p.status === 1
                            ? `<button class="btn btn-danger" onclick="offProduct(${p.id})">下架</button>`
                            : `<span style="color:#999;font-size:12px;">已下架</span>`}
                    </span>
                </div>
            `).join("");
        }
    } catch (e) {
        el.innerHTML = `<p class="empty-tip">加载失败</p>`;
    }
}

async function offProduct(id) {
    if (!confirm("确认下架这个商品吗？")) return;
    try {
        await api(`/api/products/${id}`, { method: "DELETE" });
        alert("已下架");
        loadProducts();
        loadMyProducts();
    } catch (e) {
        alert(e.message);
    }
}

// ------------------------------------------------------------------
// 弹窗 & 工具
// ------------------------------------------------------------------
function showModal(id) {
    document.getElementById(id).style.display = "flex";
}
function hideModal(id) {
    document.getElementById(id).style.display = "none";
}

// 转义 HTML，防止 XSS（用户输入的内容不能当 HTML 直接渲染）
function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
