"""
core.backends.ai.mock — Mock AI 后端

纯 Python 内置实现，零外部依赖，始终可用。
作为兜底后端，优先级最低（类似 bcrypt 的纯 Python 实现）。

生成基于预设模板的结构化内容，确保系统在没有 API Key 时也能正常运行。
"""

from __future__ import annotations

import json as _json
import logging
import random as _random
import re
import uuid as _uuid
from typing import Any

from core.backends.base import AIBackend

logger = logging.getLogger("site-builder.ai.mock")

# ═══════════════════════════════════════════════════════════
#  预设的企业资料库（用于提词注入）
# ═══════════════════════════════════════════════════════════

_SLOGANS = {
    "default": ["从0到1，每一步都有数据支撑", "不画饼，只交付可量化的结果", "用方法论替代拍脑袋"],
    "tech": ["别让系统故障晚发现15分钟", "API响应<200ms，可用率99.97%", "代码能解决的，别靠人"],
    "shop": ["退货率从25%降到8%", "复购率翻3倍的秘密", "上新3天GMV破百万的打法"],
    "biz": ["方案落地才叫方案", "帮37家企业把PPT变成了数据", "你的痛点，我们踩过坑"],
    "edu": ["完课率30%→78%是怎么做到的", "学不会？那是课的问题不是你的", "3个月从0到拿offer"],
    "health": ["等2小时看5分钟？试试30秒响应", "检查报告大白话解读", "线上问诊≠假医生"],
}

_FEATURE_POOLS = [
    [("3道质检关卡", "原材料入厂→半成品→成品全检，退货率0.3%，同行平均2.1%"), ("7×24秒级响应", "工单平均响应47秒，1小时内给出方案，不是让你排队等"), ("行业老兵坐镇", "8年+资深顾问1对1，不是刚毕业的客服照本宣科")],
    [("多源数据实时接入", "支持50+数据源，3分钟完成清洗，识别准确率99.2%"), ("RBAC权限隔离", "6级角色权限，操作日志留存180天，等保三级通过"), ("全球化部署", "3地域节点自动就近接入，海外访问延迟<120ms")],
    [("按场景灵活配置", "不是千篇一律的模板，而是根据你的业务流程定制工作流"), ("成本透明可控", "用多少付多少，月度账单明细到每一笔调用，没有隐藏费用"), ("双周迭代更新", "产品每14天迭代一次，你的需求48小时内进入排期评估")],
]


class MockAIBackend(AIBackend):
    """
    内置 Mock AI 后端。

    优先级 999（始终最后），零依赖，100% 可用。
    生成基于模板的结构化内容，格式与真实 AI 返回一致。

    类似：
    - json 模块中 py_scanstring 作为 C 版不可用时的回退
    - bcrypt 中纯 Python 实现作为 C 扩展不可用时的回退
    """

    name = "mock"
    priority = 999
    display_name = "Mock (内置模板)"

    def __init__(self):
        pass

    @classmethod
    def _check_dependencies(cls) -> None:
        """Mock 后端始终可用"""
        pass

    async def health_check(self) -> bool:
        return True

    async def generate(self, prompt: str, **kwargs) -> dict[str, Any]:
        """
        从提示中提取关键信息，生成模板化的结构化内容。

        虽然不如 AI 生成灵活，但保证系统始终可运行。
        """
        # 从 prompt 中提取商家信息
        info = self._extract_info(prompt)
        mode = info.get("mode", "landing")

        if mode == "site":
            return self._gen_site(info)
        elif mode == "pricing":
            return self._gen_pricing(info)
        else:
            return self._gen_landing(info)

    def _extract_info(self, prompt: str) -> dict:
        """从提示中提取关键信息"""
        info = {"name": "默认商家", "industry": "科技", "description": "一站式数字化解决方案", "keywords": "", "mode": "landing"}

        import re

        # 提取商家名称 (兼容新旧prompt格式)
        m = re.search(r"商家[:：]\s*(.+?)(?:\||$|\n)", prompt or "")
        if m:
            info["name"] = m.group(1).strip()
        else:
            m = re.search(r"名称[:：\-]\s*(.+?)(?:\||$|\n)", prompt or "")
            if m:
                info["name"] = m.group(1).strip()

        # 提取行业
        m = re.search(r"行业[:：\-]\s*(.+?)(?:\||$|\n)", prompt or "")
        if m:
            info["industry"] = m.group(1).strip()

        # 提取描述
        m = re.search(r"描述[:：\-]\s*(.+?)(?:\||$|\n)", prompt or "")
        if m:
            info["description"] = m.group(1).strip()

        # 提取关键词
        m = re.search(r"关键词[:：\-]\s*(.+?)(?:\||$|\n)", prompt or "")
        if m:
            info["keywords"] = m.group(1).strip()

        # 提取电话
        m = re.search(r"电话[:：\-]\s*(.+?)(?:\||$|\n)", prompt or "")
        if m:
            info["phone"] = m.group(1).strip()

        # 提取邮箱
        m = re.search(r"邮箱[:：\-]\s*(.+?)(?:\||$|\n)", prompt or "")
        if m:
            info["email"] = m.group(1).strip()

        # 提取地址
        m = re.search(r"地址[:：\-]\s*(.+?)(?:\||$|\n)", prompt or "")
        if m:
            info["address"] = m.group(1).strip()

        # 检测模式（只匹配显式标记，不匹配内容词汇）
        p = prompt or ""
        # 优先匹配明确模式标记
        m_mode = re.search(r'(?:模式|mode)[:：\-=]\s*(landing|site|pricing|shop)', p, re.IGNORECASE)
        if m_mode:
            info["mode"] = m_mode.group(1).lower()
        elif re.search(r'定价页|pricing.?page|3档|plans|套餐', p, re.IGNORECASE):
            info["mode"] = "pricing"
        elif re.search(r'完整网站|多页网站|full.?site|品牌故事|关于我们|team|团队介绍', p, re.IGNORECASE):
            info["mode"] = "site"
        elif re.search(r'商城|shop|电商|商品|购物车|products', p, re.IGNORECASE):
            info["mode"] = "shop"

        return info

    def _gen_landing(self, info: dict) -> dict:
        """生成着陆页内容"""
        n = info["name"]
        ind = info["industry"]
        desc = info["description"]
        kw = info["keywords"]
        if not kw or kw.startswith('-') or kw.startswith(' '):
            # 自动生成合理关键词
            kw = f"{n},{ind},{desc[:20]}".replace(' ', ',')[:80]
        
        # 行业定制化内容
        _industry_content = {
            "物流运输": {
                "hero": f"{n} · 华北12年整车零担当日达",
                "sub": "日均发车87班次，覆盖晋冀蒙鲁4省68城，准时交付率98.6%",
                "cta": "30秒询价，当天出方案",
                "cta_headline": "今日询价，明天发车",
                "features": [
                    {"title": "整车零担双通道", "description": "4.2-17.5米全车型覆盖，3吨起零担拼车，吨位越大单价越低"},
                    {"title": "智能调度追踪", "description": "GPS+北斗双定位，每15分钟更新位置，APP实时查看在途状态"},
                    {"title": "仓储分拨一体", "description": "太原/石家庄2万㎡中心仓，B2C订单24小时出库，破损率0.12%"},
                    {"title": "保险赔付保障", "description": "货运险0.3‰费率，出险72小时定损，7工作日到账"},
                ],
                "about": f'<p>{n}成立于2012年，从3台4.2米货车起步，如今自有车辆126台、合作运力500+，年货运量突破42万吨。核心团队来自顺丰、德邦，把快递级时效管理引入零担物流。</p><p>2025年上线智能调度平台后，平均配载率从67%提升至89%，单车月均行驶里程增加2300公里，客户综合物流成本降低约15%。</p>',
                "testimonials": [
                    {"name": "赵明辉", "role": "恒泰建材 采购总监", "rating": 5, "text": "从太原到济南的零担，他们隔天上午就到，比之前合作的物流快了整整一天。价格还便宜8%。"},
                    {"name": "陈婉清", "role": "优选零食电商 运营负责人", "rating": 4, "text": "仓储发货速度确实快，就是旺季仓位有点紧需要提前3天预约，其他没毛病。"},
                    {"name": "刘建国", "role": "鑫源化工 厂长", "rating": 5, "text": "危化品运输资质齐全，司机持证上岗，比找散户踏实太多。合作两年零事故。"},
                ],
                "stats": [{"value": "98.6%", "label": "准时交付率"}, {"value": "126台", "label": "自有车辆"}, {"value": "42万吨", "label": "年货运量"}],
                "faq": [
                    {"q": "零担怎么收费？最低多少起？", "a": "按重量/体积取大计费，3吨起运。太原→石家庄约0.35元/公斤，具体看线路和货类。"},
                    {"q": "你们和安能、德邦比优势在哪？", "a": "我们深耕华北短途专线，同省次日达。大网是拼全国干线，我们做区域深度覆盖，配载率和时效更好。"},
                    {"q": "货损了怎么赔？", "a": "按声明价值赔付，0.3‰费率投保。出险后72小时定损，7个工作日打款。未投保按运费3倍赔。"},
                    {"q": "可以月结吗？对账流程是什么？", "a": "月发货量超20吨可申请月结（30天账期）。每月5号出对账单，支持系统导出明细和开票。"},
                    {"q": "危化品能运吗？需要什么资质？", "a": "可以。我们持有道路危险货物运输许可证，司机持危运从业资格证，车辆配备GPS和防泄漏装置。"},
                ],
                "process": [
                    {"title": "在线询价", "desc": "提交货类/重量/起止地，系统15分钟出报价"},
                    {"title": "上门提货", "desc": "市区2小时上门，县区4小时到达"},
                    {"title": "在途追踪", "desc": "GPS实时定位，到站自动通知收货人"},
                ],
                "guarantee": "货损72小时定损，7日赔付",
                "badges": ["货运险0.3‰", "危运资质齐全", "24h客服"],
                "color": "#0d7c3e",
                "address": "太原市小店区长风街168号",
                "email": "service@xinda-logistics.com",
                "phone": "0351-7658900",
            },
            "科技软件": {
                "hero": f"别再让系统故障晚发现15分钟",
                "sub": "API平均响应<200ms，故障发现从15分钟降到47秒，全年宕机<53分钟",
                "cta": "注册即开通，无需信用卡",
                "cta_headline": "14天免费，不满意随时退",
                "features": [
                    {"title": "秒级异常检测", "description": "全链路监控，故障发现从平均15分钟降到47秒，三通道告警（短信+企微+钉钉）"},
                    {"title": "多源数据实时接入", "description": "50+数据源3分钟接入，支持REST/SDK/Webhook，单次批量导出上限1万条"},
                    {"title": "RBAC权限隔离", "description": "6级角色权限，操作日志留存180天，审计追溯零死角"},
                    {"title": "灰度发布管控", "description": "按比例/白名单/地域灰度，回滚1秒完成，上线事故率降低92%"},
                ],
                "about": f"<p>{n}由前阿里P8架构师带队，6年监控领域实战经验。我们从0自研了分布式追踪引擎，处理过单日12亿条日志的峰值场景，比开源方案快3倍、省60%资源。</p><p>目前服务860家企业，覆盖电商、金融、教育等23个行业。客户平均故障恢复时间从4.2小时缩短到18分钟，全年SLA达成率99.97%。</p>",
                "testimonials": [
                    {"name": "张工", "role": "云途电商 技术总监", "rating": 5, "text": "双11那天QPS飙到平时的15倍，他们的监控系统扛住了，0误报。之前用开源方案双11必挂。"},
                    {"name": "小李", "role": "饭团科技 后端负责人", "rating": 4, "text": "接入很快，文档写得也清楚。就是自定义告警规则的语法学习曲线有点陡，花了两天才摸熟。"},
                    {"name": "老陈", "role": "金信期货 CTO", "rating": 5, "text": "金融场景对审计要求极高，他们的操作日志留存180天+不可篡改，合规检查一次过。"},
                ],
                "stats": [{"value": "从0到860家", "label": "服务企业"}, {"value": "全年宕机<53分钟", "label": "SLA 99.97%"}, {"value": "23个行业", "label": "覆盖领域"}],
                "faq": [
                    {"q": "我现在的Prometheus+Grafana好好的，为什么要换？", "a": "开源方案能覆盖监控，但故障发现→定位→修复的闭环需要人肉。我们做到47秒发现→3秒定位→1秒回滚，全自动。"},
                    {"q": "数据安全怎么保证？能私有化部署吗？", "a": "等保三级+SOC2认证。支持私有化部署，Helm Chart 10分钟部署完成，数据不出你的K8s集群。"},
                    {"q": "免费版和付费版差多少？", "a": "免费版5台主机+3天数据留存。专业版599/月起，无限主机+180天留存+告警通道。企业版支持定制SLA。"},
                    {"q": "接入会不会很麻烦？现有系统要改吗？", "a": "Java/Go/Python/Node.js 4个SDK，pip install一行搞定。不改代码，探针自动采集。平均接入时间<30分钟。"},
                    {"q": "小团队5台服务器用得起吗？", "a": "5台以内永久免费，无功能阉割。超出后按量计费，一台主机约19/月，比一杯咖啡便宜。"},
                ],
                "process": [
                    {"title": "注册接入", "desc": "pip install一行搞定，30分钟完成数据采集"},
                    {"title": "配置告警", "desc": "选预设规则或自定义，5分钟配好通知通道"},
                    {"title": "上线运行", "desc": "全自动巡检+告警，7×24不眨眼盯着"},
                ],
                "guarantee": "14天无条件退款",
                "badges": ["等保三级", "SOC2认证", "7×24监控"],
                "color": "#1d4ed8",
                "phone": "400-890-1234",
                "email": "hi@cloudmonitor.cn",
                "address": "北京市海淀区中关村软件园",
            },
            "教育培训": {
                "hero": f"3个月从零基础到拿offer，完课率78%",
                "sub": "不是看视频自学，是1对1督学+真人批改+就业兜底，完课率从行业平均30%到78%",
                "cta": "试听第一课，不满意不收钱",
                "cta_headline": "零基础？3个月后见分晓",
                "features": [
                    {"title": "1对1督学+真人批改", "description": "每份作业24小时内批改反馈，不是AI自动批，是8年+教研逐行看"},
                    {"title": "模块化课程体系", "description": "不是'系统课程'4个字，是模块1：基础语法→模块2：框架实战→模块3：项目部署，学完1个再进下1个"},
                    {"title": "就业兜底协议", "description": "签协议：学完6个月未就业退全款，已有372位学员成功就业，平均薪资12.8K"},
                    {"title": "无限回放+社区答疑", "description": "课程3年有效期内无限回放，社区1小时内必答，不是扔个录播就不管了"},
                ],
                "about": f"<p>{n}创始团队来自网易、字节跳动技术部门，2019年从线下转线上，发现录播课完课率只有28%。于是我们砍掉录播，改用直播+督学+批改+就业兜底四件套，完课率直接拉到78%。</p><p>目前开设Python、前端、数据分析3个方向，累计毕业学员372人，就业率96.5%，平均起薪12.8K。2024届学员中薪资最高的是28K，入职某大厂。</p>",
                "testimonials": [
                    {"name": "小王", "role": "转行学员 → 字节跳动前端", "rating": 5, "text": "之前自学3个月啥也没学会，报了他们之后3个月拿到字节offer。关键是有人盯着你学，逃不掉。"},
                    {"name": "李姐", "role": "宝妈学员 → 数据分析师", "rating": 4, "text": "课程质量没话说，就是每天要交作业压力挺大的。不过也正是因为这样才学得会，自己学肯定又放弃了。"},
                    {"name": "大刘", "role": "机械转码 → 后端开发", "rating": 5, "text": "第4个月的时候差点放弃，班主任天天微信催我交作业…现在回头看感谢他们的'骚扰'，不然我现在还在拧螺丝。"},
                ],
                "stats": [{"value": "完课率78%", "label": "行业平均30%"}, {"value": "96.5%就业率", "label": "6个月数据"}, {"value": "12.8K平均起薪", "label": "2024届"}],
                "faq": [
                    {"q": "零基础能学会吗？跟不上怎么办？", "a": "能。我们专门为零基础设计了模块0（学前班），2周打基础。跟不上可申请延期1期，不额外收费。"},
                    {"q": "学完真能找到工作吗？和科班比呢？", "a": "96.5%就业率是真实数据。简历+项目+模拟面试三件套，很多学员面试表现比应届科班好，因为有3个实战项目。"},
                    {"q": "学费多少？能分期吗？", "a": "全款12800，分期每月1100左右。签就业协议的学员6个月未就业退全款。也有先学后付方案，找到工作再付款。"},
                    {"q": "每天要花多少时间学？上班族能跟吗？", "a": "每天2-3小时，周末4-5小时。70%的学员是在职转行。直播课有回放，作业截止时间灵活，但每天必须打卡。"},
                    {"q": "和慕课网、极客时间比有什么区别？", "a": "他们是看视频自学，完课率<15%。我们是直播+督学+批改+就业，完课率78%。就像健身请私教vs自己跑步，效果差3倍。"},
                ],
                "process": [
                    {"title": "试听第一课", "desc": "免费体验1节直播课，不满意不报名"},
                    {"title": "入学测试+定制计划", "desc": "2小时摸底测试，生成个人学习路径"},
                    {"title": "直播+作业+就业", "desc": "3个月高强度学习，毕业即推荐面试"},
                ],
                "guarantee": "6个月未就业退全款",
                "badges": ["真人批改", "就业协议", "96.5%就业率"],
                "color": "#7c3aed",
                "phone": "400-667-8901",
                "email": "learn@xuedao.cn",
                "address": "上海市杨浦区五角场",
            },
            "餐饮美食": {
                "hero": f"3个月流水从8万到32万，外卖占比翻3倍",
                "sub": "不是教你做菜，是教你做餐饮生意——选址分析+菜单工程+外卖运营+私域复购",
                "cta": "免费领餐饮诊断报告",
                "cta_headline": "你的餐厅还能再赚多少？",
                "features": [
                    {"title": "菜单工程分析", "description": "不是拍脑袋定价，是按食材成本+制作时间+销量数据算出每道菜的真实利润率，砍掉亏钱菜"},
                    {"title": "外卖平台代运营", "description": "美团+饿了么双平台优化，平均3天提升店铺评分0.3分，月订单量提升120%"},
                    {"title": "私域复购体系", "description": "企微社群+小程序+会员体系，把一次性顾客变成回头客，复购率从15%拉到48%"},
                    {"title": "选址数据评估", "description": "3公里内人流量+消费力+竞品密度三维分析，新店存活率从行业45%提升到82%"},
                ],
                "about": f"<p>{n}创始人开了6年餐厅，踩过选址踩过定价踩过外卖运营所有的坑。后来把踩坑经验系统化成方法论，2022年开始帮同行做咨询，第一家客户3个月流水从8万涨到32万。</p><p>目前服务126家餐饮门店，覆盖快餐、正餐、奶茶、烘焙4个品类。客户平均3个月流水增长180%，最慢的也涨了60%。</p>",
                "testimonials": [
                    {"name": "张姐", "role": "红烧肉大王 老板娘", "rating": 5, "text": "菜单砍了8道菜，利润反而涨了30%。原来有5道菜是亏钱在卖，之前都不知道。"},
                    {"name": "阿强", "role": "鲜茶道 奶茶店长", "rating": 4, "text": "外卖运营确实有两把刷子，3天评分就上去了。就是方案执行需要人手配合，小门店可能忙不过来。"},
                    {"name": "老马", "role": "马记面馆 创始人", "rating": 5, "text": "新店选址他们出的数据报告，预测月流水误差不到10%。现在3家分店全活下来了，隔壁3家倒了2家。"},
                ],
                "stats": [{"value": "126家门店", "label": "服务客户"}, {"value": "180%平均增长", "label": "3个月流水"}, {"value": "82%存活率", "label": "新店1年"}],
                "faq": [
                    {"q": "我生意还行，有必要找你们吗？", "a": "90%的餐厅老板以为自己赚钱了，其实有30%的菜品在亏钱。免费领一份诊断报告，看看到底有没有优化空间。"},
                    {"q": "外卖代运营会不会和堂食冲突？", "a": "不会。我们做的是菜品分仓——堂食卖什么、外卖卖什么，分开定价分开出餐。很多客户外卖和堂食利润都涨了。"},
                    {"q": "收费怎么算？效果不好怎么办？", "a": "基础咨询5800起，代运营抽成3%。签3个月对赌协议，流水没涨20%不收代运营费。"},
                    {"q": "我是小县城的店，你们能做吗？", "a": "能。126家客户里43%是三四线城市。数据模型覆盖全国328个城市，算法是一样的，策略因地制宜。"},
                    {"q": "你们和美团代运营有什么区别？", "a": "美团代运营只管美团一个平台，我们做全渠道（美团+饿了么+私域+堂食）。而且他们抽5-8%，我们只抽3%。"},
                ],
                "process": [
                    {"title": "免费诊断", "desc": "1小时到店调研，3天出诊断报告"},
                    {"title": "方案定制", "desc": "菜单+外卖+私域三线并行，7天出方案"},
                    {"title": "陪跑执行", "desc": "3个月1对1陪跑，周复盘调优"},
                ],
                "guarantee": "3个月流水未涨20%退差价",
                "badges": ["126家实证", "对赌协议", "3%低抽成"],
                "color": "#dc2626",
                "phone": "400-234-5678",
                "email": "hi@canyinzixun.cn",
                "address": "广州市天河区体育西路",
            },
        }
        
        # 默认行业内容
        _default_content = {
            "hero": f"别再为{desc}头疼了，3步搞定",
            "sub": f"从月均23单到月均156单，用数据和方法论替代拍脑袋决策",
            "cta": "30秒看方案，当天出报价",
            "cta_headline": "免费获取专属方案",
            "features": [
                {"title": "多维度数据交叉验证", "description": "支持50+数据源实时接入，3分钟完成数据清洗，识别准确率99.2%"},
                {"title": "秒级异常检测与告警", "description": "故障发现从平均15分钟降到47秒，短信+企微+钉钉三通道通知"},
                {"title": "按业务场景配置分析模型", "description": "6种预设模型+自定义规则，不是千篇一律的模板，按你的流程来"},
                {"title": "一键生成决策报告", "description": "月度/季度/年度报告3秒出稿，之前3人做一周的活现在点一下"},
            ],
            "about": f"<p>{n}由一群在{ind}摸爬滚打多年的实战派创立。我们不信&quot;万能方法论&quot;，只信具体场景下的具体解法。过去3年，帮37家企业实现了可量化的增长——不是PPT上画饼，是实打实的数字。</p><p>团队核心来自行业头部公司，累计服务超200家客户。我们不做一次性交付就跑，所有方案都持续跟进到数据见效为止。</p>",
            "testimonials": [
                {"name": "老周", "role": "锐思科技 CTO", "rating": 5, "text": "合作半年，核心指标从月均23单涨到156单，ROI清清楚楚。最关键是他们不画饼，每步都给数据。"},
                {"name": "Amy", "role": "悦享生活 市场总监", "rating": 4, "text": "方案执行力很强，就是初次沟通花了比较长时间对齐需求，但上手后效率起飞。建议他们把onboarding流程标准化一下。"},
                {"name": "赵工", "role": "博远投资 技术负责人", "rating": 5, "text": "之前靠3个人用Excel手动做报表，现在自动化了，省了2个人力。上线头两周踩了点坑，他们的响应还算快。"},
            ],
            "stats": [{"value": "从0到37家", "label": "服务客户"}, {"value": "3年+深耕", "label": "行业经验"}, {"value": "200+案例", "label": "交付成果"}],
            "faq": [
                {"q": "我现在的工具好好的，为什么要换？", "a": "通用工具能覆盖60%需求，剩下40%正是我们发力的地方。先免费试用14天，用数据说话。"},
                {"q": "数据安全怎么保证？能私有化部署吗？", "a": "数据加密存储，通过等保三级。支持私有化部署，数据不出你的服务器，部署周期3天。"},
                {"q": "免费版和付费版功能差多少？", "a": "免费版月处理量上限1000条，1个分析模型。付费版起步价599/月，无限量+全部模型+专属顾问。"},
                {"q": "我原来的系统数据怎么迁移？", "a": "提供API对接+批量导入，技术1对1协助，平均3天完成切换，停机<2小时。"},
                {"q": "我这种小团队适合用吗？", "a": "3人以上团队就能用。我们30%的客户是10人以下团队，最小的是2人创业公司，月费599起。"},
            ],
            "process": [
                {"title": "需求诊断", "desc": "1对1沟通，摸清现状和目标，1小时出诊断报告"},
                {"title": "方案定制", "desc": "3天内出方案+报价，所有费用写在明面上"},
                {"title": "落地执行", "desc": "专属团队跟进，周报同步进展，2周上线"},
            ],
            "guarantee": "7天无理由退款",
            "badges": ["等保三级", "数据加密", "7×24响应"],
            "color": "#1a73e8",
            "email": "hi@kejitech.cn",
            "phone": "010-62895501",
            "address": f"{n}总部",
        }
        
        ic = _industry_content.get(ind, _default_content)
        
        return {
            "meta_title": f"{n} · {desc} | {ind}解决方案 - 免费试用",
            "meta_description": f"{n}专注{desc}，{ic['sub']}。{ic['cta']}，免费获取专属方案。",
            "meta_keywords": kw,
            "hero_headline": ic["hero"],
            "hero_subheadline": ic["sub"],
            "hero_cta": ic["cta"],
            "features_title": "核心优势",
            "features": ic["features"],
            "about_title": "关于我们",
            "about_content": ic["about"],
            "testimonials_title": "客户怎么说",
            "stats": ic["stats"],
            "testimonials": ic["testimonials"],
            "process_title": "合作流程",
            "process_subtitle": "简单3步",
            "process_steps": ic["process"],
            "faq_title": "常见问题",
            "faq": ic["faq"],
            "cta_headline": ic.get("cta_headline", "准备好提升业务了吗？"),
            "cta_subheadline": f"和{n}聊聊，不花一分钱先看方案",
            "cta_button": ic["cta"],
            "cta_guarantee": ic["guarantee"],
            "cta_trust_badges": [{"text": b} for b in ic["badges"]],
            "footer_text": f"© {n} 版权所有 | 专注{ind}服务",
            "email": info.get("email", ic.get("email", "")),
            "phone": info.get("phone", ic.get("phone", "")),
            "address": info.get("address", ic.get("address", f"{n}总部")),
            "primary_color": ic["color"],
            "og_image": "",
        }

    def _gen_site(self, info: dict) -> dict:
        """生成完整多页网站"""
        n = info["name"]
        ind = info["industry"]
        desc = info["description"]

        return {
            "meta_title": f"{n} · {ind}专业服务官网 - 产品与解决方案",
            "meta_description": f"{n}是{ind}领域专业服务商，专注{desc}与一站式解决方案。查看我们的产品、服务与客户评价，免费获取专属方案。",
            "hero_headline": f"欢迎来到{n}",
            "hero_subheadline": f"专注{desc}，专业的{ind}解决方案",
            "hero_cta": "立即咨询",
            "services_title": "我们的服务",
            "services": [
                {"title": "核心问题诊断", "description": f"1对1深度调研，72小时出具诊断报告，找到{ind}业务增长的核心瓶颈"},
                {"title": "方案落地执行", "description": f"不是PPT交付，是陪跑3个月直到数据见效。{ind}场景实战经验，方案落地率92%"},
                {"title": "持续增长陪跑", "description": "月度复盘+季度调优，不是一锤子买卖，是长期增长伙伴"},
            ],
            "about_title": "关于我们",
            "about_summary": f"{n}是{ind}领域领先的服务提供商，为客户创造最大价值。",
            "story_title": "品牌故事",
            "story_content": f"<p>{n}成立于行业高速发展之时，我们看到了{ind}领域的巨大机会。经过团队的不断努力和创新，如今已服务超过千家客户。</p><p>我们相信，专业和用心是赢得市场的唯一法则。未来，我们将继续深耕{ind}，用更好的服务回馈每一位客户的信任。</p>",
            "team_title": "核心团队",
            "team": [
                {"name": "创始人", "title": "CEO / 连续创业者", "bio": f"8年{ind}行业实战，前阿里P7，带过0到月千万的业务线"},
                {"name": "技术负责人", "title": "CTO / 前大厂架构师", "bio": "6年分布式系统经验，单日处理过12亿条日志峰值"},
                {"name": "运营负责人", "title": "COO / 增长黑客", "bio": "操盘过3个从0到百万用户的增长项目，擅长数据驱动增长"},
            ],
            "values_title": "企业价值观",
            "values": [
                {"title": "客户至上", "description": "一切以客户需求为出发点"},
                {"title": "创新驱动", "description": "持续创新，保持行业领先"},
                {"title": "诚信为本", "description": "以诚待人，以信立业"},
            ],
            "products_title": "产品与服务",
            "products_subtitle": "一站式解决方案",
            "products": [
                {"name": "起步版", "badge": "", "desc": "5人以下团队，月处理量≤1000条", "price": "¥599/月", "features": ["3个分析模型", "邮件支持", "7天数据留存"]},
                {"name": "增长版", "badge": "最受欢迎", "desc": "10-50人团队，不限量处理", "price": "¥1999/月", "features": ["全部模型", "专属顾问", "180天留存", "API访问"]},
                {"name": "企业版", "badge": "", "desc": "50人+，定制化需求", "price": "按需报价", "features": ["私有化部署", "定制开发", "7×24响应", "SLA 99.99%"]},
            ],
            "testimonials_title": "客户评价",
            "testimonials": [
                {"name": "老周", "text": f"和{n}合作2年，核心指标从月均23单到156单，ROI清清楚楚。"},
                {"name": "Amy", "text": "方案落地执行力很强，初次沟通花了2周对齐，但上手后3个月见效。"},
            ],
            "cta_headline": "开启合作之旅",
            "cta_subheadline": "留下联系方式，我们的顾问将为您制定专属方案",
            "cta_button": "免费咨询",
            "blog_title": "博客 · 行业洞察",
            "blog_subtitle": "最新行业动态与深度分析",
            "articles": [
                {"title": f"2025年{ind}行业趋势分析", "date": "2025-03-15", "tag": "行业分析", "excerpt": f"深度解读{ind}行业最新的发展趋势与技术变革..."},
                {"title": f"如何选择靠谱的{ind}服务商", "date": "2025-03-01", "tag": "选购指南", "excerpt": "选择服务商时需要注意的五个关键点..."},
                {"title": f"{ind}数字化转型实践", "date": "2025-02-20", "tag": "技术实践", "excerpt": "从零到一的数字化转型实践经验分享..."},
            ],
            "contact_headline": "联系我们",
            "contact_subtitle": "期待与您的合作",
            "footer_text": f"© {n} 版权所有 | 电话: {info.get('phone', '400-000-0000')} | 邮箱: {info.get('email', f'contact@{n.lower().replace(' ', '')}.com')}",
        }

    def _gen_pricing(self, info: dict) -> dict:
        """生成定价页面"""
        n = info["name"]
        ind = info.get("industry", "")

        return {
            "meta_title": f"{n} {ind}定价方案 - 灵活透明 | 免费试用" if ind else f"{n} 定价方案 - 灵活透明 | 免费试用",
            "meta_description": f"{n}提供{ind}领域三档灵活定价方案，从基础版到企业版满足不同规模企业需求。14天免费试用，随时升级降级，立即选择适合您的方案！" if ind else f"{n}提供三档灵活定价方案，从基础版到企业版满足不同规模企业需求。14天免费试用，随时升级降级，立即选择！",
            "hero_title": "灵活定价，透明收费",
            "hero_subtitle": "选择最适合您的方案，随时升级或降级",
            "pricing_note": "所有方案均支持14天无条件退款",
            "plans": [
                {"name": "基础版", "price": "¥99", "period": "/月", "badge": "", "features": ["3个分析模型", "月处理≤1000条", "7天数据留存", "邮件支持", "99.9%可用性"], "popular": False},
                {"name": "专业版", "price": "¥599", "period": "/月", "badge": "最受欢迎", "features": ["全部模型", "无限处理量", "180天留存", "专属顾问", "API访问", "自定义报表"], "popular": True},
                {"name": "企业版", "price": "¥1999", "period": "/月", "badge": "", "features": ["专业版全部", "私有化部署", "白标授权", "定制开发", "7×24响应", "SLA 99.99%"], "popular": False},
            ],
            "cta_title": "还有疑问？",
            "cta_subtitle": "我们的销售团队随时为您解答",
            "cta_button": "联系销售",
            "footer_text": f"© {n} 版权所有 | 价格可能随市场调整，以实际报价为准",
            "faq": [
                {"q": "免费版和付费版差多少？", "a": "免费版3个模型+月1000条+7天留存。专业版解锁全部模型+无限量+180天留存+专属顾问，599/月起。"},
                {"q": "可以随时取消吗？会被扣钱吗？", "a": "随时取消，按天折算退余款。比如月中取消，退下半个月费用。无违约金。"},
                {"q": "数据安全怎么保证？", "a": "数据加密存储(AES-256)，等保三级认证。企业版支持私有化部署，数据不出你的服务器。"},
            ],
        }
