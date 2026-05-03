from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Date, Text, UUID, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


# ============================================
# MULTI-TENANT MODELS (NEW)
# ============================================

class Organization(Base):
    """Organization/Tenant model for multi-tenancy"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)  # Company name
    slug = Column(String(255), unique=True, nullable=False, index=True)  # URL-friendly slug
    tier = Column(String(50), default="free", nullable=False)  # free, pro, business, enterprise
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")
    predictions = relationship("PredictionRecord", back_populates="organization", cascade="all, delete-orphan")
    metrics = relationship("ModelMetrics", back_populates="organization", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    """Organization member with roles"""
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="member", nullable=False)  # admin, member, viewer
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Unique constraint: one user per org
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="org_memberships")


class APIKey(Base):
    """API Keys for organizations (separate from User model)"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Human-readable name
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # SHA256 hashed
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")


# ============================================
# MODIFIED USER MODEL (for multi-tenant)
# ============================================

class User(Base):
    """User model (now org-scoped)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, index=True)  # No longer globally unique
    email = Column(String(255), unique=True, nullable=False, index=True)  # Email is global unique
    api_key = Column(String(255), unique=True, nullable=False, index=True)  # Legacy, kept for backward compat
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    org_memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("PredictionRecord", back_populates="user", cascade="all, delete-orphan")
    metrics = relationship("ModelMetrics", back_populates="user", cascade="all, delete-orphan")




# ============================================
# MULTI-TENANT DATA MODELS
# ============================================

class PredictionRecord(Base):
    """Individual prediction records with multi-tenant isolation"""
    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)  # NEW: Tenant context
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    input_text = Column(Text, nullable=False)
    prediction = Column(String(50), nullable=False)  # POSITIVE or NEGATIVE
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    inference_time_ms = Column(Float, nullable=False)  # Model latency in milliseconds
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    request_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    archived = Column(Boolean, default=False, index=True)

    # NEW: Composite indexes for org isolation
    __table_args__ = (
        UniqueConstraint("organization_id", "request_id", name="uq_org_request_id"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="predictions")
    user = relationship("User", back_populates="predictions")




class ModelMetrics(Base):
    """Daily aggregate metrics for performance tracking (multi-tenant)"""
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)  # NEW: Tenant context
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    predictions_count = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    avg_inference_time_ms = Column(Float, default=0.0)
    date = Column(Date, nullable=False, index=True)

    # NEW: Composite indexes for org isolation
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "date", name="uq_org_user_date"),
    )

    # Relationships
    organization = relationship("Organization", back_populates="metrics")
    user = relationship("User", back_populates="metrics")


# ============================================
# BILLING MODELS (NEW for SaaS)
# ============================================

class SubscriptionTier(Base):
    """Subscription tier definitions"""
    __tablename__ = "subscription_tiers"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # free, pro, business, enterprise
    price_usd = Column(Integer, default=0)  # Price in cents ($29 = 2900)
    requests_per_month = Column(Integer, nullable=False)  # Monthly request limit
    batch_limit = Column(Integer, default=100)  # Max batch prediction size
    rate_limit_rpm = Column(Integer, default=1000)  # Requests per minute
    features = Column(Text, default="")  # JSON features list

    # Relationships
    subscriptions = relationship("Subscription", back_populates="tier")


class Subscription(Base):
    """Organization subscription to a tier"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), nullable=False, index=True)
    status = Column(String(50), default="active", nullable=False, index=True)  # active, canceled, past_due
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)  # Stripe subscription ID
    stripe_customer_id = Column(String(255), nullable=True, index=True)  # Stripe customer ID
    billing_cycle_start = Column(DateTime, default=datetime.utcnow)
    billing_cycle_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="subscriptions")
    tier = relationship("SubscriptionTier", back_populates="subscriptions")


class UsageQuota(Base):
    """Track org usage against their tier limits"""
    __tablename__ = "usage_quotas"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), nullable=False)
    requests_used_this_month = Column(Integer, default=0)
    billing_period_start = Column(DateTime, default=datetime.utcnow, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invoice(Base):
    """Billing invoices for subscriptions"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    stripe_invoice_id = Column(String(255), unique=True, nullable=True)
    amount_cents = Column(Integer, nullable=False)  # Amount in cents
    status = Column(String(50), default="draft", nullable=False)  # draft, open, paid, void, uncollectible
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)

