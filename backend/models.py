"""
SQLAlchemy ORM Models for Supply Chain Platform.
Includes: Users, Products, Suppliers, Inventory, Forecasts, Alerts.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    """User model for authentication and workspace isolation."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    role = Column(String(20), default="analyst")  # analyst, manager, admin
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationships
    uploads = relationship("DataUpload", back_populates="user", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="user", cascade="all, delete-orphan")


class DataUpload(Base):
    """Track uploaded data files and their metadata."""
    __tablename__ = "data_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    data_type = Column(String(50))  # inventory, sales, suppliers, etc.
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)

    user = relationship("User", back_populates="uploads")


class Product(Base):
    """Product master data."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), unique=True, index=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    current_stock = Column(Float, default=0)
    safety_stock = Column(Float, default=0)
    reorder_point = Column(Float, default=0)
    warehouse_id = Column(String(50), nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    forecasts = relationship("Forecast", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete-orphan")


class Supplier(Base):
    """Supplier master data and performance metrics."""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(String(50), unique=True, index=True, nullable=False)
    supplier_name = Column(String(255), nullable=False)
    lead_time_days = Column(Float, default=7)
    reliability_score = Column(Float, default=100)
    delay_rate = Column(Float, default=0)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE, AT_RISK
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Forecast(Base):
    """ML-generated demand forecasts."""
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    predicted_demand = Column(Float, nullable=False)
    avg_daily_sales = Column(Float, nullable=False)
    demand_spike = Column(Boolean, default=False)
    days_until_stockout = Column(Float, nullable=False)
    
    model_version = Column(String(20), default="v1.0")
    confidence_score = Column(Float, default=0.85)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="forecasts")
    product = relationship("Product", back_populates="forecasts")


class Alert(Base):
    """Operational alerts: stockouts, delays, anomalies."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    alert_type = Column(String(50))  # STOCKOUT, DELAY, ANOMALY, COST
    severity = Column(String(20))  # CRITICAL, WARNING, INFO
    message = Column(Text, nullable=False)
    
    is_acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    acknowledged_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="alerts")


class ReorderRecommendation(Base):
    """Generated reorder suggestions from the optimization engine."""
    __tablename__ = "reorder_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), nullable=False, index=True)
    
    reorder_quantity = Column(Float, nullable=False)
    supplier_lead_time = Column(Float, nullable=False)
    stockout_risk = Column(Boolean, default=False)
    recommended_action = Column(Text, nullable=False)
    
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    priority = Column(Integer, default=0)  # 1=critical, 2=high, 3=medium


class SystemMetric(Base):
    """System health and performance metrics over time."""
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Examples: api_response_time, db_query_time, forecast_accuracy, etc.
