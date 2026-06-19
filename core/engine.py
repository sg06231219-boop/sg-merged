"""
core.engine — SiteBuilderEngine 核心编排器

这是整个项目的核心，负责：
1. 加载 AI 和模板后端（通过 loaders 自动选择最优）
2. 接收用户输入 → AI 生成内容 → 模板渲染 → 输出完整 HTML
3. 支持单页着陆、完整多页网站、定价页面三种模式
4. 提供同步 / 异步两种调用方式
5. 支持并发多页生成（asyncio）

类比：就像 asyncio.BaseEventLoop 定义了 run_forever / create_task 等接口，
      SiteBuilderEngine 定义了 build_site / build_landing 等接口，
      由不同的 AI 和模板后端实现具体逻辑。
"""

from __future__ import annotations

import asyncio
import logging
import hashlib
import uuid
from pathlib import Path
from typing import Any

from core.backends.base import AIBackend, TemplateBackend
from core.loaders import AIBackendLoader, TemplateBackendLoader
from core.exceptions import AIGenerationError, TemplateRenderError, SiteBuilderError

logger = logging.getLogger("site-builder.engine")

# ═══════════════════════════════════════════════════════════
#  Prompt 模板 — 仿 AI 提示设计
# ═══════════════════════════════════════════════════════════

def _landing_prompt(info: dict[str, str]) -> str:
    """生成着陆页的 AI 提示"""
    _industry = info.get('industry', '通用').lower()

    # ── 行业特异化创作指引 ──
    _industry_guide = ""
    if any(k in _industry for k in ('tech', 'saas', '软件', '科技', 'it', '云')):
        _industry_guide = """
### 行业创作指引：Tech / SaaS
痛点：①开发团队40%时间花在重复造轮子②系统出问题靠人肉巡检，平均发现故障>15分钟③多系统数据孤岛，月度报表要3人做一周
术语：SLA、API/Webhook/SDK、CI/CD、RBAC、灰度发布、QPS、冷启动
常问FAQ：①我现有BI好好的为什么要换？②数据安全怎么保证，能私有化部署吗？③免费版和付费版功能差多少？
写法：像给CTO写的方案摘要，用数据说话，忌营销腔。feature写明能力边界如"REST API，批量导出上限1万条"。CTA用"免费试用14天""查看API文档"。testimonials用技术背景人(CTO/技术总监/后端负责人)。
"""
    elif any(k in _industry for k in ('ecommerce', '零售', '电商', '购物', '商城', '贸易', '消费')):
        _industry_guide = """
### 行业创作指引：电商 / 零售
痛点：①退货率>25%，尺码问题占60%②复购率低，用户买完就流失③上新后3天流量断崖，不会追投
术语：SKU、GMV、ROI、客单价、复购率、加购率、动销率、私域、种草
常问FAQ：①尺码不准能免费退吗？②和旗舰店比哪个更便宜？③团购和单买差多少？
写法：hero直接亮价格/折扣，用限时限量制造紧迫感。产品描述像实物讲解：材质手感、尺寸、使用场景。testimonials写买家秀口吻。FAQ要覆盖退货/尺码/真假。
"""
    elif any(k in _industry for k in ('教育', '培训', '课程', '学', '考')):
        _industry_guide = """
### 行业创作指引：教育 / 培训
痛点：①学员完课率不到30%，学了就弃②课程大纲模糊，不知道学了能干嘛③价格不透明，藏着附加收费
术语：完课率、提分、模考、批改、督学、开班、课时、学分、答疑
常问FAQ：①零基础能学会吗，跟不上怎么办？②学完真能找到工作/考过吗？③和XX课程比哪个更适合我？
写法：列课程大纲结构(不是"系统课程"而是"模块1：XX→模块2：XX")。testimonials写学员成果：分数提升、拿offer、项目上线。师资写具体背景("8年一线教学，原XX机构教研组长")。CTA用"试听第一课""查看课程大纲"。
"""
    elif any(k in _industry for k in ('医疗', '健康', '医', '药', '诊', '保健')):
        _industry_guide = """
### 行业创作指引：医疗 / 健康
痛点：①患者等2小时看5分钟，满意度极低②检查报告看不懂，没人解释③线上问诊不敢信，怕遇到假医生
术语：门诊、住院、体检、问诊、处方、医嘱、随访、转诊、预约挂号、医保报销
常问FAQ：①医保能用吗，报销比例多少？②检查前需要准备什么，要空腹吗？③线上问诊能开处方吗？
写法：合规第一——绝不承诺疗效，用"改善""辅助""管理"代替"治愈""根治"。展示资质认证。案例脱敏。testimonials侧重服务体验而非疗效。FAQ覆盖医保/准备/处方。
"""
    elif any(k in _industry for k in ('外贸', 'b2b', '出口', '进出口', '跨境', 'wholesale')):
        _industry_guide = """
### 行业创作指引：外贸 / B2B
痛点：①客户只比价格，说不清自己到底值在哪②打样3轮客户跑了，前期投入全白费③交期一拖再拖，老客户催急了翻脸
术语：MOQ、FOB/CIF、交期、OEM/ODM、打样、验厂、信用证(L/C)、质检、报关
常问FAQ：①打样要多久，费用能退吗？②能做OEM/ODM吗，最小起订量多少？③付款方式有哪些，支持信用证吗？
写法：必须写MOQ、交期、认证(CE/FDA/ISO)。工厂实景：产线数、质检流程、年产能。价格用FOB/CIF标明。testimonials写采购经理视角。FAQ覆盖打样/OEM/付款。
"""
    elif any(k in _industry for k in ('本地', '服务', '家政', '维修', '装修', '搬家', '保洁', '门店')):
        _industry_guide = """
### 行业创作指引：本地服务
痛点：①叫了不来，来了又推迟，时间全浪费②修完又坏，没售后，二次收费③价格说不清，上门就开始加价
术语：上门、到店、工时费、配件费、起步价、预约、师傅、持证、质保期
常问FAQ：①上门收不收上门费，修不好收费吗？②师傅持什么证，有质保吗？③周末能约吗，大概多久能到？
写法：写明服务半径和响应时间。上门vs到店流程明确。师傅资质写从业年限+持证。价格透明：起步价+计价方式，忌"价格面议"。testimonials写周边居民口吻。
"""
    elif any(k in _industry for k in ('餐饮', '美食', '外卖', '饭店', '火锅', '奶茶', '咖啡', '烘焙')):
        _industry_guide = """
### 行业创作指引：餐饮 / 美食
痛点：①新客进店不知道点什么，看菜单纠结5分钟②外卖图片好看实物差，差评率飙升③回头客少，吃完就忘，没有复购动力
术语：堂食、外卖、翻台率、客单价、招牌菜、时令菜、午市/晚市、预约制、套餐
常问FAQ：①有包间吗，能坐多少人？②外卖大概多久到，配送范围多大？③有优惠活动吗，团购能和会员叠加吗？
写法：hero区亮招牌菜+价格区间，用"现炒""每日现送""慢炖6小时"等工艺词。features写具体菜品而非笼统"精选食材"。testimonials写食客口吻："点了XX和XX，XX绝了但XX一般"。CTA用"看今日菜单""预约包间"。
"""
    elif any(k in _industry for k in ('法律', '律所', '律师', '法务', '合规', '知识产权')):
        _industry_guide = """
### 行业创作指引：法律 / 律所
痛点：①普通人对法律术语一头雾水，不知道自己有没有理②律师费不透明，怕被按小时坑③案件进度完全黑箱，问了也没人回
术语：咨询、代理、胜诉率、标的额、执业年限、专业领域、法律意见书、合规审查
常问FAQ：①咨询收费吗，大概多少？②我这情况打官司有胜算吗？③你们擅长什么领域的案件？
写法：合规第一——绝不承诺胜诉，用"成功代理""协助处理"代替"包赢""必胜"。写明执业证号和擅长领域。testimonials侧重服务体验而非案件结果。FAQ覆盖收费/领域/流程。
"""
    elif any(k in _industry for k in ('金融', '理财', '保险', '贷款', '投资', '基金', '银行')):
        _industry_guide = """
### 行业创作指引：金融 / 保险
痛点：①产品条款密密麻麻看不懂，隐藏费用多②收益说的好听，实际到手差一截③出险了赔不到，各种免责条款
术语：年化收益率、费率、保额、免赔额、犹豫期、等待期、分红、净值、回撤
常问FAQ：①手续费多少，有隐性收费吗？②提前赎回/退保有损失吗？③收益是保底的还是浮动的？
写法：合规第一——绝不承诺收益，用"历史年化""预期收益"并标注"过往业绩不代表未来"。写明费率和风险等级。testimonials侧重服务体验而非投资收益。CTA用"查看产品详情""预约专属顾问"。
"""
    elif any(k in _industry for k in ('宠物', '猫', '狗', '兽医', '宠物医院', '宠物店')):
        _industry_guide = """
### 行业创作指引：宠物
痛点：①宠物看病比人贵，一次几百上千还不知道有没有必要②寄养不放心，怕虐待怕交叉感染③买的粮食零食不知道安不安全
术语：驱虫、疫苗、绝育、体检、寄养、洗护、处方粮、幼犬/成犬、品种认证
常问FAQ：①驱虫多久做一次，内驱外驱都要吗？②寄养需要什么证件，能看监控吗？③处方粮和普通粮有什么区别？
写法：hero区写服务范围+价格透明度。features写具体项目而非"专业护理"。testimonials写铲屎官口吻："带猫去绝育，术后护理很细心，就是等位有点久"。CTA用"预约体检""看今日优惠"。
"""
    else:
        _industry_guide = """
### 行业创作指引：通用
- 找到该行业最核心的1-2个决策因素，文案围绕它展开
- 用行业内的具体术语和数字建立专业感
- testimonials体现典型客户画像和使用场景
"""

    prompt = f"""[mode: landing] 你是10年转化率优化师，帮200+品牌从0到月入10万+。你写的每个字都要说服持怀疑态度的访客——不是让同行觉得"文案不错"，而是让陌生人看了就想下一步。

## 商家信息
- 名称: {info.get('name', '未知商家')}
- 行业: {info.get('industry', '通用')}
- 业务描述: {info.get('description', '专业服务')}
- 目标关键词: {info.get('keywords', '')}
- 目标客户: {info.get('audience', '')}

{_industry_guide}

## 🚫 绝对禁止
1. 禁止词表：引领、卓越、领先、一站式、全方位、专业、优质、高端、极致、赋能、致力于、旨在、闭环、矩阵、生态、打法、颗粒度、抓手、底层逻辑、降本增效、协同 —— 用具体事实替代
2. 禁止占位符：电话/邮箱/地址不许"xxx""XX""某某"，没有就留空字符串""
3. 禁止AI编造联系信息：email/phone/address商家没提供就必须留空字符串""，不许自己编一个
3. 禁止全5星：3条评价至少1条≤4星，写出具体不满
4. 禁止假大空数字：不许"大幅提升""显著增加"，必须"从月均23单到月均156单"有起止
5. 禁止自夸FAQ：不许"你们有什么优势""怎么联系"这种
6. 禁止假统计：不许"4.8/5评分""2360+评价""98%推荐率"
7. 禁止空洞feature标题：不许纯形容词如"精准分析""实时监控""定制化服务"

## ✅ 必须做到
- hero_headline格式：痛点场景+解决方案，如"3分钟看透业务数据，告别报表焦虑"，品牌名放logo不在标题堆砌
- feature标题：动词+名词，6-10字，如"多维度数据交叉验证""秒级异常检测与告警""按业务场景配置分析模型"
- feature描述：至少1个具体数字+1个使用场景，如"支持50+数据源实时接入，3分钟完成数据清洗，准确率99.2%"
- testimonials每条含：使用时长("用了3个月")、场景("季度复盘做数据看板")、对比("之前Excel手动做，现在5分钟")；至少1条含真实不满("学习曲线陡，头两周踩坑")；人名用职场称呼如"老周""Amy""赵工"
- stats必须有起点和终点："从0到860家企业""全年宕机<53分钟，SLA 99.9%"
- FAQ 5个问题必须覆盖：①对比顾虑②安全顾虑③价格顾虑④迁移顾虑⑤适用性顾虑
- CTA说清下一步："30秒填表，当天收到方案""注册即开通，无需信用卡"，不许"立即咨询""免费试用"

## 输出格式（严格JSON）
{{
  "meta_title": "50-60字，含品牌名+核心关键词+地域/场景词",
  "meta_description": "120-160字，含行动号召，自然融入2-3个关键词",
  "meta_keywords": "5-8个关键词，逗号分隔，从核心到长尾",
  "hero_headline": "8-15字，痛点场景+解决方案，如'3分钟看透业务数据，告别报表焦虑'，禁止品牌名堆砌",
  "hero_subheadline": "20-40字，补充具体收益或数据",
  "hero_cta": "4-8字，动词开头，说清下一步会发生什么",
  "features_title": "6-8字板块标题",
  "features": [
    {{"title": "6-10字，动词+名词如'多维度数据交叉验证'，禁纯形容词", "description": "20-40字，至少1个具体数字+1个使用场景"}},
    ...共4个
  ],
  "about_title": "关于板块标题",
  "about_content": "两段<p>，第一段品牌故事/初心(50-80字)，第二段成果数据(50-80字，含起止数字)",
  "testimonials_title": "客户评价标题",
  "stats": [
    {{"value": "有起止的数字如'从0到860家'或'全年宕机<53分钟，SLA 99.9%'", "label": "6字以内标签"}},
    ...共3条
  ],
  "partner_brands": [],
  "partner_heading": "合作伙伴",
  "testimonials": [
    {{"name": "职场称呼如老周/Amy/赵工/李姐", "role": "公司+职位", "rating": "3-5，至少1条≤4", "text": "40-70字，含使用时长+场景+对比，至少1条含真实不满"}},
    ...共3条
  ],
  "process_title": "服务流程/如何合作/使用步骤",
  "process_subtitle": "10字以内副标题",
  "process_steps": [
    {{"title": "6-10字步骤名", "desc": "15-25字说明，含具体时间或动作"}},
    ...共3步
  ],
  "faq_title": "常见问题",
  "faq": [
    {{"q": "真实决策纠结点", "a": "30-60字，含具体数据或流程"}},
    ...共5个，覆盖：对比/安全/价格/迁移/适用性顾虑
  ],
  "cta_headline": "底部CTA标题，制造价值感",
  "cta_subheadline": "补充保障或服务承诺",
  "cta_button": "4-8字，说清下一步动作",
  "cta_guarantee": "具体保障如'7天无理由退款'，没有就不填",
  "footer_text": "版权文字，含品牌名",
  "email": "商家邮箱，商家没提供就留空字符串\"\"",
  "phone": "商家电话，商家没提供就留空字符串\"\"",
  "address": "商家地址/城市，商家没提供就留空字符串\"\"",
  "primary_color": "品牌主色十六进制(如#0d7c3e)，物流绿/餐饮红/科技蓝/医疗青绿/法律深灰"
}}

## 文案要求
1. 用事实替代形容词："卓越品质"→"3道质检，退货率0.3%"
2. 评价像真人：有褒有贬有场景有对比，不是广告软文
3. 流程贴合行业：电商浏览→下单→收货; SaaS注册→配置→上线; 教育试听→报名→开课
4. SEO自然融入关键词，不堆砌
5. 中文撰写，口语化但不随意
6. 严格遵循上方行业创作指引

只返回JSON，不要markdown代码块。"""
    return prompt


def _site_prompt(info: dict[str, str]) -> str:
    """生成完整网站的 AI 提示"""
    _industry = info.get('industry', '通用').lower()

    _industry_guide = ""
    if any(k in _industry for k in ('tech', 'saas', '软件', '科技', 'it', '云')):
        _industry_guide = """
### 行业创作指引：Tech / SaaS
- hero区用"开发者实测""API响应时间XXms""可用率99.97%"这类数据
- services写具体能力："REST API / Webhook推送 / 批量导入导出(每次1万条)"
- about里写技术栈、团队规模、服务过的客户量级
- team人员写真实技术背景："张XX，CTO，前XX公司技术总监，10年分布式系统经验"
- values用工程师文化："文档优先""持续部署""开放API"
- products写定价阶梯、功能边界、集成列表
- blog文章写技术教程、API最佳实践、行业白皮书
"""
    elif any(k in _industry for k in ('ecommerce', '零售', '电商', '购物', '商城', '贸易', '消费')):
        _industry_guide = """
### 行业创作指引：电商 / 零售
- hero区直接亮价格带或限时活动："春季上新，全场2件8折"
- services写售后保障："7天无理由""运费险""上门取件"
- products写具体SKU信息：材质、尺码表、库存状态、用户评分
- testimonials写买家秀风格："图3是实拍，比图片显瘦"
- blog写搭配指南、穿搭教程、用户晒单
"""
    elif any(k in _industry for k in ('教育', '培训', '课程', '学', '考')):
        _industry_guide = """
### 行业创作指引：教育 / 培训
- hero区用学员成果："2024年87%学员提分30+"
- services写课程体系："基础班→强化班→冲刺班，分层教学"
- about写师资背景和通过率数据
- team写老师真实履历："李XX，数学主讲，15年教龄，原XX学校教研组长"
- products写课程大纲、课时安排、配套资料
- testimonials写学员/家长评价，含具体分数变化
- FAQ要有"零基础能跟上吗""有没有班主任督促"
"""
    elif any(k in _industry for k in ('医疗', '健康', '医', '药', '诊', '保健')):
        _industry_guide = """
### 行业创作指引：医疗 / 健康
- 合规：绝不用"治愈""根治""包好"，用"改善""管理""辅助调理"
- hero区写资质和特色科室，不写疗效承诺
- services写检查项目、就诊流程，标注是否需要空腹/预约
- about写执业许可证号、医生执业证号（可脱敏）
- team写医生真实职称和从业年限，不夸大
- testimonials写就诊体验，不写疗效评价
- FAQ要有"医保报销比例""检查结果多久出"
"""
    elif any(k in _industry for k in ('外贸', 'b2b', '出口', '进出口', '跨境', 'wholesale')):
        _industry_guide = """
### 行业创作指引：外贸 / B2B
- hero区写MOQ、交期、认证："MOQ 500件，交期15天，通过CE/FDA认证"
- services写OEM/ODM能力、打样流程、验厂安排
- about写工厂面积、产线数量、年产能、合作品牌
- team写外贸经理背景："王XX，外贸总监，8年B2B出口经验，英语/西班牙语"
- products写详细规格、包装方式、运输建议
- testimonials写采购经理视角：交期稳定性、品控水平、沟通效率
- FAQ要有"打样费能退吗""支持第三方验货吗""付款方式"
"""
    elif any(k in _industry for k in ('本地', '服务', '家政', '维修', '装修', '搬家', '保洁', '门店')):
        _industry_guide = """
### 行业创作指引：本地服务
- hero区写服务半径和响应时间："主城三区，30分钟上门"
- services写具体项目明细和计价方式，避免"价格面议"
- about写从业年限、服务过的家庭/企业数量
- team写师傅持证情况："持有电工证/空调安装证/健康证"
- testimonials写周边居民口吻，含具体门牌号或小区名（可化名）
- FAQ要有"怎么预约""上门前需要准备什么""有售后保障吗"
"""
    elif any(k in _industry for k in ('餐饮', '美食', '外卖', '饭店', '火锅', '奶茶', '咖啡', '烘焙')):
        _industry_guide = """
### 行业创作指引：餐饮 / 美食
- hero区亮招牌菜+价格："招牌酸菜鱼38元起，现杀现做"
- services写具体菜品和用餐场景：堂食/外卖/包间/宴席
- about写食材来源和厨师背景："主厨8年粤菜经验，食材每日凌晨4点从批发市场直采"
- team写厨师/店长真实履历
- products写套餐和招牌菜，含价格和份量
- testimonials写食客口吻："XX绝了但XX一般"
- FAQ要有"有包间吗""外卖多久到""能开发票吗"
"""
    elif any(k in _industry for k in ('法律', '律所', '律师', '法务', '合规', '知识产权')):
        _industry_guide = """
### 行业创作指引：法律 / 律所
- hero区写专业领域和执业年限："专注商事诉讼15年"
- services写具体案件类型和流程
- about写律所规模、成功案例数量、执业许可证
- team写每位律师的执业证号和擅长领域
- products写服务套餐：咨询→代理→诉讼
- testimonials写客户体验而非案件结果
- FAQ要有"咨询收费吗""我这情况有胜算吗""多久能出结果"
"""
    elif any(k in _industry for k in ('金融', '理财', '保险', '贷款', '投资', '基金', '银行')):
        _industry_guide = """
### 行业创作指引：金融 / 保险
- hero区写服务类型和合规资质
- services写具体产品线和目标人群
- about写持牌信息和风控体系
- team写持证理财师/精算师背景
- products写费率和风险等级，标注"过往业绩不代表未来"
- testimonials侧重服务体验而非投资收益
- FAQ要有"手续费多少""提前赎回有损失吗""收益保底吗"
"""
    elif any(k in _industry for k in ('宠物', '猫', '狗', '兽医', '宠物医院', '宠物店')):
        _industry_guide = """
### 行业创作指引：宠物
- hero区写服务范围和价格透明度
- services写具体项目：体检/疫苗/绝育/寄养/洗护
- about写兽医资质和设备
- team写兽医持证情况
- products写粮食/用品/套餐，含规格和适用阶段
- testimonials写铲屎官口吻
- FAQ要有"驱虫多久一次""寄养能看监控吗""处方粮和普通粮区别"
"""
    else:
        _industry_guide = """
### 行业创作指引：通用
- 找到该行业最核心的1-2个决策因素，文案围绕它展开
- 用行业内的具体术语和数字建立专业感
"""

    prompt = f"""[mode: site] 你是一个10年独立站转化率优化顾问，帮200+品牌从0做到月入10万+。你为这家企业写的内容，要让目标客户看完想下单，而不是让老板看了觉得"面子上有光"。

## 商家信息
- 名称: {info.get('name', '未知商家')}
- 行业: {info.get('industry', '通用')}
- 描述: {info.get('description', '专业服务')}
- 关键词: {info.get('keywords', '')}
- 电话: {info.get('phone', '')}
- 邮箱: {info.get('email', '')}
- 地址: {info.get('address', '')}
- 网址: {info.get('website', '')}

{_industry_guide}

## 🚫 绝对禁止
1. **禁止词表**：引领、卓越、领先、一站式、全方位、专业、优质、高端、极致、赋能、致力于、旨在
2. **禁止占位符**：电话/邮箱/地址中不许出现"xxx""XX""某某"等占位符，商家没提供就留空字符串""
3. **禁止AI编造联系信息**：email/phone/address商家没提供就必须留空字符串""，不许自己编一个
3. **禁止评价模板**："★★★★★" + 缩写名 + "非常满意"
3. **禁止全好评**：testimonials中至少1条是3-4星，写出具体不满
4. **禁止假数字**：不用"大幅提升""显著增加"，用"从X到Y"的具体数字
5. **禁止空洞团队介绍**：team里每个人的bio必须含从业年限或具体成就
6. **禁止假统计**：不许输出"4.8/5评分""2360+评价""98%推荐率"等编造统计，只放真实评价文字

## ✅ 必须做到
- testimonials至少1条含负面/中性细节："整体不错，就是首响有点慢"
- about_summary含具体数据：成立时间、团队规模、服务客户数
- story_content讲真实的创业动机，不写"为了让世界更美好"
- products描述含具体参数或功能边界
- FAQ问真实纠结的问题，不写自夸式问题

## 任务
生成一个完整5页网站的全部内容，每个页面的文案必须具体、真实、可直接上线。

## 输出格式（严格JSON）
{{
  "meta_title": "全局SEO标题，含品牌名+行业关键词",
  "meta_description": "全局SEO描述120-160字",
  "hero_headline": "8-15字首页大标题，格式'品牌名+核心价值'或'品类+痛点解决方案'，禁止只写纯卖点片段",
  "hero_subheadline": "20-40字补充核心价值或数据",
  "hero_cta": "4-8字行动按钮，说清下一步",
  "services_title": "服务板块标题",
  "services": [{{"title": "6-10字服务名称", "description": "30-50字服务说明，含具体成果或案例"}}, ...共4个],
  "about_title": "关于标题",
  "about_summary": "80-120字品牌概述，含创立时间/规模/成果数据",
  "story_title": "品牌故事标题",
  "story_content": "两段<p>，第一段讲为什么做(50-80字，真实动机)，第二段讲做到了什么(50-80字，具体成果)",
  "team_title": "团队标题",
  "team": [{{"name": "姓名", "title": "职位", "bio": "30-50字简介，含从业年限/具体成就，不用'资深''经验丰富'"}}, ...共3人],
  "values_title": "价值观标题",
  "values": [{{"title": "4-6字", "description": "20-30字具体诠释，不用'诚信''专业'这种空词"}}, ...共3个],
  "products_title": "产品标题",
  "products_subtitle": "副标题",
  "products": [{{"name": "产品名", "badge": "标签如热销/新品", "desc": "30-50字描述含核心卖点或具体参数", "price": "价格", "features": ["3-5个功能点，具体不笼统"]}}, ...共3个],
  "testimonials_title": "客户评价标题",
  "stats": [{{"value": "具体数字", "label": "6字以内"}}, ...共3条真实数据],
  "partner_brands": [],
  "partner_heading": "合作伙伴",
  "testimonials": [{{"name": "真实姓名(禁用张三李四王五，用刘建国/陈婉清/赵明辉)", "role": "公司+职位", "rating": "3-5，至少1条≤4", "text": "40-70字具体评价，至少1条含负面/中性细节"}}, ...共3条],
  "cta_headline": "CTA标题",
  "cta_subheadline": "副标题含优惠/保障",
  "cta_button": "按钮文字",
  "blog_title": "博客标题",
  "blog_subtitle": "副标题",
  "articles": [{{"title": "文章标题(含关键词，像真人写的)", "date": "日期", "tag": "分类标签", "excerpt": "40-60字摘要，有观点有数据"}}, ...共3篇],
  "contact_headline": "联系标题",
  "contact_subtitle": "副标题",
  "footer_text": "版权文字"
}}

## 文案要求
1. 用事实替代形容词
2. 评价像真人写的，至少1条非5星
3. SEO自然融入关键词
4. 每个页面内容要完整，不是占位符
5. 中文撰写，面向国内用户
6. 严格遵循行业创作指引

只返回JSON。"""
    return prompt


def _shop_prompt(info: dict[str, str]) -> str:
    """生成电商网站的 AI 提示"""
    _industry = info.get('industry', '通用').lower()

    _industry_guide = ""
    if any(k in _industry for k in ('tech', 'saas', '软件', '科技', 'it', '云')):
        _industry_guide = """
### 行业创作指引：Tech / SaaS 电商
- 信任背书用数据："日均处理12万笔订单""系统可用率99.97%"
- hero区强调平台能力而非情感："一键开店，API对接主流ERP"
- advantages写技术优势："秒级结算""自动库存同步""多仓库路由"
- banner写功能上线活动，不打价格战
"""
    elif any(k in _industry for k in ('ecommerce', '零售', '电商', '购物', '商城', '贸易', '消费')):
        _industry_guide = """
### 行业创作指引：电商 / 零售
- hero区直接亮价格或折扣："春季上新，全场2件8折"
- trust_stats用销量/复购率："累计售出50万件""复购率38%"
- advantages写具体售后："7天无理由""运费险""上门取件""30天保价"
- banner写限时活动含截止日期："3.8节特惠，3月8日23:59截止"
- brand_story写产品产地/材质故事，不写"让世界更美好"
"""
    elif any(k in _industry for k in ('教育', '培训', '课程', '学', '考')):
        _industry_guide = """
### 行业创作指引：教育电商
- hero区用课程成果："87%学员3个月内通过考试"
- trust_stats用通过率/学员数："已服务3万+学员""平均提分27分"
- advantages写教学优势："1对1批改""答疑2小时内响应""学不完可延期"
- banner写招生优惠含截止日期："早鸟价截至3月31日"
"""
    elif any(k in _industry for k in ('外贸', 'b2b', '出口', '进出口', '跨境', 'wholesale')):
        _industry_guide = """
### 行业创作指引：外贸 / B2B 电商
- hero区写MOQ和交期："起订量500件，15天交货"
- trust_stats用认证和出口量："CE/FDA认证，年出口200万件"
- advantages写B2B优势："OEM/ODM""免费打样""第三方验货支持""FOB/CIF灵活报价"
- banner写展会/新品发布，不写C端促销
"""
    else:
        _industry_guide = """
### 行业创作指引：通用电商
- 信任背书用可验证的具体数据
- advantages写消费者真正关心的：售后、物流、价格
- banner写真实促销活动
"""

    prompt = f"""你是一个操盘过200+电商店铺的转化率优化顾问，最擅长把"只逛不买"变成"加购物车"。你写的每个字都要让消费者觉得"买了不亏"，而不是"这又是AI编的"。

## 商家信息
- 名称: {info.get('name', '未知商家')}
- 行业: {info.get('industry', '通用')}
- 描述: {info.get('description', '专业电商')}
- 关键词: {info.get('keywords', '')}
- 电话: {info.get('phone', '')}
- 邮箱: {info.get('email', '')}
- 地址: {info.get('address', '')}

{_industry_guide}

## 🚫 绝对禁止
1. **禁止词表**：引领、卓越、领先、一站式、全方位、专业、优质、高端、极致、赋能、致力于、旨在
2. **禁止占位符**：电话/邮箱/地址中不许出现"xxx""XX""某某"等占位符，商家没提供就留空字符串""
3. **禁止AI编造联系信息**：email/phone/address商家没提供就必须留空字符串""，不许自己编一个
3. **禁止假数据**：trust_stats里不能有"千万级""亿万级"这种吹牛数字，用"已服务12,348位客户"这种精确数字
3. **禁止空洞banner**：每个banner必须有具体活动内容、折扣力度、截止时间，不写"精彩活动等你来"
4. **禁止自我吹嘘**：advantages不能写"品质保证""客户至上"这种废话，写"3道质检，退货率0.3%""下单后24小时内发货"
5. **禁止假统计**：不许输出"4.8/5评分""2360+评价""98%推荐率"等编造统计，只放真实评价文字

## ✅ 必须做到
- trust_stats必须有可验证感：用精确数字而非整数（"12,348"比"10,000+"更可信）
- brand_story_content讲真实的品牌起源：为什么做这个产品，不是"追求卓越"
- advantages每个都含具体数据或场景：不说"物流快"而说"全国87%地区次日达"
- banner要有真实感的促销：含折扣力度、截止时间、适用范围

## 任务
生成完整电商网站内容，所有文案必须具体、可信任、可直接上线。

## 输出格式（严格JSON）
{{
  "meta_title": "50-60字含品牌名+品类关键词",
  "meta_description": "120-160字含行动号召",
  "hero_headline": "8-15字首页大标题，突出品类优势，格式'品牌名+核心价值'或'品类+痛点解决方案'",
  "hero_subheadline": "20-40字补充核心卖点或数据",
  "trust_stats": ["3-5条信任背书，用精确数字，如'已服务12,348位客户''复购率38%''退货率0.3%'"],
  "brand_story_title": "品牌故事标题",
  "brand_story_content": "两段<p>，第一段品牌真实由来(50-80字，讲为什么做)，第二段品质承诺含具体数据(50-80字)",
  "advantages": [{{"title": "6-10字优势名称", "desc": "20-40字具体说明含数据，不用'品质保证''客户至上'"}}, ...共4个],
  "banner_slides": [{{"title": "8-15字活动标题含折扣力度", "subtitle": "15-25字活动说明含截止时间", "cta": "4-6字按钮"}}, ...共3个],
  "footer_about": "50字品牌简介，含具体数据",
  "footer_links": {{"帮助中心": ["订单查询", "退换货政策", "配送说明", "支付方式"], "关于我们": ["品牌故事", "联系我们", "加入我们", "隐私政策"]}}
}}

## 文案要求
1. 信任感：用精确数字、认证、真实案例建立信任，不用"10万+"用"12,348"
2. 具体不空洞：不用"品质卓越"改用"3道质检，0.1%退货率"
3. 购物导向：banner要有真实感的促销活动，含截止时间
4. 中文撰写，面向国内消费者
5. 严格遵循行业创作指引

只返回JSON。"""
    return prompt


def _pricing_prompt(info: dict[str, str]) -> str:
    """生成定价页的 AI 提示"""
    _industry = info.get('industry', '通用').lower()

    _industry_guide = ""
    if any(k in _industry for k in ('tech', 'saas', '软件', '科技', 'it', '云')):
        _industry_guide = """
### 行业创作指引：Tech / SaaS 定价
- 功能点写具体上限和边界："最多5个项目"vs"无限项目"，"API 1000次/天"vs"API无限次"
- 基础版限制要明确：用户数、存储量、API调用次数
- 专业版写出解锁的关键能力："Webhook""自定义集成""优先技术支持"
- 企业版写SLA保障："99.99%可用率""专属客户经理""7×24响应"
- FAQ要有"能按年付费吗""数据能导出吗""中途升级怎么算"
"""
    elif any(k in _industry for k in ('教育', '培训', '课程', '学', '考')):
        _industry_guide = """
### 行业创作指引：教育 / 培训 定价
- 功能点写课时/内容量："8节课"vs"24节课+1对1答疑"vs"无限课时+督学"
- 基础版写清不含什么："不含模拟考""不含1对1批改"
- 专业版突出增值："模拟考3次""作文精批""专属班主任"
- 企业版写团报优惠和定制服务
- FAQ要有"学不完能延期吗""可以退费吗""
"""
    elif any(k in _industry for k in ('外贸', 'b2b', '出口', '进出口', '跨境', 'wholesale')):
        _industry_guide = """
### 行业创作指引：外贸 / B2B 定价
- 功能点写订单量/SKU数："最多50个SKU"vs"500个SKU"
- 基础版写清限制："不支持多币种""无ERP对接"
- 专业版写增值能力："多币种报价""ERP自动同步""多语言店铺"
- FAQ要有"可以按年付费吗""有实施费吗""
"""
    else:
        _industry_guide = """
### 行业创作指引：通用定价
- 功能点写具体数值和边界，不用"高级功能"
- 每档之间要有清晰的"值不值"对比感
- FAQ回答真实纠结的问题
"""

    prompt = f"""[mode: pricing] 你是一个帮300+SaaS公司设计定价页的转化率顾问，最懂怎么让用户心甘情愿选中间档。你设计的定价方案要让人觉得"基础版够用但有点亏，专业版明显更值，企业版给有钱人准备的"。

## 商家信息
- 名称: {info.get('name', '未知商家')}
- 描述: {info.get('description', '专业服务')}
- 行业: {info.get('industry', '通用')}

{_industry_guide}

## 🚫 绝对禁止
1. **禁止词表**：引领、卓越、领先、一站式、全方位、专业、优质、高端、极致、赋能、致力于、旨在
2. **禁止占位符**：电话/邮箱/地址中不许出现"xxx""XX""某某"等占位符，商家没提供就留空字符串""
3. **禁止AI编造联系信息**：email/phone/address商家没提供就必须留空字符串""，不许自己编一个
4. **禁止笼统功能点**：不说"高级功能""更多权益"，必须写具体："无限项目+优先客服+API接入"
3. **禁止虚假保障**：不说"不满意全额退款"除非真有这政策，改说"14天内可无理由取消"
4. **禁止FAQ自夸**：FAQ不能问"你们有什么优势"这种给你唱赞歌的问题
5. **禁止假统计**：不许输出"4.8/5评分""2360+评价""98%推荐率"等编造统计，只放真实评价文字

## ✅ 必须做到
- 基础版功能点要写出"够用但有限制"的感觉："最多5个项目""API 1000次/天"
- 专业版功能点要让人觉得"多花这点钱太值了"：解锁关键能力+消除基础版限制
- 企业版功能点要展示天花板：SLA、专属服务、定制能力
- FAQ必须问真实纠结的问题："免费版有什么限制？""中途升级怎么算？""能按年付吗？""和XX比有什么区别？"
- 每档features的数量和层次要有对比感，不是简单的5-5-5

## 任务
设计3档定价方案，让用户自然选择中间档。每档功能点要具体、可理解、有对比感。

## 输出格式（严格JSON）
{{
  "meta_title": "含'价格/定价/方案'+品牌名的SEO标题",
  "meta_description": "100-150字含CTA",
  "hero_title": "8-15字定价页标题",
  "hero_subtitle": "20-30字副标题",
  "pricing_note": "补充说明如'所有方案含14天免费试用'",
  "plans": [
    {{
      "name": "基础版",
      "price": "¥99",
      "period": "/月",
      "badge": "",
      "features": ["5个5-10字功能点，写具体上限和边界，如'最多5个项目''API 1000次/天'"],
      "popular": false
    }},
    {{
      "name": "专业版",
      "price": "¥299",
      "period": "/月",
      "badge": "最受欢迎",
      "features": ["5个功能点，含基础版全部+解锁关键能力，如'无限项目''API无限制''优先客服'"],
      "popular": true
    }},
    {{
      "name": "企业版",
      "price": "¥999",
      "period": "/月",
      "badge": "",
      "features": ["5个功能点，含专属服务，如'99.99%SLA''专属客户经理''定制部署'"],
      "popular": false
    }}
  ],
  "cta_title": "行动号召标题",
  "cta_subtitle": "补充保障说明，含具体政策",
  "cta_button": "4-8字按钮",
  "footer_text": "版权",
  "faq": [{{"q": "购买决策中真实纠结的问题，如'免费版有什么限制''中途升级怎么算'", "a": "30-50字清晰回答，含具体政策"}}, ...共5个]
}}

## 文案要求
1. 功能点具体：不说"高级功能"改说"无限项目+优先客服+API接入"
2. 价格心理学：基础版够用但有限制，专业版明显更值，企业版展示天花板
3. FAQ要真实：回答用户真的会纠结的问题，不写自夸式问题
4. 中文撰写
5. 严格遵循行业创作指引

只返回JSON。"""
    return prompt


# ═══════════════════════════════════════════════════════════
#  Engine
# ═══════════════════════════════════════════════════════════

class SiteBuilderEngine:
    """
    站点构建引擎。

    这是项目的"老板"，协调 AI 和 Template 两个子系统。

    用法:
        engine = SiteBuilderEngine()
        await engine.init()  # 自动加载最优后端

        result = await engine.build_landing({"name": "星辰跨境", "industry": "跨境电商", "description": "独立站建站"})
        html = result["html"]

    """

    def __init__(self, output_dir: str | Path = "./outputs"):
        self._ai = AIBackendLoader()
        self._template = TemplateBackendLoader()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = False

    @property
    def ai_backend(self) -> AIBackend | None:
        return self._ai.get_backend_instance()

    @property
    def template_backend(self) -> TemplateBackend | None:
        return self._template.get_backend_instance()

    @property
    def active_ai(self) -> str:
        return self._ai.get_backend() or "none"

    @property
    def active_template(self) -> str:
        return self._template.get_backend() or "none"

    async def init(self, ai_config: dict | None = None) -> dict[str, str]:
        """
        初始化引擎（加载默认后端）。

        相当于启动 asyncio event loop 时选择 Selector / Proactor：
        系统自动检测可用实现并选择最优。
        """
        ai = self._ai.load_default(ai_config)
        tpl = self._template.load_default()
        
        # 健康检查：如果active后端不可用，切换到下一个
        ai_backend = self.ai_backend
        if ai_backend and hasattr(ai_backend, 'health_check'):
            healthy = await ai_backend.health_check()
            if not healthy:
                logger.warning(f"AI后端 {ai} 健康检查失败，尝试切换")
                # 尝试切换到其他可用后端
                for name in ["glm", "deepseek", "mock"]:
                    if name != ai:
                        try:
                            self._ai.set_backend(name, **(ai_config or {}))
                            new_backend = self.ai_backend
                            if new_backend and hasattr(new_backend, 'health_check'):
                                if await new_backend.health_check():
                                    ai = name
                                    logger.info(f"切换AI后端到 {name}")
                                    break
                        except Exception:
                            continue
                else:
                    # 所有AI后端不可用，使用mock
                    logger.warning("所有AI后端不可用，使用Mock模板")
                    self._ai.set_backend("mock")
                    ai = "mock"
        
        self._initialized = True
        logger.info(f"引擎就绪 — AI: {ai} | Template: {tpl}")
        return {"ai": ai, "template": tpl}

    def _ensure_init(self):
        if not self._initialized:
            raise RuntimeError("引擎尚未初始化，请先调用 await engine.init()")

    # ── 3种核心构建能力 ──

    async def build_landing(self, info: dict[str, str], is_pro: bool = False, **ai_kwargs) -> dict[str, Any]:
        """
        生成单页 SEO 着陆页。

        Args:
            info: {name, industry, description, keywords, audience, ...}
        Returns:
            {mode:"landing", html:"...", content:{...}, file_path:"..."}
        """
        self._ensure_init()
        ai = self.ai_backend
        tpl = self.template_backend

        prompt = _landing_prompt(info)

        ai_error = None
        try:
            content = await ai.generate(prompt, **ai_kwargs)
            ai_used = True
        except Exception as e:
            logger.warning(f"AI 生成失败: {e}，使用内置模板")
            ai_error = repr(e)
            # 尝试获取更详细的API错误
            if hasattr(ai, '_last_api_error') and ai._last_api_error:
                ai_error = ai._last_api_error
            content = await self._mock_landing(info)
            ai_used = False

        # 注入主题变量 + 用户等级
        self._inject_theme(info, content)
        content["is_pro"] = is_pro

        # 渲染
        try:
            html = tpl.render("landing", content)
        except Exception as e:
            raise TemplateRenderError(tpl.name, str(e))

        # 保存到文件
        page_id = uuid.uuid4().hex[:12]
        file_path = self.output_dir / f"{page_id}.html"
        # 免费版水印通过HTML注释标记来源
        file_path.write_text(html, encoding="utf-8")
        # 记录元数据用于过期清理
        self._save_meta(page_id, is_pro=is_pro)

        return {
            "mode": "landing",
            "html": html,
            "content": content,
            "page_id": page_id,
            "file_path": str(file_path),
            "file_size": len(html),
            "ai_used": ai_used,
            "ai_backend": self.active_ai,
            "ai_error": ai_error,
            "is_pro": is_pro,
        }

    async def build_site(self, info: dict[str, str], is_pro: bool = False, **ai_kwargs) -> dict[str, Any]:
        """
        生成完整多页网站（首页 + 关于 + 产品 + 博客 + 联系）。

        Returns:
            {mode:"site", pages:{...}, html:"首页", content:{...}, zip_path:"..."}
        """
        self._ensure_init()
        ai = self.ai_backend
        tpl = self.template_backend

        prompt = _site_prompt(info)

        try:
            content = await ai.generate(prompt, **ai_kwargs)
            ai_used = True
        except Exception as e:
            logger.warning(f"AI 生成网站失败: {e}")
            content = await self._mock_site(info)
            ai_used = False

        self._inject_theme(info, content)
        content["is_pro"] = is_pro

        # 渲染多页（并发）
        pages = await self._render_multi_page(content, info)

        # 打包 ZIP
        import zipfile as _zf
        import io as _io

        buf = _io.BytesIO()
        with _zf.ZipFile(buf, "w", _zf.ZIP_DEFLATED) as zf:
            for name, html_str in pages.items():
                zf.writestr(f"{name}.html", html_str)
        zip_data = buf.getvalue()

        site_id = uuid.uuid4().hex[:12]
        zip_path = self.output_dir / f"{site_id}.zip"
        zip_path.write_bytes(zip_data)

        # 也存一份首页
        index_html = pages.get("index", "")
        html_path = self.output_dir / f"{site_id}.html"
        html_path.write_text(index_html, encoding="utf-8")

        return {
            "mode": "site",
            "pages": list(pages.keys()),
            "html": index_html,
            "content": content,
            "site_id": site_id,
            "file_path": str(html_path),
            "zip_path": str(zip_path),
            "file_size": len(index_html),
            "zip_size": len(zip_data),
            "ai_used": ai_used,
            "ai_backend": self.active_ai,
        }

    async def build_shop(self, info: dict[str, str], is_pro: bool = False, **ai_kwargs) -> dict[str, Any]:
        """
        生成电商网站（含购物车/支付/商品管理）。

        Returns:
            {mode:"shop", site_id:"...", html:"...", ...}
        """
        self._ensure_init()
        ai = self.ai_backend
        tpl = self.template_backend

        prompt = _shop_prompt(info)

        try:
            content = await ai.generate(prompt, **ai_kwargs)
            ai_used = True
        except Exception as e:
            logger.warning(f"AI 生成电商网站失败: {e}")
            content = await self._mock_shop(info)
            ai_used = False

        # 注入电商专用变量
        site_id = uuid.uuid4().hex[:12]
        content.setdefault("site_id", site_id)
        content.setdefault("api_base_url", info.get("api_base_url", ""))
        content.setdefault("theme", info.get("theme", "tech_blue"))
        content.setdefault("currency", info.get("currency", "CNY"))
        content.setdefault("currency_symbol", "¥" if content["currency"] == "CNY" else "$")
        content.setdefault("customer_service_url", info.get("customer_service_url", ""))
        content.setdefault("ga_id", info.get("ga_id", ""))
        content.setdefault("baidu_tongji_id", info.get("baidu_tongji_id", ""))
        self._inject_theme(info, content)
        content["is_pro"] = is_pro

        try:
            html = tpl.render("shop", content)
        except Exception as e:
            raise TemplateRenderError(tpl.name, str(e))

        # 保存到文件
        file_path = self.output_dir / f"{site_id}.html"
        file_path.write_text(html, encoding="utf-8")

        # 初始化电商数据
        try:
            from core.ecommerce.store import SiteConfigStore, PaymentConfigStore, ShippingStore, ProductStore
            SiteConfigStore(site_id).update_config({
                "theme": content["theme"],
                "currency": content["currency"],
                "shop_name": info.get("name", ""),
                "shop_slogan": content.get("hero_subheadline", ""),
                "language": "zh",
                "logo": "",
                "favicon": "",
                "phone": info.get("phone", ""),
                "email": info.get("email", ""),
                "address": info.get("address", ""),
                "customer_service_url": "",
                "ga_id": "",
                "baidu_tongji_id": "",
                "modules": {
                    "banner": True, "featured": True, "coupon_banner": True,
                    "buyer_show": True, "brand_story": True,
                },
                "module_order": ["banner", "featured", "coupon_banner", "buyer_show", "brand_story"],
                "custom_pages": {},
            })
            # 初始化空数据文件
            ProductStore(site_id)
            PaymentConfigStore(site_id).update_config("wechat", {"enabled": False, "sandbox": True})
            PaymentConfigStore(site_id).update_config("alipay", {"enabled": False, "sandbox": True})
            PaymentConfigStore(site_id).update_config("paypal", {"enabled": False, "sandbox": True})
            ShippingStore(site_id).update_config({"methods": [], "free_shipping_min": 0})
        except Exception as e:
            logger.warning(f"电商数据初始化失败(非致命): {e}")

        return {
            "mode": "shop",
            "site_id": site_id,
            "html": html,
            "content": content,
            "file_path": str(file_path),
            "file_size": len(html),
            "ai_used": ai_used,
            "ai_backend": self.active_ai,
        }

    async def build_pricing(self, info: dict[str, str], is_pro: bool = False, **ai_kwargs) -> dict[str, Any]:
        """
        生成付费定价页面。

        Returns:
            {mode:"pricing", html:"...", content:{...}, page_id:"...", file_path:"..."}
        """
        self._ensure_init()
        ai = self.ai_backend
        tpl = self.template_backend

        prompt = _pricing_prompt(info)

        try:
            content = await ai.generate(prompt, **ai_kwargs)
            ai_used = True
        except Exception as e:
            logger.warning(f"AI 生成定价失败: {e}")
            content = await self._mock_pricing(info)
            ai_used = False

        self._inject_theme(info, content)
        content["is_pro"] = is_pro

        html = tpl.render("pricing", content)  # 定价专用模板
        page_id = uuid.uuid4().hex[:12]
        file_path = self.output_dir / f"{page_id}.html"
        file_path.write_text(html, encoding="utf-8")

        return {
            "mode": "pricing",
            "html": html,
            "content": content,
            "page_id": page_id,
            "file_path": str(file_path),
            "file_size": len(html),
            "ai_used": ai_used,
            "ai_backend": self.active_ai,
        }

    # ── 文件元数据与过期清理 ──

    def _save_meta(self, page_id: str, is_pro: bool = False):
        """保存生成文件的元数据（用于过期清理和权限校验）"""
        import json as _json
        meta_path = self.output_dir / f"{page_id}.meta.json"
        meta = {
            "id": page_id,
            "is_pro": is_pro,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }
        meta_path.write_text(_json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    def cleanup_expired(self, max_age_hours: int = 24):
        """清理过期的输出文件（免费版24h, 专业版72h）"""
        import json as _json
        now = __import__("datetime").datetime.now().timestamp()
        for f in list(self.output_dir.glob("*.meta.json")):
            try:
                meta = _json.loads(f.read_text(encoding="utf-8"))
                age_hours = (now - __import__("datetime").datetime.fromisoformat(meta["created_at"]).timestamp()) / 3600
                max_h = 72 if meta.get("is_pro") else max_age_hours
                if age_hours > max_h:
                    fid = meta["id"]
                    (self.output_dir / f"{fid}.html").unlink(missing_ok=True)
                    (self.output_dir / f"{fid}.zip").unlink(missing_ok=True)
                    f.unlink()
                    logger.info(f"清理过期文件: {fid} ({age_hours:.0f}h)")
            except Exception as e:
                logger.warning(f"清理元数据失败 {f}: {e}")

    # ── 主题注入 ──

    def _inject_theme(self, info: dict, content: dict):
        """注入主题变量和商家基础信息"""
        # 商家基础信息 — 用户输入优先于AI推断
        if info.get("name"):
            content.setdefault("name", info["name"])
        # 行业：用户指定时用用户值（确保颜色映射正确），AI返回时保留
        if info.get("industry"):
            content["industry"] = info["industry"]  # 用户指定的行业优先，覆盖AI推断
        else:
            content.setdefault("industry", "")
        if info.get("website"):
            content.setdefault("website", info["website"])
        # 主题色 — primary_dark/light 由模板 _prepare_context 根据主色自动计算
        content.setdefault("primary_color", "#1a73e8")
        # 不再在此注入 primary_dark / primary_light，避免覆盖 _prepare_context 的 colorsys 计算
        content.setdefault("footer_bg", "#1a1a2e")
        content.setdefault("footer_text", "#aaa")
        content.setdefault("canonical_url", info.get("website", ""))

    # ── 多页并发渲染 ──

    async def _render_multi_page(self, content: dict, info: dict) -> dict[str, str]:
        """渲染Site模式的多页面（index + about + services + contact）"""
        pages = {
            "index": self.template_backend.render("site", content),
        }
        # 从content中提取多页数据
        sections = content.get("sections", {})
        nav_links = content.get("nav_links", [])
        
        # 为子页面渲染——复用site模板但注入子页面内容
        for page_key, page_title in [("about", "关于我们"), ("services", "服务项目"), ("contact", "联系我们")]:
            # 检查AI是否返回了子页面内容
            page_content = sections.get(page_key) or content.get(page_key)
            if not page_content:
                continue
            # 构建子页面content（继承主站信息）
            sub_content = dict(content)
            sub_content["_sub_page"] = page_key
            sub_content["_sub_title"] = page_title
            sub_content["hero_headline"] = page_content.get("headline", page_title) if isinstance(page_content, dict) else page_title
            sub_content["hero_subtitle"] = page_content.get("subtitle", "") if isinstance(page_content, dict) else ""
            sub_content["_page_sections"] = page_content
            try:
                pages[page_key] = self.template_backend.render("site", sub_content)
            except Exception as e:
                logger.warning(f"渲染子页面 {page_key} 失败: {e}")
        
        return pages

    # ── Mock fallbacks ──

    async def _mock_landing(self, info: dict) -> dict:
        from core.backends.ai.mock import MockAIBackend
        mock = MockAIBackend()
        prompt = _landing_prompt(info)
        return await mock.generate(prompt)

    async def _mock_site(self, info: dict) -> dict:
        from core.backends.ai.mock import MockAIBackend
        mock = MockAIBackend()
        # Mock can handle site mode
        prompt = f"mode=site|名称:{info.get('name','')}|行业:{info.get('industry','')}|描述:{info.get('description','')}|关键词:{info.get('keywords','')}|电话:{info.get('phone','')}|邮箱:{info.get('email','')}|地址:{info.get('address','')}|网址:{info.get('website','')}"
        return await mock.generate(prompt)

    async def _mock_pricing(self, info: dict) -> dict:
        from core.backends.ai.mock import MockAIBackend
        mock = MockAIBackend()
        prompt = f"mode=pricing|名称:{info.get('name','')}|行业:{info.get('industry','')}|描述:{info.get('description','')}"
        return await mock.generate(prompt)

    async def _mock_shop(self, info: dict) -> dict:
        from core.backends.ai.mock import MockAIBackend
        mock = MockAIBackend()
        prompt = f"mode=shop|名称:{info.get('name','')}|行业:{info.get('industry','')}|描述:{info.get('description','')}|关键词:{info.get('keywords','')}|电话:{info.get('phone','')}|邮箱:{info.get('email','')}|地址:{info.get('address','')}"
        return await mock.generate(prompt)


# ═══════════════════════════════════════════════════════════
#  全局单例（仿 asyncio 的 get_event_loop）
# ═══════════════════════════════════════════════════════════

_engine: SiteBuilderEngine | None = None


async def get_engine(ai_config: dict | None = None) -> SiteBuilderEngine:
    """获取全局引擎单例（懒加载）"""
    global _engine
    if _engine is None:
        _engine = SiteBuilderEngine()
        await _engine.init(ai_config)
    return _engine