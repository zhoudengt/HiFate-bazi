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
                        <a href="daily-fortune-calendar.html" class="nav-submenu-item" data-page="daily-fortune-calendar">每日运势</a>
                        <a href="shengong-minggong.html" class="nav-submenu-item" data-page="shengong-minggong">身宫命宫</a>
                    </div>
                    <a href="pan.html" class="nav-item" data-page="pan">
                        <span class="nav-item-icon">📖</span>
                        <span class="nav-item-text">命书</span>
                    </a>
                    <div class="nav-submenu">
                        <a href="pan.html" class="nav-submenu-item" data-page="pan">基础八字排盘</a>
                        <a href="rizhu-liujiazi.html" class="nav-submenu-item" data-page="rizhu-liujiazi">日元-六十甲子</a>
                        <a href="wuxing-proportion.html" class="nav-submenu-item" data-page="wuxing-proportion">五行占比</a>
                        <a href="xishen-jishen.html" class="nav-submenu-item" data-page="xishen-jishen">八字命理-喜神与忌神</a>
                        <a href="marriage-analysis.html" class="nav-submenu-item" data-page="marriage-analysis">八字命理-感情婚姻</a>
                        <a href="career-wealth-analysis.html" class="nav-submenu-item" data-page="career-wealth-analysis">八字命理-事业财富</a>
                        <a href="children-study-analysis.html" class="nav-submenu-item" data-page="children-study-analysis">八字命理-子女学习</a>
                        <a href="health-analysis.html" class="nav-submenu-item" data-page="health-analysis">八字命理-身体健康</a>
                        <a href="general-review-analysis.html" class="nav-submenu-item" data-page="general-review-analysis">八字命理-总评</a>
                        <a href="ai-qa.html" class="nav-submenu-item" data-page="ai-qa">AI问答</a>
                    </div>
                    <a href="basic-info.html" class="nav-item" data-page="basic-info">
                        <span class="nav-item-icon">📋</span>
                        <span class="nav-item-text">基本信息</span>
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
                // 如果激活的是子菜单项，也激活父菜单项
                const parentNavItem = item.closest('.nav-submenu')?.previousElementSibling;
                if (parentNavItem && parentNavItem.classList.contains('nav-item')) {
                    parentNavItem.classList.add('active');
                }
            }
        });
        
        // 确保子菜单默认显示（如果当前页面是子菜单项，展开父菜单）
        if (currentPage === 'daily-fortune-calendar' || 
            currentPage === 'fortune' || 
            currentPage === 'year-report' || 
            currentPage === 'dayun-liunian' || 
            currentPage === 'shengong-minggong' ||
            currentPage === 'pan' ||
            currentPage === 'rizhu-liujiazi' ||
            currentPage === 'wuxing-proportion' ||
            currentPage === 'xishen-jishen' ||
        currentPage === 'marriage-analysis' ||
        currentPage === 'career-wealth-analysis' ||
        currentPage === 'children-study-analysis' ||
        currentPage === 'health-analysis' ||
        currentPage === 'general-review-analysis' ||
        currentPage === 'ai-qa') {
        const submenus = document.querySelectorAll('.nav-submenu');
            submenus.forEach(submenu => {
                if (submenu) {
                    submenu.style.display = 'block';
                }
            });
        }
    }

    getCurrentPage() {
        const path = window.location.pathname;
        const filename = path.split('/').pop() || 'index.html';
        
        if (filename.includes('basic-info')) return 'basic-info';
        if (filename.includes('rizhu-liujiazi')) return 'rizhu-liujiazi';
        if (filename.includes('pan')) return 'pan';
        if (filename.includes('shengong-minggong')) return 'shengong-minggong';
        if (filename.includes('daily-fortune-calendar')) return 'daily-fortune-calendar';
        if (filename.includes('fortune')) return 'dayun-liunian';
        if (filename.includes('yigua')) return 'yigua';
        if (filename.includes('dayun')) return 'dayun';
        if (filename.includes('liunian')) return 'liunian';
        if (filename.includes('wuxing-proportion')) return 'wuxing-proportion';
        if (filename.includes('xishen-jishen')) return 'xishen-jishen';
    if (filename.includes('marriage-analysis')) return 'marriage-analysis';
    if (filename.includes('career-wealth-analysis')) return 'career-wealth-analysis';
    if (filename.includes('children-study-analysis')) return 'children-study-analysis';
    if (filename.includes('health-analysis')) return 'health-analysis';
    if (filename.includes('general-review-analysis')) return 'general-review-analysis';
    if (filename.includes('ai-qa')) return 'ai-qa';
    return 'index';
    }
}

// 初始化侧边栏
document.addEventListener('DOMContentLoaded', () => {
    new Sidebar();
});

