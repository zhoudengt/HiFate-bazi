// 侧边栏导航组件
class Sidebar {
    constructor() {
        this.init();
    }

    init() {
        this.createSidebar();
        this.bindEvents();
    }

    createSidebar() {
        const sidebar = `
            <div class="sidebar" id="sidebar">
                <div class="sidebar-header">
                    <div class="sidebar-logo">F</div>
                    <div class="sidebar-logo-text">FATE TELL</div>
                </div>
                <nav class="sidebar-nav">
                    <a href="index.html" class="nav-item" data-page="index">
                        <span class="nav-item-icon">📊</span>
                        <span class="nav-item-text">运书</span>
                    </a>
                    <div class="nav-submenu">
                        <a href="fortune.html" class="nav-submenu-item" data-page="fortune">日运日签</a>
                        <a href="fortune.html" class="nav-submenu-item" data-page="year-report">2025乙巳年年运报告</a>
                        <a href="fortune.html" class="nav-submenu-item active" data-page="dayun-liunian">大运流年</a>
                    </div>
                    <a href="pan.html" class="nav-item" data-page="pan">
                        <span class="nav-item-icon">📖</span>
                        <span class="nav-item-text">命书</span>
                    </a>
                    <a href="yigua.html" class="nav-item" data-page="yigua">
                        <span class="nav-item-icon">💬</span>
                        <span class="nav-item-text">召唤</span>
                    </a>
                    <a href="#" class="nav-item" data-page="shop">
                        <span class="nav-item-icon">🛒</span>
                        <span class="nav-item-text">商店</span>
                    </a>
                    <a href="#" class="nav-item" data-page="profile">
                        <span class="nav-item-icon">👤</span>
                        <span class="nav-item-text">我的</span>
                    </a>
                </nav>
            </div>
        `;
        
        document.body.insertAdjacentHTML('afterbegin', sidebar);
    }

    bindEvents() {
        // 根据当前页面高亮导航项
        const currentPage = this.getCurrentPage();
        const navItems = document.querySelectorAll('.nav-item, .nav-submenu-item');
        navItems.forEach(item => {
            if (item.dataset.page === currentPage) {
                item.classList.add('active');
            }
        });
    }

    getCurrentPage() {
        const path = window.location.pathname;
        const filename = path.split('/').pop() || 'index.html';
        
        if (filename.includes('pan')) return 'pan';
        if (filename.includes('fortune')) return 'dayun-liunian';
        if (filename.includes('yigua')) return 'yigua';
        if (filename.includes('dayun')) return 'dayun';
        if (filename.includes('liunian')) return 'liunian';
        return 'index';
    }
}

// 初始化侧边栏
document.addEventListener('DOMContentLoaded', () => {
    new Sidebar();
});

