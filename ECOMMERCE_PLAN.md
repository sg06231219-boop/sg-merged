# SG v5.0 电商大改造计划

## 架构设计

### 核心思路
SG是SaaS建站平台（类Shopify），每个生成的站点有自己的商品/订单/用户数据。
生成的电商页面是动态前端，调用SG平台API实现购物车/下单/支付。

### 新增文件
1. `core/ecommerce/store.py` — 电商数据层（商品/订单/购物车/优惠券/运费）
2. `apis/routes/ecommerce.py` — 前台电商API（商品列表/详情/购物车/结算/评价）
3. `apis/routes/payment.py` — 支付处理（微信/支付宝/PayPal回调）
4. 更新 `core/backends/template/jinja2.py` — 新增电商模板(shop模式)
5. 更新 `apis/routes/auth.py` — 扩展管理员API
6. 重写 `static/admin.html` — 电商管理后台

### 数据模型（JSON文件存储）
- `data/products_{site_id}.json` — 商品数据
- `data/orders_{site_id}.json` — 订单数据
- `data/coupons_{site_id}.json` — 优惠券
- `data/reviews_{site_id}.json` — 评价
- `data/shipping_{site_id}.json` — 运费模板
- `data/payment_config_{site_id}.json` — 支付配置
- `data/site_config_{site_id}.json` — 站点配置（主题/语言/货币等）

### API设计
前台(无需认证):
- GET /api/v1/shop/{site_id}/products — 商品列表
- GET /api/v1/shop/{site_id}/products/{pid} — 商品详情
- POST /api/v1/shop/{site_id}/cart — 购物车操作
- POST /api/v1/shop/{site_id}/checkout — 创建订单
- GET /api/v1/shop/{site_id}/reviews — 评价列表

支付回调:
- POST /api/v1/payment/wechat/callback — 微信支付回调
- POST /api/v1/payment/alipay/callback — 支付宝回调
- POST /api/v1/payment/paypal/callback — PayPal回调

管理API(需JWT):
- CRUD /api/v1/admin/products — 商品管理
- CRUD /api/v1/admin/orders — 订单管理
- CRUD /api/v1/admin/coupons — 优惠券管理
- GET/PUT /api/v1/admin/site-config — 站点配置
- GET/PUT /api/v1/admin/payment-config — 支付配置
- GET/PUT /api/v1/admin/shipping-config — 运费配置
