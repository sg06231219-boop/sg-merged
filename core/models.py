"""
core.models — SQLAlchemy 2.0 ORM 模型（Mapped 风格）

支持多租户（Tenant）+ 单租户（SQLite 兼容）
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    String, Text, Float, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, _IS_SQLITE


def _pk() -> Mapped[str]:
    return mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime, default=datetime.utcnow)


def _json() -> Mapped[Optional[dict]]:
    return mapped_column(JSON, nullable=True)


# ════════════════════════════════════════════════
# 1. 租户（多租户核心）
# ════════════════════════════════════════════════
class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = _pk()
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="free")
    settings: Mapped[Optional[dict]] = _json()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users: Mapped[List["User"]] = relationship(back_populates="tenant")
    sites: Mapped[List["Site"]] = relationship(back_populates="tenant")
    products: Mapped[List["Product"]] = relationship(back_populates="tenant")
    orders: Mapped[List["Order"]] = relationship(back_populates="tenant")


# ════════════════════════════════════════════════
# 2. 用户（RBAC）
# ════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trial_available: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant: Mapped[Optional["Tenant"]] = relationship(back_populates="users")
    sites: Mapped[List["Site"]] = relationship(back_populates="user")
    orders: Mapped[List["Order"]] = relationship(back_populates="user")
    ai_usage: Mapped[List["AIUsage"]] = relationship(back_populates="user")


# ════════════════════════════════════════════════
# 3. 生成的站点
# ════════════════════════════════════════════════
class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    config: Mapped[Optional[dict]] = _json()
    html_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_pro: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship(back_populates="sites")
    user: Mapped["User"] = relationship(back_populates="sites")


# ════════════════════════════════════════════════
# 4. 商品（电商）
# ════════════════════════════════════════════════
class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[Optional[dict]] = _json()
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship(back_populates="products")


# ════════════════════════════════════════════════
# 5. 购物车
# ════════════════════════════════════════════════
class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    items: Mapped[Optional[dict]] = _json()
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ════════════════════════════════════════════════
# 6. 订单
# ════════════════════════════════════════════════
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    items: Mapped[Optional[dict]] = _json()
    total: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    payment_method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    payment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    shipping_address: Mapped[Optional[dict]] = _json()
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship(back_populates="orders")
    user: Mapped[Optional["User"]] = relationship(back_populates="orders")


# ════════════════════════════════════════════════
# 7. 询盘（联系表单）
# ════════════════════════════════════════════════
class Inquiry(Base):
    __tablename__ = "inquiries"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    site_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sites.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new")
    reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ════════════════════════════════════════════════
# 8. 激活码（付费激活）
# ════════════════════════════════════════════════
class ActivationCode(Base):
    __tablename__ = "activation_codes"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(32), default="pro")
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = _now()


# ════════════════════════════════════════════════
# 9. AI 使用记录（计费/限流）
# ════════════════════════════════════════════════
class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    tool_type: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = _now()

    tenant: Mapped["Tenant"] = relationship()
    user: Mapped[Optional["User"]] = relationship(back_populates="ai_usage")


# ════════════════════════════════════════════════
# 10. 订阅（SaaS 计费）
# ════════════════════════════════════════════════
class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = _pk()
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    provider_customer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
