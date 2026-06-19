"""
岗位典型工作任务转化 Agent
将岗位典型工作任务自动转化为教学用学习型工作任务，实现「以岗定教」
赛题核心方向3：岗位典型工作任务转化成学习型任务
"""

import os
import json
import re
import requests
from typing import Dict, List

ZHIPUAI_API_KEY = os.environ.get(
    "ZHIPUAI_API_KEY",
    "a3a3123abff546999aeb4547885c4ae8.PocEri894pv9APeu"
)

def _call_glm(messages: list, temperature: float = 0.3, timeout: int = 20) -> str:
    try:
        from core.utils.jwt_helper import generate_token
        token = generate_token(ZHIPUAI_API_KEY)
        resp = requests.post(
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "model": "glm-4-flash",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 2000,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise RuntimeError("AI请求超时")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("AI服务连接失败")
    except Exception as e:
        raise RuntimeError(f"AI调用失败: {str(e)[:80]}")


def _extract_json(content: str) -> dict:
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
    if json_match:
        return json.loads(json_match.group(1))
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    if json_start >= 0 and json_end > json_start:
        return json.loads(content[json_start:json_end])
    raise ValueError("无法从AI返回中提取JSON")


# 预置的典型工作任务→学习型任务转化数据（fallback用）
FALLBACK_TASKS = {
    "前端开发工程师": {
        "job_name": "前端开发工程师",
        "typical_tasks": [
            {
                "task_id": "T001",
                "task_name": "开发响应式电商首页",
                "task_type": "典型工作任务",
                "description": "根据UI设计稿，使用HTML5/CSS3/JavaScript开发适配多端的电商首页，包含轮播图、商品列表、搜索框等模块",
                "source": "《Web前端开发职业技能等级标准》高级典型工作任务",
                "learning_tasks": [
                    {
                        "lt_id": "LT001-1",
                        "lt_name": "页面结构与语义化布局",
                        "knowledge_points": ["HTML5语义化标签", "SEO友好结构", "微数据标记"],
                        "practice": "使用header/nav/main/section/footer重构电商首页骨架",
                        "assessment": "输出完整HTML结构，通过W3C验证",
                        "hours": 4,
                        "difficulty": "基础"
                    },
                    {
                        "lt_id": "LT001-2",
                        "lt_name": "CSS3响应式布局实现",
                        "knowledge_points": ["Flexbox布局", "媒体查询", "移动优先策略", "CSS变量"],
                        "practice": "使用Flexbox+媒体查询实现3端适配（手机/平板/桌面）",
                        "assessment": "3种屏幕尺寸下布局无错位，Lighthouse移动评分>90",
                        "hours": 8,
                        "difficulty": "进阶"
                    },
                    {
                        "lt_id": "LT001-3",
                        "lt_name": "交互功能开发",
                        "knowledge_points": ["DOM操作", "事件委托", "防抖节流", "Fetch API"],
                        "practice": "实现轮播图自动播放+手势切换、搜索框防抖、商品懒加载",
                        "assessment": "交互流畅无卡顿，滚动帧率>55fps",
                        "hours": 8,
                        "difficulty": "进阶"
                    },
                    {
                        "lt_id": "LT001-4",
                        "lt_name": "性能优化与部署",
                        "knowledge_points": ["资源压缩", "图片懒加载", "CDN", "关键渲染路径"],
                        "practice": "配置Vite构建优化，图片转WebP，实施资源预加载",
                        "assessment": "FCP<1.5s, LCP<2.5s, CLS<0.1",
                        "hours": 6,
                        "difficulty": "高级"
                    }
                ],
                "total_hours": 26,
                "mapped_courses": ["HTML5+CSS3网页设计", "JavaScript程序设计", "前端框架开发", "Web性能优化"]
            },
            {
                "task_id": "T002",
                "task_name": "开发后台管理系统",
                "task_type": "典型工作任务",
                "description": "使用Vue3+Element Plus开发企业后台管理系统，包含登录鉴权、动态路由、数据表格CRUD、权限控制",
                "source": "《Web前端开发职业技能等级标准》高级典型工作任务",
                "learning_tasks": [
                    {
                        "lt_id": "LT002-1",
                        "lt_name": "项目搭建与路由配置",
                        "knowledge_points": ["Vite项目初始化", "Vue Router", "路由守卫", "动态路由"],
                        "practice": "搭建Vue3项目，配置动态路由与导航守卫",
                        "assessment": "路由切换正常，权限拦截生效",
                        "hours": 6,
                        "difficulty": "进阶"
                    },
                    {
                        "lt_id": "LT002-2",
                        "lt_name": "登录鉴权与权限系统",
                        "knowledge_points": ["JWT认证", "Token刷新", "RBAC权限模型", "Pinia状态管理"],
                        "practice": "实现登录页+Token管理+角色权限控制",
                        "assessment": "未登录跳转登录页，不同角色看到不同菜单",
                        "hours": 8,
                        "difficulty": "进阶"
                    },
                    {
                        "lt_id": "LT002-3",
                        "lt_name": "数据表格与CRUD操作",
                        "knowledge_points": ["组件封装", "Axios封装", "表单验证", "分页查询"],
                        "practice": "封装通用表格组件，实现增删改查完整流程",
                        "assessment": "CRUD操作正常，表单验证完整，分页准确",
                        "hours": 10,
                        "difficulty": "进阶"
                    },
                    {
                        "lt_id": "LT002-4",
                        "lt_name": "系统优化与部署",
                        "knowledge_points": ["代码分割", "按需加载", "构建优化", "Nginx部署"],
                        "practice": "配置按需加载、代码分割，部署到服务器",
                        "assessment": "首屏加载<2s，Lighthouse评分>80",
                        "hours": 6,
                        "difficulty": "高级"
                    }
                ],
                "total_hours": 30,
                "mapped_courses": ["Vue3框架开发", "Node.js后端开发", "数据库基础", "软件测试"]
            },
            {
                "task_id": "T003",
                "task_name": "对接第三方API与数据可视化",
                "task_type": "典型工作任务",
                "description": "对接RESTful API获取业务数据，使用ECharts实现数据看板，包含实时图表、大屏适配、数据导出",
                "source": "《Web前端开发职业技能等级标准》高级典型工作任务",
                "learning_tasks": [
                    {
                        "lt_id": "LT003-1",
                        "lt_name": "API对接与数据处理",
                        "knowledge_points": ["Axios封装", "请求拦截", "错误处理", "数据转换"],
                        "practice": "封装HTTP请求模块，实现统一错误处理和Token注入",
                        "assessment": "API调用健壮，网络异常有友好提示",
                        "hours": 6,
                        "difficulty": "进阶"
                    },
                    {
                        "lt_id": "LT003-2",
                        "lt_name": "ECharts图表开发",
                        "knowledge_points": ["ECharts配置", "响应式图表", "大数据渲染", "图表交互"],
                        "practice": "开发折线图/柱状图/饼图/地图4种图表组件",
                        "assessment": "图表渲染正确，交互流畅，10万条数据不卡顿",
                        "hours": 10,
                        "difficulty": "进阶"
                    },
                    {
                        "lt_id": "LT003-3",
                        "lt_name": "大屏适配与实时更新",
                        "knowledge_points": ["rem适配", "WebSocket", "定时刷新", "数据动画"],
                        "practice": "实现1920x1080大屏自适应，WebSocket实时数据推送",
                        "assessment": "大屏显示正常，数据延迟<1s",
                        "hours": 8,
                        "difficulty": "高级"
                    }
                ],
                "total_hours": 24,
                "mapped_courses": ["JavaScript高级编程", "数据可视化", "网络编程", "前端综合实战"]
            }
        ]
    }
}


def convert_task_to_learning(job_name: str, task_name: str, task_description: str = "") -> Dict:
    """将典型工作任务转化为学习型任务，10秒超时"""
    prompt = f"""你是职业教育课程设计专家。将岗位典型工作任务转化为教学用学习型工作任务。

岗位：{job_name}
典型工作任务：{task_name}
任务描述：{task_description or '根据岗位要求自行推演'}

严格输出JSON（无其他文字）：
```json
{{
  "job_name": "{job_name}",
  "task_name": "{task_name}",
  "task_type": "典型工作任务",
  "description": "任务描述",
  "source": "《Web前端开发职业技能等级标准》",
  "learning_tasks": [
    {{
      "lt_id": "LT001",
      "lt_name": "学习型任务名称",
      "knowledge_points": ["知识点1", "知识点2"],
      "practice": "具体实践内容",
      "assessment": "考核标准",
      "hours": 6,
      "difficulty": "基础/进阶/高级"
    }}
  ],
  "total_hours": 24,
  "mapped_courses": ["对应课程1", "对应课程2"]
}}
```
至少拆解为3-4个递进式学习型任务，从基础到高级，每个任务包含知识点、实践、考核标准、学时。"""

    messages = [
        {"role": "system", "content": "你是职业教育课程设计专家。只输出JSON，不解释。"},
        {"role": "user", "content": prompt},
    ]
    content = _call_glm(messages, timeout=10)
    return _extract_json(content)


def get_fallback_tasks(job_name: str) -> Dict:
    """获取预置的典型工作任务→学习型任务数据"""
    if job_name in FALLBACK_TASKS:
        return FALLBACK_TASKS[job_name]
    # 通用fallback
    return {
        "job_name": job_name,
        "typical_tasks": FALLBACK_TASKS["前端开发工程师"]["typical_tasks"],
        "note": "使用前端开发工程师岗位的预置数据作为参考示例"
    }
