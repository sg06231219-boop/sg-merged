"""
SG电商建站平台 - 电商模板
包含3套主题模板和完整的电商前端交互JS
"""

# ==================== 三套主题配色 ====================
THEMES = {
    "tech_blue": {
        "name": "科技蓝",
        "primary": "#2563eb",
        "primary_dark": "#1d4ed8",
        "primary_light": "#eff6ff",
        "accent": "#3b82f6",
        "bg": "#f8fafc",
        "card_bg": "#ffffff",
        "text": "#1e293b",
        "text_secondary": "#64748b",
        "border": "#e2e8f0",
        "success": "#22c55e",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "gradient": "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
        "shadow": "0 4px 24px rgba(37,99,235,0.12)",
        "radius": "16px",
        "radius_sm": "8px",
    },
    "luxury_gold": {
        "name": "轻奢金",
        "primary": "#b8860b",
        "primary_dark": "#996515",
        "primary_light": "#fdf8e8",
        "accent": "#d4a017",
        "bg": "#fafaf7",
        "card_bg": "#ffffff",
        "text": "#2c2c2c",
        "text_secondary": "#7a7a6e",
        "border": "#e8e4d9",
        "success": "#5a9e6f",
        "warning": "#d4a017",
        "danger": "#c0392b",
        "gradient": "linear-gradient(135deg, #1a1a2e 0%, #2d2d44 50%, #b8860b 100%)",
        "shadow": "0 4px 24px rgba(184,134,11,0.15)",
        "radius": "20px",
        "radius_sm": "10px",
    },
    "fresh_green": {
        "name": "清新绿",
        "primary": "#16a34a",
        "primary_dark": "#15803d",
        "primary_light": "#f0fdf4",
        "accent": "#22c55e",
        "bg": "#fafffe",
        "card_bg": "#ffffff",
        "text": "#1a2e1a",
        "text_secondary": "#6b8f6b",
        "border": "#d4e8d4",
        "success": "#16a34a",
        "warning": "#eab308",
        "danger": "#dc2626",
        "gradient": "linear-gradient(135deg, #16a34a 0%, #06b6d4 100%)",
        "shadow": "0 4px 24px rgba(22,163,74,0.12)",
        "radius": "16px",
        "radius_sm": "8px",
    },
}

# ==================== 电商模板HTML ====================
SHOP_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ shop_name }} - {{ shop_slogan }}</title>
    <meta name="description" content="{{ meta_description }}">
    <meta property="og:title" content="{{ shop_name }}">
    <meta property="og:description" content="{{ meta_description }}">
    <meta property="og:type" content="website">
    <meta name="theme-color" content="{{ theme.primary }}">
    <style>
        /* ==================== 1. CSS变量 + 主题 ==================== */
        :root {
            --primary: {{ theme.primary }};
            --primary-dark: {{ theme.primary_dark }};
            --primary-light: {{ theme.primary_light }};
            --accent: {{ theme.accent }};
            --bg: {{ theme.bg }};
            --card-bg: {{ theme.card_bg }};
            --text: {{ theme.text }};
            --text-secondary: {{ theme.text_secondary }};
            --border: {{ theme.border }};
            --success: {{ theme.success }};
            --warning: {{ theme.warning }};
            --danger: {{ theme.danger }};
            --gradient: {{ theme.gradient }};
            --shadow: {{ theme.shadow }};
            --radius: {{ theme.radius }};
            --radius-sm: {{ theme.radius_sm }};
            
            /* 基础变量 */
            --header-height: 64px;
            --footer-height: auto;
            --max-width: 1280px;
            --spacing-xs: 4px;
            --spacing-sm: 8px;
            --spacing-md: 16px;
            --spacing-lg: 24px;
            --spacing-xl: 32px;
            --spacing-2xl: 48px;
            --spacing-3xl: 80px;
        }

        /* ==================== 2. 全局样式 ==================== */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        a {
            color: var(--primary);
            text-decoration: none;
            transition: color 0.2s;
        }

        a:hover {
            color: var(--primary-dark);
        }

        img {
            max-width: 100%;
            height: auto;
            display: block;
        }

        button {
            cursor: pointer;
            border: none;
            outline: none;
            font-family: inherit;
            font-size: inherit;
        }

        input, select, textarea {
            font-family: inherit;
            font-size: inherit;
            outline: none;
        }

        /* 容器 */
        .container {
            max-width: var(--max-width);
            margin: 0 auto;
            padding: 0 var(--spacing-md);
        }

        /* 按钮样式 */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 24px;
            border-radius: var(--radius-sm);
            font-weight: 600;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
            text-align: center;
            min-height: 44px;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: var(--shadow);
        }

        .btn-secondary {
            background: var(--card-bg);
            color: var(--primary);
            border: 2px solid var(--primary);
        }

        .btn-secondary:hover {
            background: var(--primary-light);
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .btn-success {
            background: var(--success);
            color: white;
        }

        .btn-block {
            width: 100%;
        }

        .btn-sm {
            padding: 8px 16px;
            font-size: 14px;
            min-height: 36px;
        }

        .btn-lg {
            padding: 16px 32px;
            font-size: 18px;
        }

        /* 卡片样式 */
        .card {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        }

        /* 价格样式 */
        .price {
            color: var(--danger);
            font-weight: 700;
            font-size: 20px;
        }

        .price-original {
            color: var(--text-secondary);
            text-decoration: line-through;
            font-size: 14px;
            margin-left: 8px;
        }

        /* 评分星星 */
        .stars {
            color: #fbbf24;
            font-size: 14px;
        }

        /* 加载动画 */
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px;
        }

        .loading::after {
            content: '';
            width: 32px;
            height: 32px;
            border: 3px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* ==================== 3. 导航栏 ==================== */
        #main-nav {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: var(--header-height);
            background: var(--card-bg);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            z-index: 1000;
            display: flex;
            align-items: center;
            padding: 0 var(--spacing-md);
        }

        .nav-content {
            max-width: var(--max-width);
            margin: 0 auto;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .nav-logo {
            font-size: 24px;
            font-weight: 700;
            color: var(--primary);
            text-decoration: none;
        }

        .nav-links {
            display: flex;
            gap: var(--spacing-lg);
            list-style: none;
        }

        .nav-links a {
            color: var(--text);
            font-weight: 500;
            transition: color 0.2s;
        }

        .nav-links a:hover {
            color: var(--primary);
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: var(--spacing-md);
        }

        .nav-cart-btn {
            position: relative;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            padding: 8px;
        }

        .cart-badge {
            position: absolute;
            top: 0;
            right: 0;
            background: var(--danger);
            color: white;
            font-size: 12px;
            font-weight: 700;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .nav-toggle {
            display: none;
            flex-direction: column;
            gap: 4px;
            background: none;
            border: none;
            cursor: pointer;
            padding: 8px;
        }

        .nav-toggle span {
            width: 24px;
            height: 3px;
            background: var(--text);
            border-radius: 2px;
            transition: 0.2s;
        }

        /* ==================== 4. 轮播Banner ==================== */
        .banner-carousel {
            margin-top: var(--header-height);
            position: relative;
            overflow: hidden;
            background: var(--gradient);
        }

        .carousel-container {
            position: relative;
            width: 100%;
            height: 400px;
        }

        @media (max-width: 768px) {
            .carousel-container {
                height: 50vw;
            }
        }

        .carousel-slides {
            display: flex;
            transition: transform 0.5s ease;
            height: 100%;
        }

        .carousel-slide {
            min-width: 100%;
            height: 100%;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .carousel-slide img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .carousel-overlay {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 60px var(--spacing-xl) 40px;
            background: linear-gradient(transparent, rgba(0,0,0,0.7));
            color: white;
        }

        .carousel-title {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: var(--spacing-sm);
        }

        .carousel-desc {
            font-size: 18px;
            opacity: 0.9;
        }

        .carousel-dots {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 8px;
        }

        .carousel-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: rgba(255,255,255,0.5);
            cursor: pointer;
            transition: 0.2s;
            border: none;
        }

        .carousel-dot.active {
            background: white;
            transform: scale(1.2);
        }

        .carousel-btn {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            font-size: 24px;
            cursor: pointer;
            transition: 0.2s;
            backdrop-filter: blur(4px);
        }

        .carousel-btn:hover {
            background: rgba(255,255,255,0.3);
        }

        .carousel-prev {
            left: 20px;
        }

        .carousel-next {
            right: 20px;
        }

        /* ==================== 5. 信任条 ==================== */
        .trust-bar {
            background: var(--card-bg);
            padding: var(--spacing-lg) 0;
            border-bottom: 1px solid var(--border);
        }

        .trust-items {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: var(--spacing-lg);
        }

        .trust-item {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            font-weight: 600;
            color: var(--text);
        }

        .trust-icon {
            font-size: 24px;
        }

        /* ==================== 6. 商品瀑布流 ==================== */
        .products-section {
            padding: var(--spacing-3xl) 0;
        }

        .section-title {
            font-size: 32px;
            font-weight: 700;
            text-align: center;
            margin-bottom: var(--spacing-2xl);
            color: var(--text);
        }

        .products-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: var(--spacing-lg);
            padding: 0 var(--spacing-md);
        }

        @media (min-width: 768px) {
            .products-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        @media (min-width: 1024px) {
            .products-grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }

        .product-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }

        .product-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        }

        .product-image {
            position: relative;
            width: 100%;
            padding-top: 100%; /* 1:1 宽高比 */
            overflow: hidden;
            background: var(--bg);
        }

        .product-image img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }

        .product-card:hover .product-image img {
            transform: scale(1.05);
        }

        .product-info {
            padding: var(--spacing-md);
        }

        .product-name {
            font-size: 16px;
            font-weight: 600;
            color: var(--text);
            margin-bottom: var(--spacing-sm);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .product-price-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .product-price {
            color: var(--danger);
            font-size: 20px;
            font-weight: 700;
        }

        .product-original-price {
            color: var(--text-secondary);
            text-decoration: line-through;
            font-size: 14px;
        }

        .add-to-cart-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: var(--radius-sm);
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
            min-height: 36px;
        }

        .add-to-cart-btn:hover {
            background: var(--primary-dark);
        }

        /* 懒加载占位符 */
        .lazy-placeholder {
            background: linear-gradient(90deg, var(--bg) 25%, var(--primary-light) 50%, var(--bg) 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
        }

        @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        /* ==================== 7. 买家秀 ==================== */
        .reviews-section {
            padding: var(--spacing-3xl) 0;
            background: var(--primary-light);
        }

        .reviews-grid {
            display: grid;
            grid-template-columns: repeat(1, 1fr);
            gap: var(--spacing-lg);
            padding: 0 var(--spacing-md);
        }

        @media (min-width: 768px) {
            .reviews-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        .review-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: var(--spacing-lg);
            box-shadow: var(--shadow);
        }

        .review-header {
            display: flex;
            align-items: center;
            gap: var(--spacing-md);
            margin-bottom: var(--spacing-md);
        }

        .review-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--primary);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 20px;
        }

        .review-author {
            font-weight: 600;
            color: var(--text);
        }

        .review-date {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .review-content {
            color: var(--text);
            line-height: 1.6;
            margin-bottom: var(--spacing-md);
        }

        .review-images {
            display: flex;
            gap: var(--spacing-sm);
            overflow-x: auto;
        }

        .review-images img {
            width: 80px;
            height: 80px;
            object-fit: cover;
            border-radius: var(--radius-sm);
            cursor: pointer;
        }

        /* ==================== 8. 商品详情 ==================== */
        .product-detail {
            padding: var(--spacing-3xl) 0;
            margin-top: var(--header-height);
        }

        .product-detail-content {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--spacing-2xl);
            padding: 0 var(--spacing-md);
        }

        @media (min-width: 1024px) {
            .product-detail-content {
                grid-template-columns: 1fr 1fr;
            }
        }

        .product-gallery {
            position: relative;
        }

        .product-main-image {
            width: 100%;
            aspect-ratio: 1;
            object-fit: cover;
            border-radius: var(--radius);
            cursor: zoom-in;
        }

        .product-thumbnails {
            display: flex;
            gap: var(--spacing-sm);
            margin-top: var(--spacing-md);
            overflow-x: auto;
        }

        .product-thumbnail {
            width: 80px;
            height: 80px;
            object-fit: cover;
            border-radius: var(--radius-sm);
            cursor: pointer;
            border: 2px solid transparent;
            transition: 0.2s;
        }

        .product-thumbnail.active {
            border-color: var(--primary);
        }

        /* 放大镜 */
        .zoom-lens {
            position: absolute;
            border: 2px solid var(--primary);
            width: 100px;
            height: 100px;
            background: rgba(255,255,255,0.3);
            cursor: crosshair;
            display: none;
        }

        .zoom-result {
            position: absolute;
            top: 0;
            right: -420px;
            width: 400px;
            height: 400px;
            border: 1px solid var(--border);
            background: white;
            display: none;
            z-index: 100;
            overflow: hidden;
        }

        .zoom-result img {
            position: absolute;
            max-width: none;
        }

        .product-info-detail {
            padding: var(--spacing-lg) 0;
        }

        .product-title {
            font-size: 28px;
            font-weight: 700;
            color: var(--text);
            margin-bottom: var(--spacing-md);
        }

        .product-price-detail {
            margin-bottom: var(--spacing-lg);
        }

        .current-price {
            font-size: 32px;
            font-weight: 700;
            color: var(--danger);
        }

        .original-price {
            font-size: 18px;
            color: var(--text-secondary);
            text-decoration: line-through;
            margin-left: var(--spacing-md);
        }

        /* SKU选择器 */
        .sku-section {
            margin-bottom: var(--spacing-lg);
        }

        .sku-label {
            font-weight: 600;
            margin-bottom: var(--spacing-sm);
            color: var(--text);
        }

        .sku-options {
            display: flex;
            flex-wrap: wrap;
            gap: var(--spacing-sm);
        }

        .sku-option {
            padding: 10px 20px;
            border: 2px solid var(--border);
            border-radius: 999px;
            background: var(--card-bg);
            cursor: pointer;
            transition: 0.2s;
            font-weight: 500;
            min-height: 44px;
        }

        .sku-option:hover {
            border-color: var(--primary);
            color: var(--primary);
        }

        .sku-option.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .sku-option.disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }

        /* 库存进度条 */
        .stock-bar {
            margin-bottom: var(--spacing-lg);
        }

        .stock-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: var(--spacing-sm);
            font-size: 14px;
            color: var(--text-secondary);
        }

        .stock-progress {
            height: 8px;
            background: var(--border);
            border-radius: 4px;
            overflow: hidden;
        }

        .stock-progress-fill {
            height: 100%;
            background: var(--success);
            transition: width 0.3s, background 0.3s;
            border-radius: 4px;
        }

        .stock-progress-fill.medium {
            background: var(--warning);
        }

        .stock-progress-fill.low {
            background: var(--danger);
        }

        /* 数量选择器 */
        .quantity-selector {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            margin-bottom: var(--spacing-lg);
        }

        .quantity-btn {
            width: 44px;
            height: 44px;
            border: 2px solid var(--border);
            background: var(--card-bg);
            border-radius: var(--radius-sm);
            font-size: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
        }

        .quantity-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
        }

        .quantity-input {
            width: 60px;
            height: 44px;
            text-align: center;
            border: 2px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 16px;
            font-weight: 600;
        }

        /* 吸底按钮栏 */
        .sticky-add-to-cart {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--card-bg);
            padding: var(--spacing-md);
            box-shadow: 0 -4px 16px rgba(0,0,0,0.1);
            display: flex;
            gap: var(--spacing-md);
            z-index: 999;
        }

        .sticky-add-to-cart .btn {
            flex: 1;
        }

        /* 商品详情Tabs */
        .product-tabs {
            margin-top: var(--spacing-3xl);
            border-top: 1px solid var(--border);
            padding-top: var(--spacing-2xl);
        }

        .tab-headers {
            display: flex;
            gap: var(--spacing-lg);
            border-bottom: 2px solid var(--border);
            margin-bottom: var(--spacing-lg);
        }

        .tab-header {
            padding: var(--spacing-md) var(--spacing-lg);
            background: none;
            border: none;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
            transition: 0.2s;
        }

        .tab-header.active {
            color: var(--primary);
            border-bottom-color: var(--primary);
        }

        .tab-content {
            display: none;
            padding: var(--spacing-lg) 0;
        }

        .tab-content.active {
            display: block;
        }

        /* 评价列表 */
        .reviews-list {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-lg);
        }

        .review-item {
            padding: var(--spacing-lg);
            background: var(--bg);
            border-radius: var(--radius);
        }

        /* ==================== 9. 购物车 ==================== */
        .cart-page {
            padding: var(--spacing-3xl) 0;
            margin-top: var(--header-height);
            min-height: calc(100vh - var(--header-height) - var(--footer-height));
        }

        .cart-items {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-md);
            margin-bottom: var(--spacing-2xl);
        }

        .cart-item {
            display: grid;
            grid-template-columns: 100px 1fr auto;
            gap: var(--spacing-md);
            padding: var(--spacing-md);
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            align-items: center;
        }

        .cart-item-image {
            width: 100px;
            height: 100px;
            object-fit: cover;
            border-radius: var(--radius-sm);
        }

        .cart-item-info {
            display: flex;
            flex-direction: column;
            gap: var(--spacing-sm);
        }

        .cart-item-name {
            font-weight: 600;
            color: var(--text);
        }

        .cart-item-sku {
            font-size: 14px;
            color: var(--text-secondary);
        }

        .cart-item-price {
            font-weight: 600;
            color: var(--danger);
        }

        .cart-item-actions {
            display: flex;
            align-items: center;
            gap: var(--spacing-md);
        }

        .cart-item-quantity {
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
        }

        .cart-item-quantity button {
            width: 32px;
            height: 32px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            border-radius: var(--radius-sm);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .cart-item-quantity span {
            min-width: 40px;
            text-align: center;
            font-weight: 600;
        }

        .cart-item-remove {
            background: none;
            border: none;
            color: var(--danger);
            cursor: pointer;
            font-size: 20px;
            padding: 4px;
        }

        .cart-item-subtotal {
            font-weight: 700;
            color: var(--text);
            min-width: 80px;
            text-align: right;
        }

        /* 优惠券 */
        .coupon-section {
            background: var(--card-bg);
            padding: var(--spacing-lg);
            border-radius: var(--radius);
            margin-bottom: var(--spacing-lg);
        }

        .coupon-input-group {
            display: flex;
            gap: var(--spacing-sm);
        }

        .coupon-input {
            flex: 1;
            padding: 12px;
            border: 2px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 16px;
        }

        .coupon-input:focus {
            border-color: var(--primary);
        }

        .coupon-message {
            margin-top: var(--spacing-sm);
            font-size: 14px;
            font-weight: 600;
        }

        .coupon-message.success {
            color: var(--success);
        }

        .coupon-message.error {
            color: var(--danger);
        }

        /* 价格汇总 */
        .cart-summary {
            background: var(--card-bg);
            padding: var(--spacing-lg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
        }

        .summary-row {
            display: flex;
            justify-content: space-between;
            padding: var(--spacing-sm) 0;
            color: var(--text-secondary);
        }

        .summary-row.total {
            border-top: 2px solid var(--border);
            margin-top: var(--spacing-md);
            padding-top: var(--spacing-md);
            font-size: 20px;
            font-weight: 700;
            color: var(--text);
        }

        .checkout-btn {
            width: 100%;
            margin-top: var(--spacing-lg);
            padding: 16px;
            font-size: 18px;
        }

        /* 空购物车 */
        .empty-cart {
            text-align: center;
            padding: var(--spacing-3xl) var(--spacing-md);
        }

        .empty-cart-icon {
            font-size: 80px;
            margin-bottom: var(--spacing-lg);
        }

        .empty-cart-text {
            font-size: 20px;
            color: var(--text-secondary);
            margin-bottom: var(--spacing-lg);
        }

        /* ==================== 10. 结算页 ==================== */
        .checkout-page {
            padding: var(--spacing-3xl) 0;
            margin-top: var(--header-height);
            min-height: calc(100vh - var(--header-height) - var(--footer-height));
        }

        .checkout-content {
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--spacing-2xl);
        }

        @media (min-width: 1024px) {
            .checkout-content {
                grid-template-columns: 2fr 1fr;
            }
        }

        .checkout-form {
            background: var(--card-bg);
            padding: var(--spacing-xl);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
        }

        .form-section {
            margin-bottom: var(--spacing-xl);
        }

        .form-section-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: var(--spacing-lg);
            color: var(--text);
        }

        .form-group {
            margin-bottom: var(--spacing-md);
        }

        .form-label {
            display: block;
            font-weight: 600;
            margin-bottom: var(--spacing-sm);
            color: var(--text);
        }

        .form-input {
            width: 100%;
            padding: 12px;
            border: 2px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 16px;
            transition: border-color 0.2s;
        }

        .form-input:focus {
            border-color: var(--primary);
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--spacing-md);
        }

        /* 支付方式 */
        .payment-methods {
            display: flex;
            gap: var(--spacing-md);
            flex-wrap: wrap;
        }

        .payment-method {
            flex: 1;
            min-width: 120px;
            padding: var(--spacing-md);
            border: 2px solid var(--border);
            border-radius: var(--radius);
            background: var(--card-bg);
            cursor: pointer;
            text-align: center;
            transition: 0.2s;
            min-height: 80px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: var(--spacing-sm);
        }

        .payment-method:hover {
            border-color: var(--primary);
        }

        .payment-method.active {
            border-color: var(--primary);
            background: var(--primary-light);
        }

        .payment-icon {
            font-size: 32px;
        }

        .payment-name {
            font-weight: 600;
            font-size: 14px;
        }

        /* 订单商品清单 */
        .checkout-items {
            background: var(--card-bg);
            padding: var(--spacing-lg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            margin-bottom: var(--spacing-lg);
        }

        .checkout-item {
            display: flex;
            gap: var(--spacing-md);
            padding: var(--spacing-md) 0;
            border-bottom: 1px solid var(--border);
        }

        .checkout-item:last-child {
            border-bottom: none;
        }

        .checkout-item-image {
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: var(--radius-sm);
        }

        .checkout-item-info {
            flex: 1;
        }

        .checkout-item-name {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }

        .checkout-item-sku {
            font-size: 12px;
            color: var(--text-secondary);
        }

        .checkout-item-price {
            font-weight: 600;
            color: var(--danger);
        }

        /* 提交按钮 */
        .place-order-btn {
            width: 100%;
            padding: 16px;
            font-size: 18px;
            margin-top: var(--spacing-md);
        }

        /* Loading动画 */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }

        .loading-spinner {
            text-align: center;
        }

        .loading-spinner p {
            margin-top: var(--spacing-md);
            font-weight: 600;
            color: var(--text);
        }

        /* ==================== 11. 页脚 ==================== */
        footer {
            background: var(--text);
            color: white;
            padding: var(--spacing-3xl) 0 var(--spacing-lg);
            margin-top: auto;
        }

        .footer-content {
            display: grid;
            grid-template-columns: repeat(1, 1fr);
            gap: var(--spacing-xl);
            padding: 0 var(--spacing-md);
        }

        @media (min-width: 768px) {
            .footer-content {
                grid-template-columns: repeat(4, 1fr);
            }
        }

        .footer-column h3 {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: var(--spacing-lg);
        }

        .footer-column ul {
            list-style: none;
        }

        .footer-column li {
            margin-bottom: var(--spacing-sm);
        }

        .footer-column a {
            color: rgba(255,255,255,0.8);
            transition: color 0.2s;
        }

        .footer-column a:hover {
            color: white;
        }

        .payment-icons {
            display: flex;
            gap: var(--spacing-sm);
            flex-wrap: wrap;
            margin-top: var(--spacing-md);
        }

        .payment-icon-box {
            padding: 8px 12px;
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: var(--radius-sm);
            font-size: 12px;
            color: rgba(255,255,255,0.8);
        }

        .security-badges {
            display: flex;
            gap: var(--spacing-md);
            margin-top: var(--spacing-md);
            flex-wrap: wrap;
        }

        .security-badge {
            font-size: 14px;
            color: rgba(255,255,255,0.8);
        }

        .footer-bottom {
            text-align: center;
            padding-top: var(--spacing-xl);
            margin-top: var(--spacing-xl);
            border-top: 1px solid rgba(255,255,255,0.1);
            color: rgba(255,255,255,0.6);
            font-size: 14px;
        }

        .footer-powered {
            margin-top: var(--spacing-sm);
        }

        .footer-powered a {
            color: var(--primary);
            font-weight: 600;
        }

        /* ==================== 12. 悬浮按钮 ==================== */
        .floating-buttons {
            position: fixed;
            bottom: 80px;
            right: 20px;
            display: flex;
            flex-direction: column;
            gap: var(--spacing-md);
            z-index: 998;
        }

        .floating-btn {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: var(--primary);
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
        }

        .floating-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }

        #customer-service-btn {
            background: var(--success);
        }

        /* ==================== 13. 紧迫感弹窗 ==================== */
        .urgency-popup {
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: var(--card-bg);
            padding: var(--spacing-md) var(--spacing-lg);
            border-radius: var(--radius);
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            z-index: 1001;
            display: none;
            max-width: 320px;
            animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .urgency-popup.show {
            display: block;
        }

        .urgency-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--spacing-sm);
        }

        .urgency-title {
            font-weight: 700;
            color: var(--danger);
        }

        .urgency-close {
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: var(--text-secondary);
            padding: 4px;
        }

        .urgency-content {
            font-size: 14px;
            color: var(--text);
        }

        /* ==================== 14. 移动端适配 ==================== */
        @media (max-width: 768px) {
            :root {
                --header-height: 56px;
            }

            body {
                font-size: 14px;
            }

            .nav-links {
                display: none;
                position: fixed;
                top: var(--header-height);
                left: 0;
                right: 0;
                background: var(--card-bg);
                flex-direction: column;
                padding: var(--spacing-md);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }

            .nav-links.show {
                display: flex;
            }

            .nav-toggle {
                display: flex;
            }

            .section-title {
                font-size: 24px;
            }

            .carousel-title {
                font-size: 24px;
            }

            .carousel-desc {
                font-size: 14px;
            }

            .product-title {
                font-size: 22px;
            }

            .current-price {
                font-size: 26px;
            }

            .cart-item {
                grid-template-columns: 80px 1fr;
                gap: var(--spacing-sm);
            }

            .cart-item-subtotal {
                grid-column: 2;
                text-align: left;
            }

            .form-row {
                grid-template-columns: 1fr;
            }

            .payment-methods {
                flex-direction: column;
            }

            .payment-method {
                min-width: auto;
            }

            .footer-content {
                grid-template-columns: 1fr;
            }

            /* 底部导航 */
            .mobile-bottom-nav {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: var(--card-bg);
                box-shadow: 0 -2px 8px rgba(0,0,0,0.08);
                display: flex;
                justify-content: space-around;
                padding: var(--spacing-sm) 0;
                z-index: 999;
                padding-bottom: env(safe-area-inset-bottom);
            }

            .mobile-nav-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
                text-decoration: none;
                color: var(--text-secondary);
                font-size: 12px;
                padding: 8px;
                min-height: 44px;
                justify-content: center;
            }

            .mobile-nav-item.active {
                color: var(--primary);
            }

            .mobile-nav-icon {
                font-size: 24px;
            }

            /* 调整主体padding避免被底部导航遮挡 */
            body {
                padding-bottom: 60px;
            }

            .sticky-add-to-cart {
                bottom: 60px;
            }
        }

        @media (min-width: 769px) {
            .mobile-bottom-nav {
                display: none;
            }
        }

        /* 触摸优化 */
        @media (hover: none) {
            .btn, .sku-option, .payment-method, .cart-item-remove, .floating-btn {
                min-height: 44px;
                min-width: 44px;
            }
        }

        /* 安全区域适配（刘海屏） */
        @supports (padding: env(safe-area-inset-left)) {
            #main-nav {
                padding-left: env(safe-area-inset-left);
                padding-right: env(safe-area-inset-right);
            }

            .container {
                padding-left: max(var(--spacing-md), env(safe-area-inset-left));
                padding-right: max(var(--spacing-md), env(safe-area-inset-right));
            }
        }

        /* 品牌故事/优势模块 */
        .brand-story {
            padding: var(--spacing-3xl) 0;
            background: var(--bg);
        }

        .features-grid {
            display: grid;
            grid-template-columns: repeat(1, 1fr);
            gap: var(--spacing-xl);
            padding: 0 var(--spacing-md);
        }

        @media (min-width: 768px) {
            .features-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }

        .feature-card {
            text-align: center;
            padding: var(--spacing-xl);
        }

        .feature-icon {
            font-size: 48px;
            margin-bottom: var(--spacing-md);
        }

        .feature-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: var(--spacing-sm);
            color: var(--text);
        }

        .feature-desc {
            color: var(--text-secondary);
            line-height: 1.6;
        }

        /* CTA区域 */
        .cta-section {
            padding: var(--spacing-3xl) 0;
            background: var(--gradient);
            color: white;
            text-align: center;
        }

        .cta-title {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: var(--spacing-md);
        }

        .cta-desc {
            font-size: 18px;
            margin-bottom: var(--spacing-xl);
            opacity: 0.9;
        }

        .cta-button {
            display: inline-block;
            padding: 16px 48px;
            background: white;
            color: var(--primary);
            border-radius: var(--radius);
            font-weight: 700;
            font-size: 18px;
            transition: 0.2s;
        }

        .cta-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        }

        /* 相关商品推荐 */
        .related-products {
            padding: var(--spacing-3xl) 0;
            border-top: 1px solid var(--border);
        }

        /* 订单状态页 */
        .order-status-page {
            padding: var(--spacing-3xl) 0;
            margin-top: var(--header-height);
            text-align: center;
            min-height: calc(100vh - var(--header-height) - var(--footer-height));
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .order-status-content {
            max-width: 480px;
            padding: var(--spacing-xl);
        }

        .order-status-icon {
            font-size: 80px;
            margin-bottom: var(--spacing-lg);
        }

        .order-status-title {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: var(--spacing-md);
            color: var(--text);
        }

        .order-status-desc {
            color: var(--text-secondary);
            margin-bottom: var(--spacing-xl);
            line-height: 1.6;
        }

        /* 返回顶部按钮 */
        .back-to-top {
            position: fixed;
            bottom: 140px;
            right: 20px;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--card-bg);
            color: var(--text);
            border: 1px solid var(--border);
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            font-size: 20px;
            display: none;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
            z-index: 997;
        }

        .back-to-top.show {
            display: flex;
        }

        .back-to-top:hover {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }
    </style>
</head>
<body>
    <!-- 导航栏 -->
    <nav id="main-nav">
        <div class="nav-content">
            <a href="#/" class="nav-logo">{{ shop_name }}</a>
            <ul class="nav-links">
                <li><a href="#/">首页</a></li>
                <li><a href="#/products">全部商品</a></li>
                <li><a href="#/about">关于我们</a></li>
                <li><a href="#/contact">联系我们</a></li>
            </ul>
            <div class="nav-actions">
                <button class="nav-cart-btn" data-action="nav-cart">
                    🛒
                    <span class="cart-badge" id="cart-badge" style="display:none;">0</span>
                </button>
                <button class="nav-toggle" id="nav-toggle" aria-label="菜单">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
            </div>
        </div>
    </nav>

    <!-- 主内容区 -->
    <main id="app">
        <!-- SPA内容由JS动态渲染 -->
    </main>

    <!-- 页脚 -->
    <footer>
        <div class="container">
            <div class="footer-content">
                <div class="footer-column">
                    <h3>关于我们</h3>
                    <ul>
                        <li><a href="#/about">品牌故事</a></li>
                        <li><a href="#/about">企业文化</a></li>
                        <li><a href="#/contact">联系方式</a></li>
                        <li><a href="#/careers">加入我们</a></li>
                    </ul>
                </div>
                <div class="footer-column">
                    <h3>帮助中心</h3>
                    <ul>
                        <li><a href="#/help">购物指南</a></li>
                        <li><a href="#/help">支付方式</a></li>
                        <li><a href="#/help">配送说明</a></li>
                        <li><a href="#/help">退换货政策</a></li>
                    </ul>
                </div>
                <div class="footer-column">
                    <h3>联系方式</h3>
                    <ul>
                        <li>客服电话：400-123-4567</li>
                        <li>客服邮箱：{{ contact_email if contact_email else 'support@' + shop_name + '.com' }}</li>
                        {% if contact_phone %}<li>客服电话：{{ contact_phone }}</li>{% endif %}
                        {% if contact_wechat %}<li>客服微信：{{ contact_wechat }}</li>{% endif %}
                        <li>服务时间：9:00-21:00</li>
                    </ul>
                </div>
                <div class="footer-column">
                    <h3>关注我们</h3>
                    <div class="payment-icons">
                        {% if payment_wechat %}<span class="payment-icon-box">[微信]</span>{% endif %}
                        {% if payment_alipay %}<span class="payment-icon-box">[支付宝]</span>{% endif %}
                        {% if payment_bank %}<span class="payment-icon-box">[银行卡]</span>{% endif %}
                        {% if payment_paypal %}<span class="payment-icon-box">[PayPal]</span>{% endif %}
                        {% if payment_card %}<span class="payment-icon-box">[VISA]</span><span class="payment-icon-box">[Mastercard]</span>{% endif %}
                    </div>
                    <div class="security-badges">
                        <span class="security-badge">🔒 SSL安全加密</span>
                        <span class="security-badge">💰 资金安全</span>
                        <span class="security-badge">✅ 正品保障</span>
                    </div>
                </div>
            </div>
            <div class="footer-bottom">
                <p>&copy; {{ current_year }} {{ shop_name }}. 保留所有权利.</p>
                {% if not is_pro %}
                <div class="sg-watermark-banner">⚡ 由 <a href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener">SG智能建站</a> 生成 · <a href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener">升级专业版去除</a></div>
                {% endif %}
                <p class="footer-powered">{% if is_pro %}Powered by SG智能建站{% else %}Powered by <a href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener">SG智能建站</a> · 免费版{% endif %}</p>
            </div>
        </div>
    </footer>

    <!-- 悬浮按钮 -->
    <div class="floating-buttons">
        <button class="floating-btn" id="customer-service-btn" data-action="customer-service" data-url="{{ customer_service_url }}" aria-label="客服">💬</button>
    </div>

    <!-- 返回顶部 -->
    <button class="back-to-top" id="back-to-top" aria-label="返回顶部">↑</button>

    <!-- 移动端底部导航 -->
    <nav class="mobile-bottom-nav">
        <a href="#/" class="mobile-nav-item active">
            <span class="mobile-nav-icon">🏠</span>
            <span>首页</span>
        </a>
        <a href="#/products" class="mobile-nav-item">
            <span class="mobile-nav-icon">📦</span>
            <span>分类</span>
        </a>
        <a href="#/cart" class="mobile-nav-item">
            <span class="mobile-nav-icon">🛒</span>
            <span>购物车</span>
        </a>
        <a href="#/account" class="mobile-nav-item">
            <span class="mobile-nav-icon">👤</span>
            <span>我的</span>
        </a>
    </nav>

    <!-- 紧迫感弹窗 -->
    <div class="urgency-popup" id="urgency-popup">
        <div class="urgency-header">
            <span class="urgency-title">🔥 热门提醒</span>
            <button class="urgency-close" id="urgency-close">&times;</button>
        </div>
        <div class="urgency-content" id="urgency-content">
            <!-- 动态内容 -->
        </div>
    </div>

    <!-- JSON-LD 结构化数据 -->
    <script type="application/ld+json">
    {{ json_ld | safe }}
    </script>

    <!-- 主JS -->
    <script>
function escHtml(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
    // ==================== XSS防御 ====================
    function _esc(str) {
        if (str == null) return '';
        return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
    }
    function _escAttr(str) { return _esc(str); }

    // ==================== 全局配置 ====================
    const CONFIG = {
        apiBase: '{{ api_base_url }}',
        siteId: '{{ site_id }}',
        theme: '{{ theme }}',
        currency: '{{ currency }}',
        currencySymbol: '{{ currency_symbol }}',
        shopName: '{{ shop_name }}',
        customerServiceUrl: '{{ customer_service_url }}',
        gaId: '{{ ga_id }}',
        baiduTongjiId: '{{ baidu_tongji_id }}',
    };

    // ==================== 主题定义 ====================
    const THEMES = {
        tech_blue: {
            name: "科技蓝",
            primary: "#2563eb",
            primary_dark: "#1d4ed8",
            primary_light: "#eff6ff",
            accent: "#3b82f6",
            bg: "#f8fafc",
            card_bg: "#ffffff",
            text: "#1e293b",
            text_secondary: "#64748b",
            border: "#e2e8f0",
            success: "#22c55e",
            warning: "#f59e0b",
            danger: "#ef4444",
            gradient: "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
            shadow: "0 4px 24px rgba(37,99,235,0.12)",
            radius: "16px",
            radius_sm: "8px",
        },
        luxury_gold: {
            name: "轻奢金",
            primary: "#b8860b",
            primary_dark: "#996515",
            primary_light: "#fdf8e8",
            accent: "#d4a017",
            bg: "#fafaf7",
            card_bg: "#ffffff",
            text: "#2c2c2c",
            text_secondary: "#7a7a6e",
            border: "#e8e4d9",
            success: "#5a9e6f",
            warning: "#d4a017",
            danger: "#c0392b",
            gradient: "linear-gradient(135deg, #1a1a2e 0%, #2d2d44 50%, #b8860b 100%)",
            shadow: "0 4px 24px rgba(184,134,11,0.15)",
            radius: "20px",
            radius_sm: "10px",
        },
        fresh_green: {
            name: "清新绿",
            primary: "#16a34a",
            primary_dark: "#15803d",
            primary_light: "#f0fdf4",
            accent: "#22c55e",
            bg: "#fafffe",
            card_bg: "#ffffff",
            text: "#1a2e1a",
            text_secondary: "#6b8f6b",
            border: "#d4e8d4",
            success: "#16a34a",
            warning: "#eab308",
            danger: "#dc2626",
            gradient: "linear-gradient(135deg, #16a34a 0%, #06b6d4 100%)",
            shadow: "0 4px 24px rgba(22,163,74,0.12)",
            radius: "16px",
            radius_sm: "8px",
        }
    };

    // ==================== 路由系统 ====================
    class Router {
        constructor() {
            this.routes = {
                '/': this.renderHome.bind(this),
                '/product': this.renderProduct.bind(this),
                '/cart': this.renderCart.bind(this),
                '/checkout': this.renderCheckout.bind(this),
                '/order': this.renderOrderStatus.bind(this),
                '/products': this.renderProducts.bind(this),
                '/about': this.renderAbout.bind(this),
                '/contact': this.renderContact.bind(this),
                '/help': this.renderHelp.bind(this),
            };
        }

        navigate(path) {
            location.hash = '#' + path;
        }

        handleRoute() {
            const hash = location.hash.slice(1) || '/';
            const [path, ...params] = hash.split('/').filter(Boolean);
            
            let routePath = '/' + path;
            let routeParams = params;

            // 处理动态路由
            if (path === 'product' && params.length > 0) {
                routePath = '/product';
            } else if (path === 'order' && params.length > 0) {
                routePath = '/order';
            } else if (!this.routes[routePath]) {
                routePath = '/';
            }

            const renderFn = this.routes[routePath] || this.routes['/'];
            renderFn(...routeParams);
        }

        renderHome() {
            app.renderHome();
        }

        renderProduct(id) {
            app.renderProduct(id);
        }

        renderCart() {
            app.renderCart();
        }

        renderCheckout() {
            app.renderCheckout();
        }

        renderOrderStatus(orderId) {
            app.renderOrderStatus(orderId);
        }

        renderProducts() {
            app.renderProducts();
        }

        renderAbout() {
            app.renderAbout();
        }

        renderContact() {
            app.renderContact();
        }

        renderHelp() {
            app.renderHelp();
        }
    }

    // ==================== API服务 ====================
    class ShopAPI {
        constructor() {
            this.baseURL = CONFIG.apiBase + '/api/v1/shop/' + CONFIG.siteId;
        }

        async request(endpoint, options = {}) {
            const url = this.baseURL + endpoint;
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                },
            };
            
            const finalOptions = {
                ...defaultOptions,
                ...options,
                headers: {
                    ...defaultOptions.headers,
                    ...options.headers,
                },
            };

            try {
                const response = await fetch(url, finalOptions);
                if (!response.ok) {
                    throw new Error('API请求失败: ' + response.status);
                }
                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        }

        async getProducts(params = {}) {
            const query = new URLSearchParams(params).toString();
            return this.request('/products' + (query ? '?' + query : ''));
        }

        async getProduct(id) {
            return this.request('/products/' + id);
        }

        async getCategories() {
            return this.request('/categories');
        }

        async getFeatured() {
            return this.request('/featured');
        }

        async getBanners() {
            return this.request('/banners');
        }

        async getReviews(productId) {
            return this.request('/products/' + productId + '/reviews');
        }

        async submitReview(productId, data) {
            return this.request('/products/' + productId + '/reviews', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        }

        async createOrder(data) {
            return this.request('/orders', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        }

        async getOrderStatus(orderId) {
            return this.request('/orders/' + orderId);
        }

        async getPaymentUrl(orderId) {
            return this.request('/orders/' + orderId + '/pay');
        }

        async getConfig() {
            return this.request('/config');
        }

        async calculateShipping(items, address) {
            return this.request('/shipping/calculate', {
                method: 'POST',
                body: JSON.stringify({ items, address }),
            });
        }

        async validateCoupon(code, total) {
            return this.request('/coupon/validate', {
                method: 'POST',
                body: JSON.stringify({ code, total }),
            });
        }
    }

    // ==================== 购物车 ====================
    class Cart {
        constructor() {
            this.items = JSON.parse(localStorage.getItem('sg_cart') || '[]');
            this.coupon = JSON.parse(localStorage.getItem('sg_coupon') || 'null');
        }

        save() {
            localStorage.setItem('sg_cart', JSON.stringify(this.items));
            if (this.coupon) {
                localStorage.setItem('sg_coupon', JSON.stringify(this.coupon));
            } else {
                localStorage.removeItem('sg_coupon');
            }
            this.updateBadge();
        }

        addItem(product, variant, quantity = 1) {
            const existingIndex = this.items.findIndex(
                item => item.product.id === product.id && 
                       JSON.stringify(item.variant) === JSON.stringify(variant)
            );

            if (existingIndex > -1) {
                this.items[existingIndex].quantity += quantity;
            } else {
                this.items.push({ product, variant, quantity });
            }
            this.save();
        }

        removeItem(index) {
            this.items.splice(index, 1);
            this.save();
        }

        updateQuantity(index, qty) {
            if (qty < 1) {
                this.removeItem(index);
            } else {
                this.items[index].quantity = qty;
                this.save();
            }
        }

        clear() {
            this.items = [];
            this.coupon = null;
            this.save();
        }

        getSubtotal() {
            return this.items.reduce((sum, item) => {
                const price = item.variant ? item.variant.price : item.product.price;
                return sum + price * item.quantity;
            }, 0);
        }

        getDiscount() {
            if (!this.coupon) return 0;
            return this.coupon.discount_amount || 0;
        }

        getShipping() {
            const subtotal = this.getSubtotal();
            // 满99包邮
            return subtotal >= 99 ? 0 : 10;
        }

        getTotal() {
            return this.getSubtotal() - this.getDiscount() + this.getShipping();
        }

        getItemCount() {
            return this.items.reduce((sum, item) => sum + item.quantity, 0);
        }

        applyCoupon(code) {
            return api.validateCoupon(code, this.getSubtotal()).then(result => {
                if (result.valid) {
                    this.coupon = result;
                    this.save();
                    return { success: true, message: '优惠券已应用' };
                } else {
                    return { success: false, message: result.message || '优惠券无效' };
                }
            });
        }

        updateBadge() {
            const badge = document.getElementById('cart-badge');
            if (badge) {
                const count = this.getItemCount();
                badge.textContent = count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
        }
    }

    // ==================== 主题切换 ====================
    function applyTheme(themeName) {
        const theme = THEMES[themeName];
        if (!theme) return;

        const root = document.documentElement;
        Object.keys(theme).forEach(key => {
            const cssVar = '--' + key.replace(/_/g, '-');
            root.style.setProperty(cssVar, theme[key]);
        });
        
        localStorage.setItem('sg_theme', themeName);
    }

    // ==================== 紧迫感模块 ====================
    class UrgencyModule {
        constructor() {
            this.popup = document.getElementById('urgency-popup');
            this.content = document.getElementById('urgency-content');
            this.closeBtn = document.getElementById('urgency-close');
            
            if (this.closeBtn) {
                this.closeBtn.addEventListener('click', () => this.hide());
            }
        }

        show() {
            if (this.popup) {
                this.popup.classList.add('show');
            }
        }

        hide() {
            if (this.popup) {
                this.popup.classList.remove('show');
            }
        }

        showRecentBuyer() {
            // 使用真实商品名和随机匿名化买方（不再硬编码假名）
            const namePool = ['王*华', '李*明', '张*军', '赵*丽', '陈*伟', '刘*芳', '周*杰', '吴*娟', '杨*强', '黄*敏'];
            const prods = (window.__shopProducts || []).slice(0, 20);
            const productName = prods.length > 0 
                ? _esc(prods[Math.floor(Math.random() * prods.length)].name) 
                : '';
            const buyerName = namePool[Math.floor(Math.random() * namePool.length)];
            const minutes = Math.floor(Math.random() * 30) + 1;

            if (this.content && productName) {
                this.content.innerHTML = `
                    <strong>${_esc(buyerName)}</strong> 在${minutes}分钟前购买了<br>
                    <strong>${productName}</strong>
                `;
            } else if (this.content) {
                // 无商品数据时不显示社交证明
                return;
            }
            this.show();

            // 10秒后自动关闭
            setTimeout(() => this.hide(), 10000);
        }

        showStockBar(stock, total) {
            const percentage = (stock / total) * 100;
            let className = 'high';
            if (percentage < 30) className = 'low';
            else if (percentage < 60) className = 'medium';

            return `
                <div class="stock-bar">
                    <div class="stock-info">
                        <span>仅剩 ${stock} 件</span>
                        <span>已售 ${total - stock} 件</span>
                    </div>
                    <div class="stock-progress">
                        <div class="stock-progress-fill ${className}" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }

        showCountdown(endTime) {
            const update = () => {
                const now = Date.now();
                const diff = endTime - now;

                if (diff <= 0) {
                    return '活动已结束';
                }

                const hours = Math.floor(diff / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((diff % (1000 * 60)) / 1000);

                return `${hours}小时 ${minutes}分 ${seconds}秒`;
            };

            const countdownEl = document.createElement('div');
            countdownEl.className = 'countdown-timer';
            countdownEl.style.cssText = 'font-weight:700;color:' + getComputedStyle(document.documentElement).getPropertyValue('--danger') + ';';
            
            const timer = setInterval(() => {
                countdownEl.textContent = update();
                if (endTime - Date.now() <= 0) {
                    clearInterval(timer);
                }
            }, 1000);
            
            countdownEl.textContent = update();
            return countdownEl;
        }
    }

    // ==================== 页面渲染 ====================
    class ShopApp {
        constructor() {
            this.api = new ShopAPI();
            this.cart = new Cart();
            this.urgency = new UrgencyModule();
        }

        async renderHome() {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="loading"></div>';

            try {
                const [banners, featured, products, reviews] = await Promise.all([
                    this.api.getBanners(),
                    this.api.getFeatured(),
                    this.api.getProducts({ limit: 12 }),
                    this.api.getReviews('featured'),
                ]);

                app.innerHTML = `
                    <!-- 轮播Banner -->
                    <section class="banner-carousel">
                        <div class="carousel-container">
                            <div class="carousel-slides" id="carousel-slides">
                                ${banners.map((banner, i) => `
                                    <div class="carousel-slide">
                                        <img src="${_escAttr(banner.image || 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="400"><rect fill="%23' + CONFIG.theme.primary.replace('#', '') + '" width="1200" height="400"/><text fill="%23fff" font-family="Arial" font-size="40" x="50%" y="50%" text-anchor="middle">Banner ' + (i + 1) + '</text></svg>')}" alt="${_esc(banner.title)}">
                                        <div class="carousel-overlay">
                                            <h2 class="carousel-title">${_esc(banner.title)}</h2>
                                            <p class="carousel-desc">${_esc(banner.description || '')}</p>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            <button class="carousel-btn carousel-prev" id="carousel-prev">‹</button>
                            <button class="carousel-btn carousel-next" id="carousel-next">›</button>
                            <div class="carousel-dots" id="carousel-dots">
                                ${banners.map((_, i) => `
                                    <button class="carousel-dot ${i === 0 ? 'active' : ''}" data-index="${i}"></button>
                                `).join('')}
                            </div>
                        </div>
                    </section>

                    <!-- 信任条 -->
                    <section class="trust-bar">
                        <div class="container">
                            <div class="trust-items">
                                <div class="trust-item">
                                    <span class="trust-icon">✅</span>
                                    <span>正品保障</span>
                                </div>
                                <div class="trust-item">
                                    <span class="trust-icon">🚚</span>
                                    <span>极速发货</span>
                                </div>
                                <div class="trust-item">
                                    <span class="trust-icon">↩️</span>
                                    <span>7天退换</span>
                                </div>
                                <div class="trust-item">
                                    <span class="trust-icon">🔒</span>
                                    <span>安全支付</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- 精选商品 -->
                    <section class="products-section">
                        <div class="container">
                            <h2 class="section-title">精选推荐</h2>
                            <div class="products-grid" id="featured-products">
                                ${products.slice(0, 8).map(product => this.renderProductCard(product)).join('')}
                            </div>
                        </div>
                    </section>

                    <!-- 买家秀 -->
                    <section class="reviews-section">
                        <div class="container">
                            <h2 class="section-title">买家秀</h2>
                            <div class="reviews-grid">
                                ${reviews.slice(0, 3).map(review => `
                                    <div class="review-card">
                                        <div class="review-header">
                                            <div class="review-avatar">${_esc(review.author[0])}</div>
                                            <div>
                                                <div class="review-author">${_esc(review.author)}</div>
                                                <div class="review-date">${_esc(review.date)}</div>
                                            </div>
                                        </div>
                                        <div class="review-content">${_esc(review.content)}</div>
                                        ${review.images && review.images.length > 0 ? `
                                            <div class="review-images">
                                                ${review.images.map(img => `<img src="${_escAttr(img)}" alt="买家秀">`).join('')}
                                            </div>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </section>

                    <!-- 品牌故事/优势 -->
                    <section class="brand-story">
                        <div class="container">
                            <h2 class="section-title">为什么选择我们</h2>
                            <div class="features-grid">
                                <div class="feature-card">
                                    <div class="feature-icon">🎯</div>
                                    <h3 class="feature-title">精选品质</h3>
                                    <p class="feature-desc">每一件商品都经过严格筛选，确保品质卓越</p>
                                </div>
                                <div class="feature-card">
                                    <div class="feature-icon">💯</div>
                                    <h3 class="feature-title">满意保证</h3>
                                    <p class="feature-desc">7天无理由退换，购物无忧</p>
                                </div>
                                <div class="feature-card">
                                    <div class="feature-icon">🚀</div>
                                    <h3 class="feature-title">极速配送</h3>
                                    <p class="feature-desc">订单确认后24小时内发货</p>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- CTA -->
                    <section class="cta-section">
                        <div class="container">
                            <h2 class="cta-title">开启您的购物之旅</h2>
                            <p class="cta-desc">发现更多优质商品，享受便捷购物体验</p>
                            <a href="#/products" class="cta-button">立即探索</a>
                        </div>
                    </section>
                `;

                // 初始化轮播
                this.initCarousel();
                
                // 初始化懒加载
                this.initLazyLoad();

                // 更新购物车角标
                this.cart.updateBadge();

            } catch (error) {
                console.error('渲染首页失败:', error);
                app.innerHTML = '<div class="container" style="text-align:center;padding:80px 0;"><h2>加载失败</h2><p>请刷新页面重试</p></div>';
            }
        }

        renderProductCard(product) {
            const price = product.price || 0;
            const originalPrice = product.original_price || price * 1.2;
            
            return `
                <div class="product-card" data-action="view-product" data-id="${_escAttr(product.id)}">
                    <div class="product-image lazy-placeholder">
                        <img src="${_escAttr(product.image || 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect fill="%23f0f0f0" width="400" height="400"/><text fill="%23999" font-family="Arial" font-size="20" x="50%" y="50%" text-anchor="middle">Loading...</text></svg>'))}" 
                             alt="${_esc(product.name)}" 
                             loading="lazy"
                             onload="this.parentElement.classList.remove('lazy-placeholder')">
                    </div>
                    <div class="product-info">
                        <h3 class="product-name">${_esc(product.name)}</h3>
                        <div class="product-price-row">
                            <span class="product-price">${CONFIG.currencySymbol}${price.toFixed(2)}</span>
                            ${originalPrice > price ? `<span class="product-original-price">${CONFIG.currencySymbol}${originalPrice.toFixed(2)}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }

        initCarousel() {
            const slides = document.getElementById('carousel-slides');
            const dots = document.querySelectorAll('.carousel-dot');
            const prevBtn = document.getElementById('carousel-prev');
            const nextBtn = document.getElementById('carousel-next');
            
            if (!slides || !dots.length) return;

            let currentIndex = 0;
            const totalSlides = dots.length;
            let autoPlayTimer;

            const goTo = (index) => {
                if (index < 0) index = totalSlides - 1;
                if (index >= totalSlides) index = 0;
                
                currentIndex = index;
                slides.style.transform = 'translateX(-' + (index * 100) + '%)';
                
                dots.forEach((dot, i) => {
                    dot.classList.toggle('active', i === index);
                });
            };

            const next = () => goTo(currentIndex + 1);
            const prev = () => goTo(currentIndex - 1);

            const startAutoPlay = () => {
                autoPlayTimer = setInterval(next, 5000);
            };

            const stopAutoPlay = () => {
                clearInterval(autoPlayTimer);
            };

            if (prevBtn) prevBtn.addEventListener('click', () => { prev(); stopAutoPlay(); });
            if (nextBtn) nextBtn.addEventListener('click', () => { next(); stopAutoPlay(); });
            
            dots.forEach((dot, i) => {
                dot.addEventListener('click', () => { goTo(i); stopAutoPlay(); });
            });

            // 触摸滑动支持
            let touchStartX = 0;
            let touchEndX = 0;

            slides.addEventListener('touchstart', (e) => {
                touchStartX = e.changedTouches[0].screenX;
                stopAutoPlay();
            }, { passive: true });

            slides.addEventListener('touchend', (e) => {
                touchEndX = e.changedTouches[0].screenX;
                const diff = touchStartX - touchEndX;
                
                if (Math.abs(diff) > 50) {
                    if (diff > 0) next();
                    else prev();
                }
                startAutoPlay();
            }, { passive: true });

            startAutoPlay();
        }

        initLazyLoad() {
            const images = document.querySelectorAll('img[loading="lazy"]');
            
            if ('IntersectionObserver' in window) {
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            // 图片加载逻辑
                            observer.unobserve(img);
                        }
                    });
                });

                images.forEach(img => observer.observe(img));
            }
        }

        async renderProduct(id) {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="loading"></div>';

            try {
                const [product, reviews] = await Promise.all([
                    this.api.getProduct(id),
                    this.api.getReviews(id),
                ]);

                const currentVariant = product.variants ? product.variants[0] : null;
                const price = currentVariant ? currentVariant.price : product.price;
                const originalPrice = product.original_price || price * 1.2;
                const stock = currentVariant ? currentVariant.stock : product.stock;

                app.innerHTML = `
                    <div class="product-detail">
                        <div class="container">
                            <div class="product-detail-content">
                                <!-- 商品图片 -->
                                <div class="product-gallery">
                                    <img src="${_escAttr(product.images[0] || 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect fill="%23f0f0f0" width="600" height="600"/><text fill="%23999" font-family="Arial" font-size="24" x="50%" y="50%" text-anchor="middle">' + _esc(product.name) + '</text></svg>')}" 
                                         alt="${_esc(product.name)}" 
                                         class="product-main-image" 
                                         id="main-image">
                                    <div class="product-thumbnails">
                                        ${(product.images || []).map((img, i) => `
                                            <img src="${_escAttr(img)}" 
                                                 alt="${_esc(product.name)} ${i + 1}" 
                                                 class="product-thumbnail ${i === 0 ? 'active' : ''}"
                                                 data-action="change-main-image" data-img="${_escAttr(img)}">
                                        `).join('')}
                                    </div>
                                </div>

                                <!-- 商品信息 -->
                                <div class="product-info-detail">
                                    <h1 class="product-title">${_esc(product.name)}</h1>
                                    
                                    <div class="product-price-detail">
                                        <span class="current-price">${CONFIG.currencySymbol}${price.toFixed(2)}</span>
                                        ${originalPrice > price ? `<span class="original-price">${CONFIG.currencySymbol}${originalPrice.toFixed(2)}</span>` : ''}
                                    </div>

                                    ${this.urgency.showStockBar(stock, product.total_stock || stock + 50)}

                                    <!-- SKU选择 -->
                                    ${product.variants && product.variants.length > 0 ? `
                                        <div class="sku-section">
                                            ${product.variant_types.map(type => `
                                                <div class="sku-label">${_esc(type.name)}</div>
                                                <div class="sku-options">
                                                    ${type.options.map(option => `
                                                        <button class="sku-option" 
                                                                data-action="select-sku" data-type="${_escAttr(type.name)}" data-option="${_escAttr(option)}"
                                                                ${option.stock === 0 ? 'disabled' : ''}>
                                                            ${_esc(option.name)}
                                                        </button>
                                                    `).join('')}
                                                </div>
                                            `).join('')}
                                        </div>
                                    ` : ''}

                                    <!-- 数量选择 -->
                                    <div class="quantity-selector">
                                        <button class="quantity-btn" data-action="qty-minus">-</button>
                                        <input type="number" class="quantity-input" id="quantity" value="1" min="1" max="${stock}">
                                        <button class="quantity-btn" data-action="qty-plus">+</button>
                                    </div>

                                    <!-- 吸底按钮（移动端） -->
                                    <div class="sticky-add-to-cart">
                                        <button class="btn btn-secondary" data-action="add-to-cart">加入购物车</button>
                                        <button class="btn btn-primary" data-action="buy-now">立即购买</button>
                                    </div>
                                </div>
                            </div>

                            <!-- 商品详情Tabs -->
                            <div class="product-tabs">
                                <div class="tab-headers">
                                    <button class="tab-header active" data-action="switch-tab" data-tab="detail">商品详情</button>
                                    <button class="tab-header" data-action="switch-tab" data-tab="specs">规格参数</button>
                                    <button class="tab-header" data-action="switch-tab" data-tab="reviews">用户评价 (${reviews.length})</button>
                                </div>

                                <div class="tab-content active" id="tab-detail">
                                    ${product.description ? _esc(product.description) : '<p>暂无详情</p>'}
                                </div>

                                <div class="tab-content" id="tab-specs">
                                    <table style="width:100%; border-collapse:collapse;">
                                        ${product.specs ? Object.entries(product.specs).map(([key, value]) => `
                                            <tr style="border-bottom:1px solid var(--border);">
                                                <td style="padding:12px; font-weight:600; width:30%;">${_esc(key)}</td>
                                                <td style="padding:12px;">${_esc(value)}</td>
                                            </tr>
                                        `).join('') : '<tr><td>暂无规格信息</td></tr>'}
                                    </table>
                                </div>

                                <div class="tab-content" id="tab-reviews">
                                    <div class="reviews-list">
                                        ${reviews.length > 0 ? reviews.map(review => `
                                            <div class="review-item">
                                                <div class="review-header">
                                                    <div class="review-avatar">${_esc(review.author[0])}</div>
                                                    <div>
                                                        <div class="review-author">${_esc(review.author)}</div>
                                                        <div class="stars">${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}</div>
                                                        <div class="review-date">${_esc(review.date)}</div>
                                                    </div>
                                                </div>
                                                <div class="review-content">${_esc(review.content)}</div>
                                                ${review.images && review.images.length > 0 ? `
                                                    <div class="review-images">
                                                        ${review.images.map(img => `<img src="${_escAttr(img)}" alt="评价图片">`).join('')}
                                                    </div>
                                                ` : ''}
                                            </div>
                                        `).join('') : '<p>暂无评价</p>'}
                                    </div>
                                </div>
                            </div>

                            <!-- 相关商品推荐 -->
                            <div class="related-products">
                                <h2 class="section-title">相关推荐</h2>
                                <div class="products-grid" id="related-products">
                                    <!-- 通过JS加载 -->
                                </div>
                            </div>
                        </div>
                    </div>
                `

                // 更新购物车角标
                this.cart.updateBadge();

            } catch (error) {
                console.error('渲染商品详情失败:', error);
                app.innerHTML = '<div class="container" style="text-align:center;padding:80px 0;"><h2>商品不存在</h2><p><a href="#/">返回首页</a></p></div>';
            }
        }

        async renderCart() {
            const app = document.getElementById('app');
            
            if (this.cart.items.length === 0) {
                app.innerHTML = `
                    <div class="cart-page">
                        <div class="container">
                            <div class="empty-cart">
                                <div class="empty-cart-icon">🛒</div>
                                <p class="empty-cart-text">购物车是空的</p>
                                <a href="#/products" class="btn btn-primary">去逛逛</a>
                            </div>
                        </div>
                    </div>
                `;
                return;
            }

            app.innerHTML = `
                <div class="cart-page">
                    <div class="container">
                        <h1 style="margin-bottom:32px;">购物车</h1>
                        
                        <div class="cart-items" id="cart-items">
                            ${this.cart.items.map((item, index) => `
                                <div class="cart-item" data-index="${index}">
                                    <img src="${_escAttr(item.product.image || 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23f0f0f0" width="100" height="100"/></svg>'))}" 
                                         alt="${_esc(item.product.name)}" 
                                         class="cart-item-image">
                                    <div class="cart-item-info">
                                        <div class="cart-item-name">${_esc(item.product.name)}</div>
                                        ${item.variant ? `<div class="cart-item-sku">${Object.entries(item.variant.options || {}).map(([k, v]) => _esc(k) + ': ' + _esc(v)).join(', ')}</div>` : ''}
                                        <div class="cart-item-price">${CONFIG.currencySymbol}${(item.variant ? item.variant.price : item.product.price).toFixed(2)}</div>
                                    </div>
                                    <div class="cart-item-actions">
                                        <div class="cart-item-quantity">
                                            <button data-action="cart-qty-minus" data-index="${index}">-</button>
                                            <span>${item.quantity}</span>
                                            <button data-action="cart-qty-plus" data-index="${index}">+</button>
                                        </div>
                                        <button class="cart-item-remove" data-action="cart-remove" data-index="${index}">🗑️</button>
                                    </div>
                                    <div class="cart-item-subtotal">${CONFIG.currencySymbol}${((item.variant ? item.variant.price : item.product.price) * item.quantity).toFixed(2)}</div>
                                </div>
                            `).join('')}
                        </div>

                        <!-- 优惠券 -->
                        <div class="coupon-section">
                            <h3 style="margin-bottom:12px;">优惠券</h3>
                            <div class="coupon-input-group">
                                <input type="text" class="coupon-input" id="coupon-input" placeholder="输入优惠码">
                                <button class="btn btn-primary btn-sm" data-action="apply-coupon">应用</button>
                            </div>
                            <div class="coupon-message" id="coupon-message"></div>
                        </div>

                        <!-- 价格汇总 -->
                        <div class="cart-summary">
                            <div class="summary-row">
                                <span>小计</span>
                                <span>${CONFIG.currencySymbol}${this.cart.getSubtotal().toFixed(2)}</span>
                            </div>
                            ${this.cart.coupon ? `
                                <div class="summary-row" style="color:var(--success);">
                                    <span>优惠 (${_esc(this.cart.coupon.code)})</span>
                                    <span>-${CONFIG.currencySymbol}${this.cart.getDiscount().toFixed(2)}</span>
                                </div>
                            ` : ''}
                            <div class="summary-row">
                                <span>运费</span>
                                <span>${this.cart.getShipping() === 0 ? '免运费' : CONFIG.currencySymbol + this.cart.getShipping().toFixed(2)}</span>
                            </div>
                            <div class="summary-row total">
                                <span>合计</span>
                                <span>${CONFIG.currencySymbol}${this.cart.getTotal().toFixed(2)}</span>
                            </div>
                            <button class="btn btn-primary btn-block checkout-btn" data-action="nav-checkout">去结算</button>
                        </div>
                    </div>
                </div>
            `;

            this.cart.updateBadge();
        }

        async renderCheckout() {
            const app = document.getElementById('app');
            
            if (this.cart.items.length === 0) {
                app.innerHTML = `
                    <div class="checkout-page">
                        <div class="container">
                            <div class="empty-cart">
                                <p class="empty-cart-text">购物车是空的</p>
                                <a href="#/products" class="btn btn-primary">去逛逛</a>
                            </div>
                        </div>
                    </div>
                `;
                return;
            }

            // 获取保存的地址
            const savedAddress = JSON.parse(localStorage.getItem('sg_last_address') || '{}');

            app.innerHTML = `
                <div class="checkout-page">
                    <div class="container">
                        <h1 style="margin-bottom:32px;">结算</h1>
                        
                        <div class="checkout-content">
                            <div class="checkout-form">
                                <!-- 收货地址 -->
                                <div class="form-section">
                                    <h2 class="form-section-title">收货地址</h2>
                                    <div class="form-group">
                                        <label class="form-label" for="name">收货人姓名</label>
                                        <input type="text" class="form-input" id="name" value="${_escAttr(savedAddress.name || '')}" required>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label" for="phone">手机号码</label>
                                        <input type="tel" class="form-input" id="phone" value="${_escAttr(savedAddress.phone || '')}" required>
                                    </div>
                                    <div class="form-row">
                                        <div class="form-group">
                                            <label class="form-label" for="province">省份</label>
                                            <input type="text" class="form-input" id="province" value="${_escAttr(savedAddress.province || '')}" required>
                                        </div>
                                        <div class="form-group">
                                            <label class="form-label" for="city">城市</label>
                                            <input type="text" class="form-input" id="city" value="${_escAttr(savedAddress.city || '')}" required>
                                        </div>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label" for="district">区/县</label>
                                        <input type="text" class="form-input" id="district" value="${_escAttr(savedAddress.district || '')}" required>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label" for="address">详细地址</label>
                                        <input type="text" class="form-input" id="address" value="${_escAttr(savedAddress.address || '')}" required>
                                    </div>
                                </div>

                                <!-- 配送方式 -->
                                <div class="form-section">
                                    <h2 class="form-section-title">配送方式</h2>
                                    <div class="form-group">
                                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                            <input type="radio" name="shipping" value="standard" checked>
                                            <span>标准快递 (${this.cart.getShipping() === 0 ? '免运费' : CONFIG.currencySymbol + this.cart.getShipping().toFixed(2)})</span>
                                        </label>
                                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;margin-top:8px;">
                                            <input type="radio" name="shipping" value="express">
                                            <span>顺丰速运 (+${CONFIG.currencySymbol}15.00)</span>
                                        </label>
                                    </div>
                                </div>

                                <!-- 支付方式 -->
                                <div class="form-section">
                                    <h2 class="form-section-title">支付方式</h2>
                                    <div class="payment-methods">
                                        {% if payment_wechat %}<div class="payment-method active" data-method="wechat" data-action="select-payment">
                                            <div class="payment-icon">[微信]</div>
                                            <div class="payment-name">微信支付</div>
                                        </div>{% endif %}
                                        {% if payment_alipay %}<div class="payment-method{% if not payment_wechat %} active{% endif %}" data-method="alipay" data-action="select-payment">
                                            <div class="payment-icon">[支付宝]</div>
                                            <div class="payment-name">支付宝</div>
                                        </div>{% endif %}
                                        {% if payment_bank %}<div class="payment-method{% if not payment_wechat and not payment_alipay %} active{% endif %}" data-method="bank" data-action="select-payment">
                                            <div class="payment-icon">[银行卡]</div>
                                            <div class="payment-name">银行卡转账</div>
                                        </div>{% endif %}
                                        {% if payment_paypal %}<div class="payment-method{% if not payment_wechat and not payment_alipay and not payment_bank %} active{% endif %}" data-method="paypal" data-action="select-payment">
                                            <div class="payment-icon">[PayPal]</div>
                                            <div class="payment-name">PayPal</div>
                                        </div>{% endif %}
                                    </div>
                                </div>

                                <!-- 订单备注 -->
                                <div class="form-section">
                                    <h2 class="form-section-title">订单备注</h2>
                                    <div class="form-group">
                                        <textarea class="form-input" id="order-notes" rows="3" placeholder="选填，可备注特殊要求" style="resize:vertical;"></textarea>
                                    </div>
                                </div>
                            </div>

                            <div>
                                <!-- 订单商品 -->
                                <div class="checkout-items">
                                    <h3 style="margin-bottom:16px;">订单商品</h3>
                                    ${this.cart.items.map(item => `
                                        <div class="checkout-item">
                                            <img src="${_escAttr(item.product.image || 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect fill="%23f0f0f0" width="60" height="60"/></svg>'))}" 
                                                 alt="${_esc(item.product.name)}" 
                                                 class="checkout-item-image">
                                            <div class="checkout-item-info">
                                                <div class="checkout-item-name">${_esc(item.product.name)}</div>
                                                ${item.variant ? `<div class="checkout-item-sku">${Object.entries(item.variant.options || {}).map(([k, v]) => _esc(k) + ': ' + _esc(v)).join(', ')}</div>` : ''}
                                                <div style="font-size:14px;color:var(--text-secondary);">x${item.quantity}</div>
                                            </div>
                                            <div class="checkout-item-price">${CONFIG.currencySymbol}${((item.variant ? item.variant.price : item.product.price) * item.quantity).toFixed(2)}</div>
                                        </div>
                                    `).join('')}
                                </div>

                                <!-- 价格汇总 -->
                                <div class="cart-summary">
                                    <div class="summary-row">
                                        <span>商品小计</span>
                                        <span>${CONFIG.currencySymbol}${this.cart.getSubtotal().toFixed(2)}</span>
                                    </div>
                                    ${this.cart.coupon ? `
                                        <div class="summary-row" style="color:var(--success);">
                                            <span>优惠</span>
                                            <span>-${CONFIG.currencySymbol}${this.cart.getDiscount().toFixed(2)}</span>
                                        </div>
                                    ` : ''}
                                    <div class="summary-row">
                                        <span>运费</span>
                                        <span id="shipping-fee">${CONFIG.currencySymbol}${this.cart.getShipping().toFixed(2)}</span>
                                    </div>
                                    <div class="summary-row total">
                                        <span>应付总额</span>
                                        <span id="total-amount">${CONFIG.currencySymbol}${this.cart.getTotal().toFixed(2)}</span>
                                    </div>
                                    <button class="btn btn-primary btn-block place-order-btn" data-action="place-order">立即支付</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // 配送方式切换
            const shippingInputs = document.querySelectorAll('input[name="shipping"]');
            shippingInputs.forEach(input => {
                input.addEventListener('change', (e) => {
                    const shipping = e.target.value;
                    const fee = shipping === 'express' ? 15 : (this.cart.getShipping());
                    document.getElementById('shipping-fee').textContent = CONFIG.currencySymbol + fee.toFixed(2);
                    
                    const total = this.cart.getTotal() + (shipping === 'express' ? 15 : 0);
                    document.getElementById('total-amount').textContent = CONFIG.currencySymbol + total.toFixed(2);
                });
            });
        }

        async renderOrderStatus(orderId) {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="loading"></div>';

            try {
                const order = await this.api.getOrderStatus(orderId);
                
                const statusMap = {
                    'pending': { icon: '⏳', title: '订单待支付', desc: '请尽快完成支付' },
                    'paid': { icon: '✅', title: '支付成功', desc: '我们将尽快为您发货' },
                    'shipped': { icon: '🚚', title: '已发货', desc: '商品正在配送中' },
                    'delivered': { icon: '📦', title: '已送达', desc: '感谢您的购买' },
                    'cancelled': { icon: '❌', title: '订单已取消', desc: '如有问题请联系客服' },
                };

                const status = statusMap[order.status] || statusMap['pending'];

                app.innerHTML = `
                    <div class="order-status-page">
                        <div class="order-status-content">
                            <div class="order-status-icon">${status.icon}</div>
                            <h1 class="order-status-title">${_esc(status.title)}</h1>
                            <p class="order-status-desc">${_esc(status.desc)}</p>
                            <p style="color:var(--text-secondary);margin-bottom:24px;">订单号: ${_esc(orderId)}</p>
                            ${order.status === 'pending' ? `
                                <button class="btn btn-primary btn-lg" data-action="pay-order" data-order-id="${_escAttr(orderId)}">立即支付</button>
                            ` : ''}
                            <div style="margin-top:16px;">
                                <a href="#/" class="btn btn-secondary">返回首页</a>
                            </div>
                        </div>
                    </div>
                `;

                // 如果订单待支付，轮询支付状态
                if (order.status === 'pending') {
                    this.pollPaymentStatus(orderId);
                }

            } catch (error) {
                console.error('查询订单状态失败:', error);
                app.innerHTML = '<div class="container" style="text-align:center;padding:80px 0;"><h2>订单不存在</h2><p><a href="#/">返回首页</a></p></div>';
            }
        }

        pollPaymentStatus(orderId) {
            const check = () => {
                this.api.getOrderStatus(orderId).then(order => {
                    if (order.status !== 'pending') {
                        location.reload();
                    } else {
                        setTimeout(check, 3000);
                    }
                }).catch(() => setTimeout(check, 3000));
            };
            setTimeout(check, 3000);
        }

        async renderProducts() {
            const app = document.getElementById('app');
            app.innerHTML = '<div class="loading"></div>';

            try {
                const products = await this.api.getProducts({ limit: 20 });
                
                app.innerHTML = `
                    <div class="products-section" style="margin-top:var(--header-height);">
                        <div class="container">
                            <h1 class="section-title">全部商品</h1>
                            <div class="products-grid">
                                ${products.map(product => this.renderProductCard(product)).join('')}
                            </div>
                        </div>
                    </div>
                `;

                this.initLazyLoad();
            } catch (error) {
                console.error('加载商品失败:', error);
            }
        }

        renderAbout() {
            const app = document.getElementById('app');
            app.innerHTML = `
                <div style="margin-top:var(--header-height);padding:80px 0;">
                    <div class="container">
                        <h1 style="margin-bottom:32px;">关于我们</h1>
                        <p>品牌故事内容...</p>
                    </div>
                </div>
            `;
        }

        renderContact() {
            const app = document.getElementById('app');
            app.innerHTML = `
                <div style="margin-top:var(--header-height);padding:80px 0;">
                    <div class="container">
                        <h1 style="margin-bottom:32px;">联系我们</h1>
                        <p>联系方式内容...</p>
                    </div>
                </div>
            `;
        }

        renderHelp() {
            const app = document.getElementById('app');
            app.innerHTML = `
                <div style="margin-top:var(--header-height);padding:80px 0;">
                    <div class="container">
                        <h1 style="margin-bottom:32px;">帮助中心</h1>
                        <p>帮助文档内容...</p>
                    </div>
                </div>
            `;
        }
    }

    // ==================== 全局函数 ====================
    // 切换主图
    function changeMainImage(thumb, src) {
        document.getElementById('main-image').src = src;
        document.querySelectorAll('.product-thumbnail').forEach(t => t.classList.remove('active'));
        thumb.classList.add('active');
    }

    // 切换SKU
    function selectSku(btn, type, value) {
        const parent = btn.parentElement;
        parent.querySelectorAll('.sku-option').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }

    // 更新数量
    function updateQuantity(change) {
        const input = document.getElementById('quantity');
        let value = parseInt(input.value) + change;
        if (value < 1) value = 1;
        input.value = value;
    }

    // 添加到购物车
    function addToCart() {
        // 获取当前商品和SKU信息
        const product = window.currentProduct;
        const quantity = parseInt(document.getElementById('quantity').value);
        
        cart.addItem(product, window.currentVariant, quantity);
        alert('已添加到购物车');
    }

    // 立即购买
    function buyNow() {
        addToCart();
        router.navigate('/checkout');
    }

    // 移除购物车商品
    function removeCartItem(index) {
        if (confirm('确定要移除这个商品吗？')) {
            cart.removeItem(index);
            router.handleRoute(); // 重新渲染
        }
    }

    // 应用优惠券
    let _lastCouponAttempt = 0;
    const COUPON_COOLDOWN = 3000; // 3秒冷却

    async function applyCoupon() {
        const now = Date.now();
        if (now - _lastCouponAttempt < COUPON_COOLDOWN) {
            const messageEl = document.getElementById('coupon-message');
            messageEl.textContent = '请稍后再试';
            messageEl.className = 'coupon-message error';
            return;
        }
        _lastCouponAttempt = now;

        const code = document.getElementById('coupon-input').value.trim();
        const messageEl = document.getElementById('coupon-message');
        
        if (!code) {
            messageEl.textContent = '请输入优惠码';
            messageEl.className = 'coupon-message error';
            return;
        }

        const result = await cart.applyCoupon(code);
        messageEl.textContent = result.message;
        messageEl.className = 'coupon-message ' + (result.success ? 'success' : 'error');
        
        if (result.success) {
            router.handleRoute(); // 重新渲染以显示优惠
        }
    }

    // 选择支付方式
    function selectPayment(el) {
        document.querySelectorAll('.payment-method').forEach(m => m.classList.remove('active'));
        el.classList.add('active');
    }

    // 提交订单
    async function placeOrder() {
        // 验证表单
        const name = document.getElementById('name').value;
        const phone = document.getElementById('phone').value;
        const province = document.getElementById('province').value;
        const city = document.getElementById('city').value;
        const district = document.getElementById('district').value;
        const address = document.getElementById('address').value;
        const notes = document.getElementById('order-notes').value;

        if (!name || !phone || !province || !city || !district || !address) {
            alert('请填写完整的收货地址');
            return;
        }

        // 保存地址
        const addressData = { name, phone, province, city, district, address };
        localStorage.setItem('sg_last_address', JSON.stringify(addressData));

        // 获取支付方式
        const paymentMethod = document.querySelector('.payment-method.active').dataset.method;

        // 获取配送方式
        const shippingMethod = document.querySelector('input[name="shipping"]:checked').value;

        // 构建订单数据
        const orderData = {
            items: cart.items,
            address: addressData,
            payment_method: paymentMethod,
            shipping_method: shippingMethod,
            notes: notes,
            coupon: cart.coupon,
        };

        // 显示loading
        const loading = document.createElement('div');
        loading.className = 'loading-overlay';
        loading.innerHTML = '<div class="loading-spinner"><div class="loading"></div><p>提交订单中...</p></div>';
        document.body.appendChild(loading);

        try {
            const result = await api.createOrder(orderData);
            
            // 清空购物车
            cart.clear();
            
            // 跳转到支付
            if (result.payment_url) {
                window.location.href = result.payment_url;
            } else {
                router.navigate('/order/' + result.order_id);
            }
        } catch (error) {
            console.error('创建订单失败:', error);
            alert('创建订单失败，请重试');
        } finally {
            loading.remove();
        }
    }

    // 支付订单
    async function payOrder(orderId) {
        try {
            const result = await api.getPaymentUrl(orderId);
            if (result.payment_url) {
                window.location.href = result.payment_url;
            }
        } catch (error) {
            console.error('获取支付链接失败:', error);
            alert('支付失败，请重试');
        }
    }

    // 切换Tab
    function switchTab(header, tabId) {
        document.querySelectorAll('.tab-header').forEach(h => h.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        header.classList.add('active');
        document.getElementById('tab-' + tabId).classList.add('active');
    }

    // ==================== 初始化 ====================
    const app = new ShopApp();
    const router = new Router();
    const api = new ShopAPI();
    const cart = new Cart();
    const urgency = new UrgencyModule();

    // 路由监听
    window.addEventListener('hashchange', () => router.handleRoute());

    // 首次加载
    router.handleRoute();

    // 应用主题
    const savedTheme = localStorage.getItem('sg_theme') || CONFIG.theme;
    applyTheme(savedTheme);

    // 返回顶部
    const backToTopBtn = document.getElementById('back-to-top');
    window.addEventListener('scroll', () => {
        if (backToTopBtn) {
            backToTopBtn.classList.toggle('show', window.scrollY > 300);
        }
    });
    if (backToTopBtn) {
        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // 移动端导航切换
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('show');
        });
    }

    // 移动端底部导航高亮
    function updateMobileNav() {
        const hash = location.hash || '#/';
        document.querySelectorAll('.mobile-nav-item').forEach(link => {
            const href = link.getAttribute('href');
            link.classList.toggle('active', href === hash);
        });
    }
    window.addEventListener('hashchange', updateMobileNav);
    updateMobileNav();

    // 紧迫感弹窗（延迟5秒显示）
    setTimeout(() => urgency.showRecentBuyer(), 5000);

    // 注入Google Analytics
    if (CONFIG.gaId) {
        const gaScript = document.createElement('script');
        gaScript.async = true;
        gaScript.src = 'https://www.googletagmanager.com/gtag/js?id=' + CONFIG.gaId;
        document.head.appendChild(gaScript);
        
        window.dataLayer = window.dataLayer || [];
        function gtag() { dataLayer.push(arguments); }
        gtag('js', new Date());
        gtag('config', CONFIG.gaId);
    }

    // 注入百度统计
    if (CONFIG.baiduTongjiId) {
        const baiduScript = document.createElement('script');
        baiduScript.src = 'https://hm.baidu.com/hm.js?' + CONFIG.baiduTongjiId;
        document.head.appendChild(baiduScript);
    }

    console.log('SG电商模板已加载 | 主题:', savedTheme, '| 店铺:', CONFIG.shopName);
    </script>
{% if not is_pro %}
    <a class="sg-watermark" href="https://auto-site-builder.onrender.com" target="_blank" rel="noopener" title="由SG智能建站生成，升级专业版去除水印">
        <svg viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        SG建站
    </a>
    {% endif %}

<script>
// ── Shop事件委托（替代inline onclick） ──
document.addEventListener('click', function(e) {
    var el = e.target.closest('[data-action]');
    if (!el) return;
    var action = el.getAttribute('data-action');
    switch(action) {
        case 'nav-cart': location.hash = '#/cart'; break;
        case 'add-to-cart': addToCart(); break;
        case 'buy-now': buyNow(); break;
        case 'apply-coupon': applyCoupon(); break;
        case 'place-order': placeOrder(); break;
        case 'qty-minus': updateQuantity(-1); break;
        case 'qty-plus': updateQuantity(1); break;
        case 'switch-tab': switchTab(el, el.getAttribute('data-tab')); break;
        case 'nav-checkout': router.navigate('/checkout'); break;
        case 'select-payment': selectPayment(el); break;
        case 'cart-qty-minus':
            var idx = parseInt(el.getAttribute('data-index'));
            cart.updateQuantity(idx, cart.items[idx].quantity - 1); break;
        case 'cart-qty-plus':
            var idx2 = parseInt(el.getAttribute('data-index'));
            cart.updateQuantity(idx2, cart.items[idx2].quantity + 1); break;
        case 'cart-remove':
            removeCartItem(parseInt(el.getAttribute('data-index'))); break;
        case 'view-product':
            router.navigate('/product/' + el.getAttribute('data-id')); break;
        case 'change-main-image':
            changeMainImage(el, el.getAttribute('data-img')); break;
        case 'select-sku':
            selectSku(el, el.getAttribute('data-type'), el.getAttribute('data-option')); break;
        case 'pay-order':
            payOrder(el.getAttribute('data-order-id')); break;
        case 'customer-service':
            var url = el.getAttribute('data-url');
            if (url) window.open(url, '_blank'); break;
    }
});
</script>

</body>
</html>"""

# ==================== 电商前端交互JS（单独变量） ====================
SHOP_JS = """
// 这个变量包含可单独注入的JS代码
// 主要用于需要动态更新JS逻辑的场景

(function() {
    'use strict';
    
    // 防抖函数
    function debounce(fn, delay) {
        let timer;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    // 节流函数
    function throttle(fn, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                fn.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // 图片延迟加载增强
    function enhanceLazyLoad() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        img.classList.remove('lazy-placeholder');
                        observer.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    // 表单验证
    function validateForm(form) {
        const inputs = form.querySelectorAll('[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                isValid = false;
                input.style.borderColor = 'var(--danger)';
                
                input.addEventListener('input', function() {
                    this.style.borderColor = this.value.trim() ? 'var(--border)' : 'var(--danger)';
                });
            } else {
                input.style.borderColor = 'var(--border)';
            }
        });

        return isValid;
    }

    // 数字格式化
    function formatNumber(num) {
        return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');
    }

    // 价格格式化
    function formatPrice(price) {
        return CONFIG.currencySymbol + parseFloat(price).toFixed(2);
    }

    // 日期格式化
    function formatDate(date) {
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return year + '-' + month + '-' + day;
    }

    // 通知提示
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            padding: 16px 24px;
            background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--primary)'};
            color: white;
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow);
            z-index: 10000;
            animation: slideIn 0.3s ease;
            max-width: 320px;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // 添加CSS动画
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);

    // 导出到全局
    window.Utils = {
        debounce,
        throttle,
        enhanceLazyLoad,
        validateForm,
        formatNumber,
        formatPrice,
        formatDate,
        showNotification,
    };

    console.log('SG电商工具库已加载');
})();
"""

# ==================== 辅助函数 ====================
def get_template(theme_name='tech_blue', **kwargs):
    """获取指定主题的完整HTML模板
    
    Args:
        theme_name: 主题名称 (tech_blue/luxury_gold/fresh_green)
        **kwargs: 覆盖默认配置的参数
    
    Returns:
        渲染后的HTML字符串
    """
    import json
    from jinja2 import Template
    
    theme = THEMES.get(theme_name, THEMES['tech_blue'])
    
    # 默认配置
    config = {
        'shop_name': '我的店铺',
        'shop_slogan': '优质商品，放心购买',
        'meta_description': '欢迎来到我的店铺，这里有最优质的商品',
        'api_base_url': 'https://auto-site-builder.onrender.com',
        'site_id': 'default',
        'theme': theme_name,
        'currency': 'CNY',
        'currency_symbol': '¥',
        'customer_service_url': '#',
        'ga_id': '',
        'baidu_tongji_id': '',
        'current_year': 2024,
        # 收款方式配置（默认开启微信+支付宝）
        'payment_wechat': True,
        'payment_alipay': True,
        'payment_bank': False,
        'payment_paypal': False,
        'payment_card': False,
        # 收款账号信息（需用户配置，不显示在页面中，仅用于订单提交）
        'wechat_pay_id': '',
        'alipay_account': '',
        'bank_name': '',
        'bank_account': '',
        'bank_holder': '',
        'paypal_id': '',
        # 联系方式
        'contact_email': '',
        'contact_phone': '',
        'contact_wechat': '',
        'json_ld': json.dumps({
            '@context': 'https://schema.org',
            '@type': 'Store',
            'name': '我的店铺',
            'description': '优质商品，放心购买',
        }, ensure_ascii=False),
    }
    
    # 添加主题配色变量
    config['theme'] = theme
    
    # 用kwargs覆盖默认值
    config.update(kwargs)
    
    # 如果kwargs中传入了theme_name字符串，更新theme字典
    if 'theme' not in kwargs and 'theme_name' in kwargs:
        config['theme'] = THEMES.get(kwargs['theme_name'], theme)
    
    # 使用Jinja2渲染模板
    template = Template(SHOP_TEMPLATE)
    return template.render(**config)


def validate_template():
    """验证模板的完整性"""
    errors = []
    
    # 检查主题定义
    if not THEMES or len(THEMES) != 3:
        errors.append('主题定义不完整')
    
    # 检查模板变量
    required_vars = ['{{ shop_name }}', '{{ api_base_url }}', '{{ site_id }}', '{{ theme }}']
    for var in required_vars:
        if var not in SHOP_TEMPLATE:
            errors.append(f'模板缺少变量: {var}')
    
    # 检查JS功能
    required_functions = ['Router', 'ShopAPI', 'Cart', 'ShopApp']
    for func in required_functions:
        if func not in SHOP_JS:
            errors.append(f'JS缺少类/函数: {func}')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
    }


# 导出
__all__ = ['THEMES', 'SHOP_TEMPLATE', 'SHOP_JS', 'get_template', 'validate_template']
