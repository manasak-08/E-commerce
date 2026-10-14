/**
 * ManChi's Luxury Fashion & Lifestyle
 * Complete Frontend Controller & State Manager
 */

// Application State
const state = {
    currentUser: null,
    cart: [],
    appliedCoupon: null,
    useRewardPoints: false,
    allProducts: [],
    allCombos: [],
    allCoupons: [],
    allOrders: [],
    activeView: 'home',
    currentTrackingOrderId: null,
    selectedHomeDealType: 'all'
};

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    loadLocalCart();
    checkAuthStatus();
    loadStoreData();
    setupEventListeners();
});

// -------------------------------------------------------------
// Authentication & Role-Based UI
// -------------------------------------------------------------
async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/me');
        const data = await res.json();
        if (data.success && data.user) {
            state.currentUser = data.user;
        } else {
            state.currentUser = null;
        }
    } catch (e) {
        console.error('Error checking auth:', e);
        state.currentUser = null;
    }
    updateUserUI();
}

function updateUserUI() {
    const userMenuBtn = document.getElementById('userNameDisplay');
    const guestDropdown = document.getElementById('guestDropdownItems');
    const userDropdown = document.getElementById('userDropdownItems');
    const adminDropdown = document.getElementById('adminDropdownItems');
    const rewardPill = document.getElementById('rewardPointsPill');
    const rewardCount = document.getElementById('rewardPointsCount');
    const cartBtn = document.getElementById('cartBtn');
    const adminTopBar = document.getElementById('adminTopBar');

    if (!state.currentUser) {
        // Guest User
        userMenuBtn.textContent = 'Sign In';
        guestDropdown.classList.remove('d-none');
        userDropdown.classList.add('d-none');
        adminDropdown.classList.add('d-none');
        rewardPill.classList.add('d-none');
        adminTopBar.classList.add('d-none');

        // Customer Cart is VISIBLE for guest shoppers
        cartBtn.classList.remove('d-none');
    } else if (state.currentUser.role === 'admin') {
        // ADMIN USER: STRICT ROLE-BASED UI
        // Requirement 9: REMOVE CART FROM ADMIN COMPLETELY
        cartBtn.classList.add('d-none'); // HIDE CART BUTTON & BADGE
        closeCartDrawer();

        userMenuBtn.textContent = 'Admin';
        guestDropdown.classList.add('d-none');
        userDropdown.classList.add('d-none');
        adminDropdown.classList.remove('d-none');
        rewardPill.classList.add('d-none');
        adminTopBar.classList.remove('d-none');

        document.getElementById('dropdownAdminName').textContent = state.currentUser.name || 'Admin';
    } else {
        // NORMAL CUSTOMER USER
        userMenuBtn.textContent = state.currentUser.name.split(' ')[0];
        guestDropdown.classList.add('d-none');
        userDropdown.classList.remove('d-none');
        adminDropdown.classList.add('d-none');
        adminTopBar.classList.add('d-none');

        // Customer Cart is VISIBLE
        cartBtn.classList.remove('d-none');

        // Reward points badge
        rewardPill.classList.remove('d-none');
        rewardCount.textContent = state.currentUser.reward_points || 0;
        document.getElementById('dropdownUserEmail').textContent = state.currentUser.email;
        document.getElementById('dropdownPointsVal').textContent = state.currentUser.reward_points || 0;
    }

    updateCartBadge();
}

function toggleUserDropdown() {
    const dropdown = document.getElementById('userDropdown');
    dropdown.classList.toggle('show');
}

// Close dropdown on clicking outside
document.addEventListener('click', (e) => {
    const userMenu = document.querySelector('.user-menu-container');
    const dropdown = document.getElementById('userDropdown');
    if (userMenu && !userMenu.contains(e.target)) {
        dropdown.classList.remove('show');
    }
});

function openAuthModal(tab = 'login') {
    document.getElementById('userDropdown').classList.remove('show');
    document.getElementById('authModal').classList.remove('d-none');
    switchAuthTab(tab);
}

function closeAuthModal() {
    document.getElementById('authModal').classList.add('d-none');
}

function switchAuthTab(tab) {
    const loginTab = document.getElementById('authTabLogin');
    const regTab = document.getElementById('authTabRegister');
    const loginForm = document.getElementById('loginForm');
    const regForm = document.getElementById('registerForm');
    const modalTitle = document.getElementById('authModalTitle');

    if (tab === 'login') {
        loginTab.classList.add('active');
        regTab.classList.remove('active');
        loginForm.classList.remove('d-none');
        regForm.classList.add('d-none');
        modalTitle.textContent = 'Welcome Back to ManChi\'s';
    } else {
        regTab.classList.add('active');
        loginTab.classList.remove('active');
        regForm.classList.remove('d-none');
        loginForm.classList.add('d-none');
        modalTitle.textContent = 'Join the ManChi\'s Club';
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (data.success) {
            state.currentUser = data.user;
            closeAuthModal();
            updateUserUI();
            showToast(data.message, 'success');
            if (state.currentUser.role === 'admin') {
                navigateTo('admin');
            }
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Login failed. Please try again.', 'error');
    }
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (data.success) {
            state.currentUser = data.user;
            closeAuthModal();
            updateUserUI();
            showToast(data.message, 'success');
        } else {
            showToast(data.message, 'error');
        }
    } catch (err) {
        showToast('Registration failed.', 'error');
    }
}

async function logoutUser() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        state.currentUser = null;
        updateUserUI();
        navigateTo('home');
        showToast('You have been logged out.', 'info');
    } catch (e) {
        console.error('Logout error:', e);
    }
}

// -------------------------------------------------------------
// Data Fetching & Store Catalog
// -------------------------------------------------------------
async function loadStoreData() {
    await Promise.all([
        fetchProducts(),
        fetchCombos(),
        fetchCoupons()
    ]);
    renderHomeView();
    renderShopView();
    renderCombosView();
}

async function fetchProducts() {
    try {
        const res = await fetch('/api/products');
        const data = await res.json();
        if (data.success) {
            state.allProducts = data.products;
        }
    } catch (e) {
        console.error('Error fetching products:', e);
    }
}

async function fetchCombos() {
    try {
        const res = await fetch('/api/combos');
        const data = await res.json();
        if (data.success) {
            state.allCombos = data.combos;
        }
    } catch (e) {
        console.error('Error fetching combos:', e);
    }
}

async function fetchCoupons() {
    try {
        const res = await fetch('/api/coupons');
        const data = await res.json();
        if (data.success) {
            state.allCoupons = data.coupons;
            renderCouponTicker();
            renderHomeCoupons();
        }
    } catch (e) {
        console.error('Error fetching coupons:', e);
    }
}

// -------------------------------------------------------------
// View Navigation
// -------------------------------------------------------------
function navigateTo(viewName) {
    state.activeView = viewName;
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('#mainNavMenu .nav-link').forEach(link => link.classList.remove('active'));

    const targetSection = document.getElementById(`${viewName}View`);
    if (targetSection) {
        targetSection.classList.add('active');
    }

    if (viewName === 'home') {
        renderHomeView();
    } else if (viewName === 'shop') {
        renderShopView();
    } else if (viewName === 'combos') {
        renderCombosView();
    } else if (viewName === 'orders') {
        if (!state.currentUser) {
            openAuthModal('login');
            showToast('Please login to view your order history.', 'info');
            return;
        }
        loadUserOrders();
    } else if (viewName === 'admin') {
        if (!state.currentUser || state.currentUser.role !== 'admin') {
            showToast('Access denied. Administrator privileges required.', 'error');
            navigateTo('home');
            return;
        }
        loadAdminDashboard();
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function scrollToAbout() {
    navigateTo('home');
    setTimeout(() => {
        const aboutEl = document.getElementById('aboutSection');
        if (aboutEl) aboutEl.scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

function scrollToDeals() {
    navigateTo('home');
    setTimeout(() => {
        const dealsEl = document.getElementById('dealTypesSection');
        if (dealsEl) dealsEl.scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

// -------------------------------------------------------------
// Requirement 1 & 5: DEAL TYPES & COMPACT PRODUCT CARD RENDERING
// -------------------------------------------------------------
function renderProductCard(p) {
    const origPrice = p.original_price || p.price;
    const discountPct = origPrice > p.price ? Math.round(((origPrice - p.price) / origPrice) * 100) : 0;

    let stockClass = 'in-stock';
    let stockText = 'In Stock';
    if (p.stock <= 0) {
        stockClass = 'out-stock';
        stockText = 'Out of Stock';
    } else if (p.stock <= 5) {
        stockClass = 'low-stock';
        stockText = `Only ${p.stock} left`;
    }

    return `
        <div class="product-card" data-id="${p.id}">
            <div class="product-img-wrapper" onclick="openProductQuickView(${p.id})">
                <img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" class="product-img" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&auto=format&fit=crop&q=80'">
                <div class="product-badges">
                    <span class="badge-deal">${escapeHtml(p.deal_type || 'Special')}</span>
                    <span class="badge-category">${escapeHtml(p.category)}</span>
                </div>
                <button class="product-quickview-btn" title="Quick View" onclick="event.stopPropagation(); openProductQuickView(${p.id})">
                    <i class="fa-solid fa-eye"></i>
                </button>
            </div>
            <div class="product-card-body">
                <h4 class="product-name" title="${escapeHtml(p.name)}" onclick="openProductQuickView(${p.id})">${escapeHtml(p.name)}</h4>
                <div class="product-meta-row">
                    <span class="product-rating"><i class="fa-solid fa-star"></i> ${p.rating || 4.7}</span>
                    <span class="product-stock-tag ${stockClass}"><i class="fa-solid fa-circle-check"></i> ${stockText}</span>
                </div>
                <div class="product-delivery-note">
                    <i class="fa-solid fa-truck-fast"></i> ${escapeHtml(p.delivery_info || 'Free delivery in 3-5 days')}
                </div>
                <div class="product-price-row">
                    <span class="price-current">₹${p.price.toFixed(2)}</span>
                    ${origPrice > p.price ? `<span class="price-original">₹${origPrice.toFixed(2)}</span>` : ''}
                    ${discountPct > 0 ? `<span class="price-discount-pill">${discountPct}% OFF</span>` : ''}
                </div>
                ${state.currentUser && state.currentUser.role === 'admin' ? `
                    <button class="btn btn-outline btn-sm w-100" onclick="openEditProductModal(${p.id})">
                        <i class="fa-solid fa-pen-to-square"></i> Edit in Admin
                    </button>
                ` : `
                    <button class="btn-add-cart" onclick="addToCart(${p.id})">
                        <i class="fa-solid fa-bag-shopping"></i> Add to Bag
                    </button>
                `}
            </div>
        </div>
    `;
}

function renderHomeView() {
    // Render Deal Types tabbed products
    renderHomeDeals();
    // Render Combos on Home
    renderHomeCombos();
}

function selectDealTypeTab(dealType) {
    state.selectedHomeDealType = dealType;
    document.querySelectorAll('.deal-pill').forEach(pill => pill.classList.remove('active'));
    event.currentTarget.classList.add('active');
    renderHomeDeals();
}

function renderHomeDeals() {
    const container = document.getElementById('homeDealsGrid');
    if (!container) return;

    let filtered = state.allProducts;
    if (state.selectedHomeDealType !== 'all') {
        filtered = filtered.filter(p => p.deal_type === state.selectedHomeDealType);
    }

    if (filtered.length === 0) {
        container.innerHTML = `<div class="col-12 text-center py-5 text-muted"><p>No items found under '${state.selectedHomeDealType}' deal type.</p></div>`;
        return;
    }

    // Display top 8 compact items
    container.innerHTML = filtered.slice(0, 8).map(p => renderProductCard(p)).join('');
}

function renderHomeCombos() {
    const container = document.getElementById('homeCombosGrid');
    if (!container) return;
    container.innerHTML = state.allCombos.slice(0, 2).map(c => renderComboCard(c)).join('');
}

function renderComboCard(c) {
    const discountPct = c.original_price > c.price ? Math.round(((c.original_price - c.price) / c.original_price) * 100) : 0;
    return `
        <div class="combo-card">
            <div class="combo-img-wrap">
                <img src="${escapeHtml(c.image_url)}" alt="${escapeHtml(c.name)}" class="combo-img" loading="lazy">
                <div class="product-badges">
                    <span class="badge-deal"><i class="fa-solid fa-layer-group"></i> Combo Deal</span>
                </div>
            </div>
            <div class="combo-body">
                <h4 class="combo-title">${escapeHtml(c.name)}</h4>
                <div class="combo-included-box">
                    <b>Includes:</b> ${escapeHtml(c.items_included)}
                </div>
                <p class="combo-desc">${escapeHtml(c.description || '')}</p>
                <div class="product-price-row mt-auto">
                    <span class="price-current">₹${c.price.toFixed(2)}</span>
                    <span class="price-original">₹${c.original_price.toFixed(2)}</span>
                    <span class="price-discount-pill">${discountPct}% SAVE</span>
                </div>
                ${state.currentUser && state.currentUser.role === 'admin' ? `
                    <button class="btn btn-outline btn-sm mt-2" onclick="navigateTo('admin'); switchAdminTab('combos');">
                        <i class="fa-solid fa-gear"></i> Manage in Admin
                    </button>
                ` : `
                    <button class="btn btn-primary btn-sm mt-2" onclick="addComboToCart(${c.id})">
                        <i class="fa-solid fa-cart-plus"></i> Add Combo to Bag
                    </button>
                `}
            </div>
        </div>
    `;
}

// -------------------------------------------------------------
// Requirement 2: COUPONS & REWARDS
// -------------------------------------------------------------
function renderCouponTicker() {
    const container = document.getElementById('tickerItemsContainer');
    if (!container) return;
    container.innerHTML = state.allCoupons.map(cp => `
        <span class="ticker-coupon" onclick="copyCouponCode('${cp.code}')" title="Click to copy code">
            <b>${cp.code}</b>: ${escapeHtml(cp.description || `${cp.discount_value}${cp.discount_type === 'percentage' ? '%' : '₹'} OFF`)}
        </span>
    `).join('');
}

function renderHomeCoupons() {
    const container = document.getElementById('homeCouponsGrid');
    if (!container) return;
    container.innerHTML = state.allCoupons.map(cp => `
        <div class="coupon-card">
            <div>
                <div class="coupon-badge-strip">
                    <span class="badge-deal">${cp.discount_type === 'percentage' ? `${cp.discount_value}% OFF` : `₹${cp.discount_value} OFF`}</span>
                    <span class="small text-muted"><i class="fa-solid fa-calendar"></i> Exp: ${cp.expiry_date || 'Ongoing'}</span>
                </div>
                <div class="coupon-code-chip my-2">${cp.code}</div>
                <h5 class="coupon-val-text">${escapeHtml(cp.description || 'Special Store Discount')}</h5>
                <p class="coupon-terms">
                    ${cp.min_order_amount > 0 ? `Min Order: ₹${cp.min_order_amount}` : 'No minimum order required'}<br/>
                    ${cp.max_discount > 0 ? `Max Discount: ₹${cp.max_discount}` : 'No maximum limit'}
                </p>
            </div>
            <button class="coupon-copy-btn" onclick="copyCouponCode('${cp.code}')">
                <i class="fa-regular fa-copy"></i> Copy Code
            </button>
        </div>
    `).join('');
}

function copyCouponCode(code) {
    navigator.clipboard.writeText(code).then(() => {
        showToast(`Coupon code '${code}' copied to clipboard!`, 'success');
    }).catch(() => {
        showToast(`Coupon: ${code}`, 'info');
    });
}

// -------------------------------------------------------------
// Shop Catalog Filtering & Sorting
// -------------------------------------------------------------
function renderShopView() {
    applyShopFilters();
}

function filterByCategory(category) {
    navigateTo('shop');
    const catSelect = document.getElementById('filterCategory');
    if (catSelect) catSelect.value = category;
    applyShopFilters();
}

function filterByDealType(dealType) {
    navigateTo('shop');
    const dealSelect = document.getElementById('filterDealType');
    if (dealSelect) dealSelect.value = dealType;
    applyShopFilters();
}

function applyShopFilters() {
    const catVal = document.getElementById('filterCategory').value;
    const dealVal = document.getElementById('filterDealType').value;
    const sortVal = document.getElementById('filterSort').value;
    const searchVal = document.getElementById('globalSearchInput').value.trim().toLowerCase();

    let filtered = [...state.allProducts];

    if (catVal !== 'all') {
        filtered = filtered.filter(p => p.category === catVal);
    }
    if (dealVal !== 'all') {
        filtered = filtered.filter(p => p.deal_type === dealVal);
    }
    if (searchVal) {
        filtered = filtered.filter(p => p.name.toLowerCase().includes(searchVal) || (p.description && p.description.toLowerCase().includes(searchVal)));
    }

    if (sortVal === 'price-low') {
        filtered.sort((a, b) => a.price - b.price);
    } else if (sortVal === 'price-high') {
        filtered.sort((a, b) => b.price - a.price);
    } else if (sortVal === 'rating') {
        filtered.sort((a, b) => (b.rating || 0) - (a.rating || 0));
    } else {
        filtered.sort((a, b) => b.id - a.id);
    }

    const grid = document.getElementById('shopProductGrid');
    const countEl = document.getElementById('shopResultsCount');
    const titleEl = document.getElementById('shopCatalogTitle');

    titleEl.textContent = catVal !== 'all' ? `${catVal} Collection` : (dealVal !== 'all' ? `${dealVal} Deals` : 'All Collections');
    countEl.textContent = `Showing ${filtered.length} products`;

    if (filtered.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-5">
                <i class="fa-solid fa-magnifying-glass fa-3x text-muted mb-3"></i>
                <h4>No matching products found</h4>
                <p class="text-muted">Try clearing your filters or search keywords.</p>
                <button class="btn btn-outline" onclick="resetShopFilters()">Reset All Filters</button>
            </div>
        `;
    } else {
        grid.innerHTML = filtered.map(p => renderProductCard(p)).join('');
    }
}

function resetShopFilters() {
    document.getElementById('filterCategory').value = 'all';
    document.getElementById('filterDealType').value = 'all';
    document.getElementById('filterSort').value = 'newest';
    document.getElementById('globalSearchInput').value = '';
    applyShopFilters();
}

function handleSearch(e) {
    if (e.key === 'Enter') {
        executeSearch();
    }
}

function executeSearch() {
    navigateTo('shop');
    applyShopFilters();
}

function renderCombosView() {
    const container = document.getElementById('catalogCombosGrid');
    if (!container) return;
    container.innerHTML = state.allCombos.map(c => renderComboCard(c)).join('');
}

// -------------------------------------------------------------
// Shopping Cart Operations (Customer Only)
// -------------------------------------------------------------
function loadLocalCart() {
    try {
        const stored = localStorage.getItem('manchis_cart');
        if (stored) {
            state.cart = JSON.parse(stored);
        }
    } catch (e) {
        state.cart = [];
    }
    updateCartBadge();
}

function saveLocalCart() {
    localStorage.setItem('manchis_cart', JSON.stringify(state.cart));
    updateCartBadge();
}

function addToCart(productId) {
    if (state.currentUser && state.currentUser.role === 'admin') {
        showToast('Admins cannot add items to cart. Please log in as a customer.', 'warning');
        return;
    }
    const product = state.allProducts.find(p => p.id === productId);
    if (!product) return;

    if (product.stock <= 0) {
        showToast('Sorry, this product is currently out of stock.', 'error');
        return;
    }

    const existing = state.cart.find(item => item.id === productId && !item.is_combo);
    if (existing) {
        if (existing.quantity >= product.stock) {
            showToast(`Maximum available stock (${product.stock}) reached for this item.`, 'warning');
            return;
        }
        existing.quantity += 1;
    } else {
        state.cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            original_price: product.original_price,
            image_url: product.image_url,
            quantity: 1,
            is_combo: false
        });
    }

    saveLocalCart();
    showToast(`Added "${product.name}" to shopping bag!`, 'success');
    renderCartDrawer();
}

function addComboToCart(comboId) {
    if (state.currentUser && state.currentUser.role === 'admin') {
        showToast('Admins cannot add items to cart.', 'warning');
        return;
    }
    const combo = state.allCombos.find(c => c.id === comboId);
    if (!combo) return;

    const existing = state.cart.find(item => item.id === comboId && item.is_combo);
    if (existing) {
        existing.quantity += 1;
    } else {
        state.cart.push({
            id: combo.id,
            name: combo.name,
            price: combo.price,
            original_price: combo.original_price,
            image_url: combo.image_url,
            quantity: 1,
            is_combo: true
        });
    }

    saveLocalCart();
    showToast(`Combo "${combo.name}" added to bag!`, 'success');
    renderCartDrawer();
}

function updateCartBadge() {
    const badge = document.getElementById('cartCountBadge');
    if (!badge) return;
    const totalCount = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    badge.textContent = totalCount;
}

function toggleCartDrawer() {
    if (state.currentUser && state.currentUser.role === 'admin') {
        return; // Disabled for admin
    }
    const drawer = document.getElementById('cartDrawer');
    const backdrop = document.getElementById('cartBackdrop');
    drawer.classList.toggle('open');
    backdrop.classList.toggle('show');
    if (drawer.classList.contains('open')) {
        renderCartDrawer();
    }
}

function closeCartDrawer() {
    const drawer = document.getElementById('cartDrawer');
    const backdrop = document.getElementById('cartBackdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('show');
}

function renderCartDrawer() {
    const body = document.getElementById('cartDrawerBody');
    const footer = document.getElementById('cartDrawerFooter');
    const countEl = document.getElementById('drawerCartCount');
    const subtotalEl = document.getElementById('drawerSubtotalVal');
    const earnPointsEl = document.getElementById('drawerEarnPointsVal');

    const totalCount = state.cart.reduce((sum, item) => sum + item.quantity, 0);
    countEl.textContent = totalCount;

    if (state.cart.length === 0) {
        body.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="fa-solid fa-bag-shopping fa-3x mb-3 text-muted"></i>
                <h5>Your shopping bag is empty</h5>
                <p class="small">Explore our festive and ethnic styles today!</p>
                <button class="btn btn-outline btn-sm mt-2" onclick="closeCartDrawer(); navigateTo('shop');">
                    Start Shopping
                </button>
            </div>
        `;
        footer.classList.add('d-none');
        return;
    }

    footer.classList.remove('d-none');
    let subtotal = 0;

    body.innerHTML = state.cart.map((item, index) => {
        const itemTotal = item.price * item.quantity;
        subtotal += itemTotal;
        return `
            <div class="cart-item-card">
                <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.name)}" class="cart-item-img">
                <div class="cart-item-info">
                    <h5 class="cart-item-title">${escapeHtml(item.name)}</h5>
                    <div class="cart-item-price">₹${item.price.toFixed(2)}</div>
                    <div class="d-flex align-items-center justify-content-between mt-2">
                        <div class="qty-control">
                            <button class="qty-btn" onclick="updateItemQuantity(${index}, -1)">-</button>
                            <span class="qty-val">${item.quantity}</span>
                            <button class="qty-btn" onclick="updateItemQuantity(${index}, 1)">+</button>
                        </div>
                        <button class="text-danger border-0 bg-transparent small cursor-pointer" onclick="removeItemFromCart(${index})">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
    earnPointsEl.textContent = `+${Math.max(1, Math.round(subtotal * 0.05))} pts`;
}

function updateItemQuantity(index, delta) {
    if (!state.cart[index]) return;
    state.cart[index].quantity += delta;
    if (state.cart[index].quantity <= 0) {
        state.cart.splice(index, 1);
    }
    saveLocalCart();
    renderCartDrawer();
}

function removeItemFromCart(index) {
    state.cart.splice(index, 1);
    saveLocalCart();
    renderCartDrawer();
}

// -------------------------------------------------------------
// Checkout Modal & Calculation Logic
// -------------------------------------------------------------
function openCheckoutModal() {
    closeCartDrawer();

    if (!state.currentUser) {
        openAuthModal('login');
        showToast('Please sign in or create an account to proceed with checkout.', 'info');
        return;
    }

    if (state.cart.length === 0) {
        showToast('Your cart is empty.', 'warning');
        return;
    }

    // Pre-populate user details
    document.getElementById('checkoutName').value = state.currentUser.name || '';
    document.getElementById('checkoutEmail').value = state.currentUser.email || '';
    document.getElementById('checkoutAvailablePoints').textContent = state.currentUser.reward_points || 0;

    // Reset coupon & rewards state
    state.appliedCoupon = null;
    state.useRewardPoints = false;
    document.getElementById('checkoutCouponInput').value = '';
    document.getElementById('checkoutCouponInput').disabled = false;
    document.getElementById('applyCouponBtn').classList.remove('d-none');
    document.getElementById('removeCouponBtn').classList.add('d-none');
    document.getElementById('couponFeedback').textContent = '';
    document.getElementById('useRewardsCheckbox').checked = false;

    renderCheckoutSummary();
    document.getElementById('checkoutModal').classList.remove('d-none');
}

function closeCheckoutModal() {
    document.getElementById('checkoutModal').classList.add('d-none');
}

function renderCheckoutSummary() {
    const itemsList = document.getElementById('checkoutItemsList');
    let subtotal = 0;

    itemsList.innerHTML = state.cart.map(item => {
        const itemTotal = item.price * item.quantity;
        subtotal += itemTotal;
        return `
            <div class="d-flex justify-content-between small mb-1">
                <span class="text-truncate" style="max-width: 180px;">${escapeHtml(item.name)} x ${item.quantity}</span>
                <b>₹${itemTotal.toFixed(2)}</b>
            </div>
        `;
    }).join('');

    let discount = 0;
    if (state.appliedCoupon) {
        discount = state.appliedCoupon.discount;
    }

    let pointsRedeemed = 0;
    const availablePoints = state.currentUser ? (state.currentUser.reward_points || 0) : 0;
    const remainingBeforePoints = Math.max(0, subtotal - discount);

    if (state.useRewardPoints && availablePoints > 0) {
        pointsRedeemed = Math.min(availablePoints, remainingBeforePoints);
    }

    const finalTotal = Math.max(0, subtotal - discount - pointsRedeemed);
    const earnedPoints = Math.max(1, Math.round(finalTotal * 0.05));

    // Update Breakdown elements
    document.getElementById('calcSubtotal').textContent = `₹${subtotal.toFixed(2)}`;

    const couponLine = document.getElementById('calcCouponLine');
    if (discount > 0 && state.appliedCoupon) {
        couponLine.style.display = 'flex';
        document.getElementById('appliedCouponCode').textContent = state.appliedCoupon.coupon_code;
        document.getElementById('calcDiscount').textContent = `- ₹${discount.toFixed(2)}`;
    } else {
        couponLine.style.display = 'none';
    }

    const pointsLine = document.getElementById('calcPointsLine');
    if (pointsRedeemed > 0) {
        pointsLine.style.display = 'flex';
        document.getElementById('calcPointsDiscount').textContent = `- ₹${pointsRedeemed.toFixed(2)}`;
    } else {
        pointsLine.style.display = 'none';
    }

    document.getElementById('calcFinalTotal').textContent = `₹${finalTotal.toFixed(2)}`;
    document.getElementById('calcEarnedPoints').textContent = earnedPoints;
}

async function handleApplyCoupon() {
    const codeInput = document.getElementById('checkoutCouponInput');
    const feedback = document.getElementById('couponFeedback');
    const code = codeInput.value.trim().toUpperCase();

    if (!code) {
        feedback.innerHTML = '<span class="text-danger">Please enter a coupon code.</span>';
        return;
    }

    const subtotal = state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

    try {
        const res = await fetch('/api/coupons/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, subtotal })
        });
        const data = await res.json();

        if (data.success) {
            state.appliedCoupon = data;
            codeInput.disabled = true;
            document.getElementById('applyCouponBtn').classList.add('d-none');
            document.getElementById('removeCouponBtn').classList.remove('d-none');
            feedback.innerHTML = `<span class="text-success"><i class="fa-solid fa-check"></i> ${data.message} Saved ₹${data.discount.toFixed(2)}</span>`;
            renderCheckoutSummary();
        } else {
            feedback.innerHTML = `<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i> ${data.message}</span>`;
        }
    } catch (e) {
        feedback.innerHTML = '<span class="text-danger">Error validating coupon.</span>';
    }
}

function handleRemoveCoupon() {
    state.appliedCoupon = null;
    const codeInput = document.getElementById('checkoutCouponInput');
    codeInput.value = '';
    codeInput.disabled = false;
    document.getElementById('applyCouponBtn').classList.remove('d-none');
    document.getElementById('removeCouponBtn').classList.add('d-none');
    document.getElementById('couponFeedback').innerHTML = '<span class="text-muted">Coupon removed.</span>';
    renderCheckoutSummary();
}

function handleToggleRewards() {
    const chk = document.getElementById('useRewardsCheckbox');
    state.useRewardPoints = chk.checked;
    const feedback = document.getElementById('rewardsFeedback');

    if (state.useRewardPoints) {
        feedback.classList.remove('d-none');
        feedback.textContent = `Applying available reward points discount.`;
    } else {
        feedback.classList.add('d-none');
    }
    renderCheckoutSummary();
}

async function submitOrder() {
    const name = document.getElementById('checkoutName').value.trim();
    const email = document.getElementById('checkoutEmail').value.trim();
    const phone = document.getElementById('checkoutPhone').value.trim();
    const address = document.getElementById('checkoutAddress').value.trim();
    const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked').value;

    if (!name || !email || !address) {
        showToast('Please enter your complete shipping name, email, and address.', 'error');
        return;
    }

    // Condition for mobile number:
    // 1. Mobile number must be entered
    // 2. Cannot be greater than 10 or less than 10 digits
    if (!phone) {
        showToast('Mobile number is required to place your order.', 'error');
        const phoneInput = document.getElementById('checkoutPhone');
        if (phoneInput) phoneInput.focus();
        return;
    }

    const cleanPhone = phone.replace(/[\s\-]/g, '');
    if (!/^\d+$/.test(cleanPhone)) {
        showToast('Mobile number must contain digits only.', 'error');
        const phoneInput = document.getElementById('checkoutPhone');
        if (phoneInput) phoneInput.focus();
        return;
    }

    if (cleanPhone.length < 10) {
        showToast('Mobile number cannot be less than 10 digits.', 'error');
        const phoneInput = document.getElementById('checkoutPhone');
        if (phoneInput) phoneInput.focus();
        return;
    }

    if (cleanPhone.length > 10) {
        showToast('Mobile number cannot be greater than 10 digits.', 'error');
        const phoneInput = document.getElementById('checkoutPhone');
        if (phoneInput) phoneInput.focus();
        return;
    }

    const subtotal = state.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    let discount = state.appliedCoupon ? state.appliedCoupon.discount : 0;
    let pointsUsed = 0;
    if (state.useRewardPoints && state.currentUser) {
        pointsUsed = Math.min(state.currentUser.reward_points, Math.max(0, subtotal - discount));
    }

    const orderPayload = {
        customer_name: name,
        customer_email: email,
        customer_phone: cleanPhone,
        customer_address: address,
        items: state.cart,
        payment_method: paymentMethod,
        coupon_code: state.appliedCoupon ? state.appliedCoupon.coupon_code : '',
        points_used: pointsUsed
    };

    const placeBtn = document.getElementById('placeOrderBtn');
    placeBtn.disabled = true;
    placeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Order...';

    try {
        const res = await fetch('/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderPayload)
        });
        const data = await res.json();

        if (data.success) {
            // Update reward points
            if (state.currentUser) {
                state.currentUser.reward_points = data.new_reward_balance;
                updateUserUI();
            }

            // Clear Cart
            state.cart = [];
            saveLocalCart();
            closeCheckoutModal();

            showToast(`Order #${data.order_id} placed! You earned ${data.points_earned} reward points.`, 'success');

            // Open Tracking Modal directly to show the user their new order!
            setTimeout(() => {
                openTrackingModal(data.order_id);
            }, 600);
        } else {
            showToast(data.message || 'Failed to place order.', 'error');
        }
    } catch (e) {
        showToast('Server communication error placing order.', 'error');
    } finally {
        placeBtn.disabled = false;
        placeBtn.innerHTML = '<i class="fa-solid fa-lock"></i> Place Order Now';
    }
}

// -------------------------------------------------------------
// Requirement 4 & 8: ORDER TRACKING & LIVE PROGRESS TIMELINE
// -------------------------------------------------------------
const TRACKING_STAGES = [
    'Order Placed',
    'Order Confirmed',
    'Processing',
    'Packed',
    'Shipped',
    'Out for Delivery',
    'Delivered'
];

async function openTrackingModal(orderId) {
    state.currentTrackingOrderId = orderId;
    closeTrackOrderSearchModal();

    try {
        const res = await fetch(`/api/orders/${orderId}`);
        const data = await res.json();

        if (!data.success || !data.order) {
            showToast('Order not found.', 'error');
            return;
        }

        renderTrackingModalContent(data.order);
        document.getElementById('trackingModal').classList.remove('d-none');
    } catch (e) {
        showToast('Error loading tracking details.', 'error');
    }
}

function closeTrackingModal() {
    document.getElementById('trackingModal').classList.add('d-none');
    state.currentTrackingOrderId = null;
}

function renderTrackingModalContent(order) {
    document.getElementById('trackModalOrderId').textContent = `Order ID: ${order.order_id}`;
    document.getElementById('trackModalStatusBadge').textContent = order.status;
    document.getElementById('trackModalDate').textContent = `Placed on: ${order.order_date}`;
    document.getElementById('trackModalDeliveryDate').textContent = order.estimated_delivery_date;
    document.getElementById('trackModalAddress').innerHTML = `<i class="fa-solid fa-location-dot"></i> Ship To: ${escapeHtml(order.customer_name)}, ${escapeHtml(order.customer_address)}`;

    // Set Bill Download link with QR code
    document.getElementById('trackModalBillDownloadBtn').href = `/api/orders/${order.order_id}/bill`;

    // Set QR code preview image
    const qrImg = document.getElementById('trackModalQrImg');
    if (qrImg) {
        qrImg.src = `/api/orders/${order.order_id}/qrcode`;
    }

    // Render Visual Step Progress
    const stepsContainer = document.getElementById('trackingStepsContainer');
    const currentStatus = order.status;
    const currentStageIndex = TRACKING_STAGES.indexOf(currentStatus);

    if (currentStatus === 'Cancelled') {
        stepsContainer.innerHTML = `
            <div class="step-node active w-100">
                <div class="step-icon-circle bg-danger text-white border-danger"><i class="fa-solid fa-xmark"></i></div>
                <div class="step-label text-danger">Order Cancelled</div>
            </div>
        `;
    } else {
        stepsContainer.innerHTML = TRACKING_STAGES.map((stage, idx) => {
            let stateClass = '';
            let iconHtml = idx + 1;

            if (idx < currentStageIndex) {
                stateClass = 'completed';
                iconHtml = '<i class="fa-solid fa-check"></i>';
            } else if (idx === currentStageIndex) {
                stateClass = 'active';
                iconHtml = '<i class="fa-solid fa-circle-dot"></i>';
            }

            return `
                <div class="step-node ${stateClass}">
                    <div class="step-icon-circle">${iconHtml}</div>
                    <div class="step-label">${stage}</div>
                </div>
            `;
        }).join('');
    }

    // Render Milestone History
    const historyContainer = document.getElementById('trackingHistoryTimeline');
    if (order.tracking_history && order.tracking_history.length > 0) {
        historyContainer.innerHTML = order.tracking_history.map(h => `
            <div class="timeline-item">
                <div class="d-flex justify-content-between align-items-center">
                    <b>${escapeHtml(h.status)}</b>
                    <span class="small text-muted">${escapeHtml(h.status_time)}</span>
                </div>
                <p class="small text-muted mb-0">${escapeHtml(h.note || '')}</p>
            </div>
        `).join('');
    } else {
        historyContainer.innerHTML = `<p class="small text-muted">No milestone records yet.</p>`;
    }

    // Render Items Summary
    const itemsSummary = document.getElementById('trackModalItemsSummary');
    itemsSummary.innerHTML = order.items.map(it => `
        <div class="d-flex justify-content-between mb-1">
            <span>${escapeHtml(it.name)} x ${it.quantity}</span>
            <b>₹${(it.price * it.quantity).toFixed(2)}</b>
        </div>
    `).join('');

    document.getElementById('trackModalPaymentMethod').textContent = order.payment_method;
    document.getElementById('trackModalPointsEarned').textContent = `+${order.points_earned || 0} pts`;
    document.getElementById('trackModalFinalTotal').textContent = `₹${order.final_total.toFixed(2)}`;

    // Show Admin Status controls if logged in as Admin
    const adminControls = document.getElementById('adminTrackingControls');
    if (state.currentUser && state.currentUser.role === 'admin') {
        adminControls.classList.remove('d-none');
        document.getElementById('adminStatusSelector').value = order.status;
        document.getElementById('adminStatusNote').value = '';
    } else {
        adminControls.classList.add('d-none');
    }
}

async function submitAdminStatusUpdate() {
    const orderId = state.currentTrackingOrderId;
    if (!orderId) return;

    const newStatus = document.getElementById('adminStatusSelector').value;
    const note = document.getElementById('adminStatusNote').value.trim();

    try {
        const res = await fetch(`/api/admin/orders/${orderId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus, note })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            // Refresh tracking modal
            openTrackingModal(orderId);
            // Refresh admin orders table if open
            if (state.activeView === 'admin') {
                loadAdminOrders();
            }
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Error updating status.', 'error');
    }
}

// Track Order Search Modal
function openTrackOrderModal() {
    document.getElementById('trackOrderSearchModal').classList.remove('d-none');
    const recentOrdersContainer = document.getElementById('quickRecentOrdersList');

    if (state.currentUser) {
        fetch('/api/orders').then(r => r.json()).then(data => {
            if (data.success && data.orders.length > 0) {
                recentOrdersContainer.innerHTML = `
                    <h6 class="small fw-bold text-muted mb-2">Or select from your recent orders:</h6>
                    <div class="list-group">
                        ${data.orders.slice(0, 3).map(o => `
                            <button class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-2" onclick="openTrackingModal('${o.order_id}')">
                                <div>
                                    <b>#${o.order_id}</b>
                                    <div class="small text-muted">${o.order_date} • ${o.status}</div>
                                </div>
                                <span class="badge badge-deal">Track</span>
                            </button>
                        `).join('')}
                    </div>
                `;
            } else {
                recentOrdersContainer.innerHTML = '';
            }
        });
    } else {
        recentOrdersContainer.innerHTML = '';
    }
}

function closeTrackOrderSearchModal() {
    document.getElementById('trackOrderSearchModal').classList.add('d-none');
}

function searchAndTrackOrder() {
    const input = document.getElementById('trackOrderIdInput');
    const orderId = input.value.trim().toUpperCase();
    if (!orderId) {
        showToast('Please enter a valid Order ID.', 'warning');
        return;
    }
    openTrackingModal(orderId);
}

// -------------------------------------------------------------
// Customer Order History View
// -------------------------------------------------------------
async function loadUserOrders() {
    const container = document.getElementById('userOrdersList');
    container.innerHTML = '<div class="text-center py-5"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></div>';

    try {
        const res = await fetch('/api/orders');
        const data = await res.json();

        if (!data.success || data.orders.length === 0) {
            container.innerHTML = `
                <div class="card p-5 text-center bg-white border-0 shadow-sm">
                    <i class="fa-solid fa-box-open fa-3x text-muted mb-3"></i>
                    <h4>You have no orders yet</h4>
                    <p class="text-muted">Once you place an order, live tracking and QR code bills will appear here.</p>
                    <button class="btn btn-primary mt-2" onclick="navigateTo('shop')">Explore Catalog</button>
                </div>
            `;
            return;
        }

        container.innerHTML = data.orders.map(order => `
            <div class="order-card-box">
                <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-3">
                    <div>
                        <span class="badge badge-status">${escapeHtml(order.status)}</span>
                        <h4 class="mb-0 mt-1">#${escapeHtml(order.order_id)}</h4>
                        <span class="small text-muted">Placed on: ${escapeHtml(order.order_date)}</span>
                    </div>
                    <div class="text-md-end">
                        <h4 class="text-primary mb-0">₹${order.final_total.toFixed(2)}</h4>
                        <span class="small text-muted">${order.payment_method}</span>
                    </div>
                </div>

                <div class="row align-items-center py-2 bg-light rounded px-3 mb-3">
                    <div class="col-md-7">
                        <small class="text-muted"><b>Estimated Delivery:</b> <span class="text-primary fw-bold">${escapeHtml(order.estimated_delivery_date)}</span></small><br/>
                        <small class="text-muted"><b>Deliver to:</b> ${escapeHtml(order.customer_name)} - ${escapeHtml(order.customer_address)}</small>
                    </div>
                    <div class="col-md-5 text-md-end mt-2 mt-md-0">
                        <small class="text-success"><i class="fa-solid fa-coins"></i> Earned ${order.points_earned} reward pts</small>
                    </div>
                </div>

                <div class="order-items-preview mb-3">
                    <small class="fw-bold">Items Ordered (${order.items.length}):</small>
                    <div class="small text-muted mt-1">
                        ${order.items.map(it => `${escapeHtml(it.name)} (x${it.quantity})`).join(', ')}
                    </div>
                </div>

                <div class="d-flex justify-content-end gap-2">
                    <button class="btn btn-primary btn-sm" onclick="openTrackingModal('${order.order_id}')">
                        <i class="fa-solid fa-location-dot"></i> Track Order
                    </button>
                    <a href="/api/orders/${order.order_id}/bill" target="_blank" class="btn btn-outline btn-sm">
                        <i class="fa-solid fa-file-pdf text-danger"></i> Download Bill (with QR)
                    </a>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<div class="alert alert-danger">Error loading orders.</div>';
    }
}

// -------------------------------------------------------------
// Admin Dashboard Controller
// -------------------------------------------------------------
function switchAdminTab(tab) {
    document.querySelectorAll('.admin-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.admin-tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.admin-nav-link').forEach(l => l.classList.remove('active'));

    const tabBtn = document.getElementById(`tabBtn${capitalize(tab)}`);
    const tabPane = document.getElementById(`adminTabContent${capitalize(tab)}`);
    if (tabBtn) tabBtn.classList.add('active');
    if (tabPane) tabPane.classList.add('active');

    if (tab === 'products') loadAdminProducts();
    if (tab === 'combos') loadAdminCombos();
    if (tab === 'coupons') loadAdminCoupons();
    if (tab === 'orders') loadAdminOrders();
    if (tab === 'users') loadAdminUsers();
}

async function loadAdminDashboard() {
    loadAdminStats();
    switchAdminTab('products');
}

async function loadAdminStats() {
    try {
        const [ordersRes, productsRes, couponsRes] = await Promise.all([
            fetch('/api/admin/orders'),
            fetch('/api/products'),
            fetch('/api/coupons')
        ]);
        const ordersData = await ordersRes.json();
        const productsData = await productsRes.json();
        const couponsData = await couponsRes.json();

        if (ordersData.success) {
            const totalRevenue = ordersData.orders.reduce((sum, o) => sum + o.final_total, 0);
            document.getElementById('adminTotalOrdersCount').textContent = ordersData.orders.length;
            document.getElementById('adminTotalRevenueVal').textContent = `₹${totalRevenue.toFixed(2)}`;
        }
        if (productsData.success) {
            document.getElementById('adminActiveProductsCount').textContent = productsData.products.length;
        }
        if (couponsData.success) {
            document.getElementById('adminLiveCouponsCount').textContent = couponsData.coupons.length;
        }
    } catch (e) {
        console.error('Error loading admin stats:', e);
    }
}

// Admin Products CRUD
async function loadAdminProducts() {
    await fetchProducts();
    const tbody = document.getElementById('adminProductsTableBody');
    tbody.innerHTML = state.allProducts.map(p => `
        <tr>
            <td><img src="${escapeHtml(p.image_url)}" class="table-thumb" alt="${escapeHtml(p.name)}"></td>
            <td><b>${escapeHtml(p.name)}</b></td>
            <td><span class="badge bg-light text-dark border">${escapeHtml(p.category)}</span></td>
            <td><span class="badge badge-deal">${escapeHtml(p.deal_type)}</span></td>
            <td><b>₹${p.price.toFixed(2)}</b> <small class="text-muted"><del>₹${p.original_price.toFixed(2)}</del></small></td>
            <td>${p.stock}</td>
            <td><span class="badge ${p.status === 'In Stock' ? 'bg-success' : 'bg-warning'} text-white">${escapeHtml(p.status)}</span></td>
            <td><small>${escapeHtml(p.delivery_info || '-')}</small></td>
            <td>
                <div class="d-flex gap-1">
                    <button class="btn btn-outline btn-sm" onclick="openEditProductModal(${p.id})"><i class="fa-solid fa-pen"></i></button>
                    <button class="btn btn-outline-danger btn-sm" onclick="deleteProduct(${p.id})"><i class="fa-solid fa-trash"></i></button>
                </div>
            </td>
        </tr>
    `).join('');
}

function openAddProductModal() {
    document.getElementById('productAdminModalTitle').textContent = 'Add New Product';
    document.getElementById('adminProdId').value = '';
    document.getElementById('productAdminForm').reset();
    document.getElementById('productAdminModal').classList.remove('d-none');
}

function openEditProductModal(id) {
    const p = state.allProducts.find(item => item.id === id);
    if (!p) return;

    document.getElementById('productAdminModalTitle').textContent = 'Edit Product Details';
    document.getElementById('adminProdId').value = p.id;
    document.getElementById('adminProdName').value = p.name;
    document.getElementById('adminProdCategory').value = p.category;
    document.getElementById('adminProdDealType').value = p.deal_type || 'Regular';
    document.getElementById('adminProdPrice').value = p.price;
    document.getElementById('adminProdOrigPrice').value = p.original_price;
    document.getElementById('adminProdStock').value = p.stock;
    document.getElementById('adminProdStatus').value = p.status;
    document.getElementById('adminProdDelivery').value = p.delivery_info || '';
    document.getElementById('adminProdImage').value = p.image_url;
    document.getElementById('adminProdDesc').value = p.description || '';

    document.getElementById('productAdminModal').classList.remove('d-none');
}

function closeProductAdminModal() {
    document.getElementById('productAdminModal').classList.add('d-none');
}

async function handleProductFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('adminProdId').value;
    const payload = {
        name: document.getElementById('adminProdName').value.trim(),
        category: document.getElementById('adminProdCategory').value,
        deal_type: document.getElementById('adminProdDealType').value,
        price: parseFloat(document.getElementById('adminProdPrice').value),
        original_price: parseFloat(document.getElementById('adminProdOrigPrice').value),
        stock: parseInt(document.getElementById('adminProdStock').value),
        status: document.getElementById('adminProdStatus').value,
        delivery_info: document.getElementById('adminProdDelivery').value.trim(),
        image_url: document.getElementById('adminProdImage').value.trim(),
        description: document.getElementById('adminProdDesc').value.trim()
    };

    const url = id ? `/api/admin/products/${id}` : '/api/admin/products';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            closeProductAdminModal();
            await fetchProducts();
            loadAdminProducts();
            renderShopView();
            renderHomeView();
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Error saving product.', 'error');
    }
}

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;
    try {
        const res = await fetch(`/api/admin/products/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            await fetchProducts();
            loadAdminProducts();
            renderShopView();
            renderHomeView();
        }
    } catch (e) {
        showToast('Error deleting product.', 'error');
    }
}

// Admin Combos
async function loadAdminCombos() {
    await fetchCombos();
    const tbody = document.getElementById('adminCombosTableBody');
    tbody.innerHTML = state.allCombos.map(c => `
        <tr>
            <td><img src="${escapeHtml(c.image_url)}" class="table-thumb" alt="${escapeHtml(c.name)}"></td>
            <td><b>${escapeHtml(c.name)}</b></td>
            <td><small>${escapeHtml(c.items_included)}</small></td>
            <td><b>₹${c.price.toFixed(2)}</b> <small class="text-muted"><del>₹${c.original_price.toFixed(2)}</del></small></td>
            <td>${c.stock}</td>
            <td><span class="badge badge-deal">${escapeHtml(c.deal_type)}</span></td>
            <td>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteCombo(${c.id})"><i class="fa-solid fa-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

function openAddComboModal() {
    document.getElementById('comboAdminForm').reset();
    document.getElementById('comboAdminModal').classList.remove('d-none');
}

function closeComboAdminModal() {
    document.getElementById('comboAdminModal').classList.add('d-none');
}

async function handleComboFormSubmit(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('adminComboName').value.trim(),
        items_included: document.getElementById('adminComboItems').value.trim(),
        price: parseFloat(document.getElementById('adminComboPrice').value),
        original_price: parseFloat(document.getElementById('adminComboOrigPrice').value),
        image_url: document.getElementById('adminComboImage').value.trim(),
        description: document.getElementById('adminComboDesc').value.trim(),
        stock: 15
    };

    try {
        const res = await fetch('/api/admin/combos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            closeComboAdminModal();
            await fetchCombos();
            loadAdminCombos();
            renderHomeCombos();
            renderCombosView();
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Error saving combo.', 'error');
    }
}

async function deleteCombo(id) {
    if (!confirm('Are you sure you want to delete this combo?')) return;
    try {
        const res = await fetch(`/api/admin/combos/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            await fetchCombos();
            loadAdminCombos();
            renderHomeCombos();
            renderCombosView();
        }
    } catch (e) {
        showToast('Error deleting combo.', 'error');
    }
}

// Admin Coupons CRUD
async function loadAdminCoupons() {
    try {
        const res = await fetch('/api/admin/coupons');
        const data = await res.json();
        if (data.success) {
            const tbody = document.getElementById('adminCouponsTableBody');
            tbody.innerHTML = data.coupons.map(cp => `
                <tr>
                    <td><span class="coupon-code-chip">${cp.code}</span></td>
                    <td>${cp.discount_type === 'percentage' ? 'Percentage' : 'Fixed ₹'}</td>
                    <td><b>${cp.discount_type === 'percentage' ? `${cp.discount_value}%` : `₹${cp.discount_value}`}</b></td>
                    <td>₹${cp.min_order_amount}</td>
                    <td>${cp.max_discount > 0 ? `₹${cp.max_discount}` : 'No Cap'}</td>
                    <td>${cp.expiry_date || 'No Expiry'}</td>
                    <td><span class="badge ${cp.active ? 'bg-success' : 'bg-secondary'} text-white">${cp.active ? 'Active' : 'Inactive'}</span></td>
                    <td><small>${escapeHtml(cp.description || '-')}</small></td>
                    <td>
                        <div class="d-flex gap-1">
                            <button class="btn btn-outline btn-sm" onclick="openEditCouponModal(${JSON.stringify(cp).replace(/"/g, '&quot;')})"><i class="fa-solid fa-pen"></i></button>
                            <button class="btn btn-outline-danger btn-sm" onclick="deleteCoupon(${cp.id})"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading coupons:', e);
    }
}

function openAddCouponModal() {
    document.getElementById('couponAdminModalTitle').textContent = 'Create New Coupon';
    document.getElementById('adminCouponId').value = '';
    document.getElementById('couponAdminForm').reset();
    document.getElementById('couponAdminModal').classList.remove('d-none');
}

function openEditCouponModal(cp) {
    document.getElementById('couponAdminModalTitle').textContent = 'Edit Discount Coupon';
    document.getElementById('adminCouponId').value = cp.id;
    document.getElementById('adminCouponCode').value = cp.code;
    document.getElementById('adminCouponType').value = cp.discount_type;
    document.getElementById('adminCouponValue').value = cp.discount_value;
    document.getElementById('adminCouponMin').value = cp.min_order_amount;
    document.getElementById('adminCouponMax').value = cp.max_discount;
    document.getElementById('adminCouponExpiry').value = cp.expiry_date || '';
    document.getElementById('adminCouponActive').value = cp.active;
    document.getElementById('adminCouponDesc').value = cp.description || '';

    document.getElementById('couponAdminModal').classList.remove('d-none');
}

function closeCouponAdminModal() {
    document.getElementById('couponAdminModal').classList.add('d-none');
}

async function handleCouponFormSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('adminCouponId').value;
    const payload = {
        code: document.getElementById('adminCouponCode').value.trim().toUpperCase(),
        discount_type: document.getElementById('adminCouponType').value,
        discount_value: parseFloat(document.getElementById('adminCouponValue').value),
        min_order_amount: parseFloat(document.getElementById('adminCouponMin').value || 0),
        max_discount: parseFloat(document.getElementById('adminCouponMax').value || 0),
        expiry_date: document.getElementById('adminCouponExpiry').value || null,
        active: parseInt(document.getElementById('adminCouponActive').value),
        description: document.getElementById('adminCouponDesc').value.trim()
    };

    const url = id ? `/api/admin/coupons/${id}` : '/api/admin/coupons';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            closeCouponAdminModal();
            loadAdminCoupons();
            fetchCoupons();
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Error saving coupon.', 'error');
    }
}

async function deleteCoupon(id) {
    if (!confirm('Are you sure you want to delete this coupon?')) return;
    try {
        const res = await fetch(`/api/admin/coupons/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            loadAdminCoupons();
            fetchCoupons();
        }
    } catch (e) {
        showToast('Error deleting coupon.', 'error');
    }
}

// Admin Orders & Tracking
async function loadAdminOrders() {
    try {
        const res = await fetch('/api/admin/orders');
        const data = await res.json();
        if (data.success) {
            const tbody = document.getElementById('adminOrdersTableBody');
            tbody.innerHTML = data.orders.map(o => `
                <tr>
                    <td><b>#${escapeHtml(o.order_id)}</b></td>
                    <td>
                        <b>${escapeHtml(o.customer_name)}</b><br/>
                        <small class="text-muted">${escapeHtml(o.customer_email)}</small>
                    </td>
                    <td><b class="text-primary">₹${o.final_total.toFixed(2)}</b></td>
                    <td><small>${escapeHtml(o.payment_method)}</small></td>
                    <td><small>${escapeHtml(o.order_date)}</small></td>
                    <td><b class="text-dark small">${escapeHtml(o.estimated_delivery_date)}</b></td>
                    <td><span class="badge badge-status">${escapeHtml(o.status)}</span></td>
                    <td>
                        <div class="d-flex gap-1">
                            <button class="btn btn-primary btn-sm" onclick="openTrackingModal('${o.order_id}')" title="Track & Update Status">
                                <i class="fa-solid fa-truck-fast"></i> Track & Update
                            </button>
                            <a href="/api/orders/${o.order_id}/bill" target="_blank" class="btn btn-outline btn-sm" title="Download QR Bill">
                                <i class="fa-solid fa-file-pdf text-danger"></i> Bill
                            </a>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading admin orders:', e);
    }
}

// Admin Users & Loyalty Points
async function loadAdminUsers() {
    try {
        const res = await fetch('/api/admin/users');
        const data = await res.json();
        if (data.success) {
            const tbody = document.getElementById('adminUsersTableBody');
            tbody.innerHTML = data.users.map(u => `
                <tr>
                    <td>${u.id}</td>
                    <td><b>${escapeHtml(u.name)}</b></td>
                    <td>${escapeHtml(u.email)}</td>
                    <td><span class="badge ${u.role === 'admin' ? 'bg-danger' : 'bg-primary'} text-white">${u.role.toUpperCase()}</span></td>
                    <td><b class="text-warning"><i class="fa-solid fa-coins"></i> ${u.reward_points} pts</b></td>
                    <td><small class="text-muted">${escapeHtml(u.created_at)}</small></td>
                </tr>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading users:', e);
    }
}

// -------------------------------------------------------------
// Product Quick View Modal
// -------------------------------------------------------------
function openProductQuickView(id) {
    const p = state.allProducts.find(item => item.id === id);
    if (!p) return;

    const modalBody = document.getElementById('quickViewModalBody');
    const origPrice = p.original_price || p.price;
    const discountPct = origPrice > p.price ? Math.round(((origPrice - p.price) / origPrice) * 100) : 0;

    modalBody.innerHTML = `
        <div class="row g-4">
            <div class="col-md-6">
                <div style="border-radius: 12px; overflow: hidden; background: #fafafa;">
                    <img src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" style="width: 100%; max-height: 380px; object-fit: cover;">
                </div>
            </div>
            <div class="col-md-6 d-flex flex-direction-column">
                <div class="mb-2">
                    <span class="badge badge-deal me-1">${escapeHtml(p.deal_type)}</span>
                    <span class="badge bg-light text-dark border">${escapeHtml(p.category)}</span>
                </div>
                <h3 class="mb-2">${escapeHtml(p.name)}</h3>
                <div class="d-flex align-items-center gap-3 mb-2 small text-muted">
                    <span class="text-warning"><i class="fa-solid fa-star"></i> ${p.rating || 4.7} Rating</span>
                    <span>•</span>
                    <span class="text-success"><i class="fa-solid fa-circle-check"></i> ${p.status} (${p.stock} in stock)</span>
                </div>
                <div class="product-price-row mb-3">
                    <span class="price-current" style="font-size: 1.6rem;">₹${p.price.toFixed(2)}</span>
                    ${origPrice > p.price ? `<span class="price-original" style="font-size: 1rem;">₹${origPrice.toFixed(2)}</span>` : ''}
                    ${discountPct > 0 ? `<span class="price-discount-pill">${discountPct}% OFF</span>` : ''}
                </div>
                <p class="text-muted small mb-3">${escapeHtml(p.description || 'Authentic designer wear handcrafted by artisanal masters.')}</p>
                <div class="p-2 rounded bg-light small mb-3">
                    <i class="fa-solid fa-truck-fast text-primary"></i> ${escapeHtml(p.delivery_info || 'Free delivery in 3-5 business days')}
                </div>
                ${state.currentUser && state.currentUser.role === 'admin' ? `
                    <button class="btn btn-outline mt-auto" onclick="closeQuickViewModal(); openEditProductModal(${p.id});">
                        <i class="fa-solid fa-pen"></i> Edit in Admin
                    </button>
                ` : `
                    <button class="btn btn-primary btn-lg mt-auto" onclick="addToCart(${p.id}); closeQuickViewModal();">
                        <i class="fa-solid fa-bag-shopping"></i> Add to Shopping Bag
                    </button>
                `}
            </div>
        </div>
    `;

    document.getElementById('productQuickViewModal').classList.remove('d-none');
}

function closeQuickViewModal() {
    document.getElementById('productQuickViewModal').classList.add('d-none');
}

// -------------------------------------------------------------
// Toast Notifications & Helpers
// -------------------------------------------------------------
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'fa-solid fa-circle-info text-primary';
    if (type === 'success') icon = 'fa-solid fa-circle-check text-success';
    if (type === 'error') icon = 'fa-solid fa-triangle-exclamation text-danger';
    if (type === 'warning') icon = 'fa-solid fa-bell text-warning';

    toast.innerHTML = `
        <i class="${icon}"></i>
        <div style="flex: 1;">${escapeHtml(message)}</div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function capitalize(s) {
    if (!s) return '';
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function setupEventListeners() {
    // Esc key closes modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAuthModal();
            closeCheckoutModal();
            closeTrackingModal();
            closeTrackOrderSearchModal();
            closeProductAdminModal();
            closeCouponAdminModal();
            closeComboAdminModal();
            closeQuickViewModal();
            closeCartDrawer();
        }
    });
}
