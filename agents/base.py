"""Agent基类 - v2.4.0
新增：_parse_llm_output / _validate_result
LLM_TIMEOUT改为60秒
"""
import os
import re
import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List


class BaseAgent(ABC):
    """所有Agent的基类"""
    
    
    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description
        self.last_result: Optional[dict] = None
    
    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """执行Agent的核心逻辑"""
        pass
    
    def info(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
        }
    
    # 默认LLM超时（秒） - 从30秒提升到60秒
    LLM_TIMEOUT = 60

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """调用智谱GLM-4-flash，带超时和重试"""
        from zhipuai import ZhipuAI
        api_key = os.environ.get("ZHIPUAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("ZHIPUAI_API_KEY环境变量未设置，请在Render环境变量中配置")
        
        client = ZhipuAI(api_key=api_key, timeout=self.LLM_TIMEOUT)
        last_err = None
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                last_err = e
                if attempt == 0 and ("timeout" in str(e).lower() or "connection" in str(e).lower()):
                    continue  # 重试一次
                raise
        raise last_err

    def _parse_llm_output(self, raw_text: str, expected_schema: Optional[Dict] = None) -> dict:
        """
        解析LLM输出的JSON，处理各种包裹情况
        
        处理场景：
        1. 纯JSON字符串
        2. ```json ... ``` 代码块包裹
        3. ``` ... ``` 代码块包裹（无语言标记）
        4. JSON前后有额外文本
        5. 单引号代替双引号
        
        Args:
            raw_text: LLM原始输出文本
            expected_schema: 期望的JSON结构（用于验证，可选）
            
        Returns:
            解析后的dict
            
        Raises:
            ValueError: 无法解析为有效JSON
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("LLM输出为空")
        
        text = raw_text.strip()
        
        # 策略1：尝试直接解析
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        
        # 策略2：去除markdown代码块包裹
        # 匹配 ```json ... ``` 或 ``` ... ```
        code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            inner = match.group(1).strip()
            try:
                result = json.loads(inner)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        
        # 策略3：提取文本中的第一个JSON对象（{ ... }）
        # 找到第一个 { 和最后一个匹配的 }
        brace_start = text.find('{')
        if brace_start >= 0:
            # 从 { 开始找匹配的 }
            depth = 0
            for i in range(brace_start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[brace_start:i+1]
                        try:
                            result = json.loads(candidate)
                            if isinstance(result, dict):
                                return result
                        except json.JSONDecodeError:
                            break
        
        # 策略4：尝试修复常见问题
        # 单引号 → 双引号
        fixed = text.replace("'", '"')
        # 移除尾随逗号（JSON标准不允许）
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        try:
            result = json.loads(fixed)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
        
        # 策略5：如果是代码块+修复
        if match:
            inner = match.group(1).strip().replace("'", '"')
            inner = re.sub(r',\s*([}\]])', r'\1', inner)
            try:
                result = json.loads(inner)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"无法解析LLM输出为JSON，原始输出前200字符：{text[:200]}")

    def _validate_result(self, result: dict, schema: Dict) -> tuple:
        """
        验证结果是否符合预期schema
        
        Args:
            result: 待验证的字典
            schema: 期望的结构，格式：
                {
                    "field_name": {"type": str, "required": True},
                    "optional_field": {"type": list, "required": False, "default": []},
                }
        
        Returns:
            (is_valid: bool, errors: List[str])
        """
        if not isinstance(result, dict):
            return False, ["结果不是字典类型"]
        
        errors = []
        
        for field_name, field_spec in schema.items():
            field_type = field_spec.get("type", str)
            required = field_spec.get("required", True)
            default = field_spec.get("default")
            
            if field_name not in result:
                if required:
                    errors.append(f"缺少必填字段: {field_name}")
                elif default is not None:
                    result[field_name] = default
                continue
            
            # 类型检查
            value = result[field_name]
            if value is not None and not isinstance(value, field_type):
                # 宽容处理：int/float互转
                if field_type == float and isinstance(value, int):
                    result[field_name] = float(value)
                elif field_type == int and isinstance(value, float) and value == int(value):
                    result[field_name] = int(value)
                elif field_type == list and isinstance(value, str):
                    # 字符串 → 单元素列表
                    result[field_name] = [value]
                else:
                    errors.append(f"字段 '{field_name}' 类型错误：期望 {field_type.__name__}，实际 {type(value).__name__}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
