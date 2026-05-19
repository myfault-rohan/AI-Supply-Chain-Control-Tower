"""
Pydantic Response Models for API Endpoints
Provides type-safe, documented response schemas for the FastAPI OpenAPI specification.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class HealthCheck(BaseModel):
    """API health check response."""
    status: str = Field(json_schema_extra={"example": "ok"})
    version: str = Field(json_schema_extra={"example": "2.0.0"})
    timestamp: str = Field(json_schema_extra={"example": "2026-03-11T12:00:00"})


class TokenRequest(BaseModel):
    """Login credentials for JWT token generation."""
    username: str = Field(json_schema_extra={"example": "admin"})
    password: str = Field(json_schema_extra={"example": "admin123"})


class TokenResponse(BaseModel):
    """JWT token response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    username: Optional[str] = None


class UserCreate(BaseModel):
    """Payload used when creating a new user."""
    username: str
    email: Optional[str]
    password: str


class UserResponse(BaseModel):
    """Response model for user objects."""
    id: Optional[int]
    username: str
    email: Optional[str]
    role: Optional[str] = "analyst"
    is_active: bool = True


class InventoryItem(BaseModel):
    """Single inventory item with stock metrics."""
    product_id: str
    warehouse_id: str
    current_stock: float
    safety_stock: float
    reorder_point: float
    inventory_days: Optional[float] = None


class DemandForecast(BaseModel):
    """Demand prediction for a product."""
    product_id: str
    predicted_demand: float
    avg_daily_sales: Optional[float] = None
    demand_spike: Optional[bool] = None


class Alert(BaseModel):
    """Supply chain alert notification."""
    product_id: str
    days_until_stockout: float
    alert_message: str


class ReorderRecommendation(BaseModel):
    """Reorder recommendation for a product."""
    product_id: str
    reorder_quantity: float
    supplier_lead_time: float
    alert_message: str


class HealthMetric(BaseModel):
    """Supply chain health metric for a product."""
    product_id: str
    current_stock: float
    predicted_demand: float
    days_until_stockout: float
    reorder_quantity: float
    health_status: str
    health_score: int


class SupplierPerformance(BaseModel):
    """Supplier performance metrics."""
    supplier_id: str
    average_delay: float
    total_shipments: int
    reliability_score: float
    supplier_status: str


class WarehouseUtilization(BaseModel):
    """Warehouse utilization metrics."""
    warehouse_id: str
    warehouse_location: str
    capacity: float
    total_stock: float
    utilization_percent: float
    status: str


class CostAnalysis(BaseModel):
    """Cost analysis for a product."""
    product_id: str
    inventory_holding_cost: float
    stockout_cost: float
    total_cost_impact: float


class GlobalRiskSummary(BaseModel):
    """Aggregated global risk summary."""
    critical_products: int
    unreliable_suppliers: int
    overloaded_warehouses: int
    high_cost_products: int


class UploadResponse(BaseModel):
    """Response after data upload and processing."""
    message: str
    files: List[str]
    workspace: str


class SystemHealth(BaseModel):
    """Administrative system health metrics."""
    status: str
    api_version: str
    workspaces: int
    processed_files: int
    storage_usage_mb: float


class DataQualityReport(BaseModel):
    """Data quality assessment for a dataset."""
    filename: str
    total_rows: int
    total_columns: int
    null_counts: dict
    duplicate_rows: int
    quality_score: float
    issues: List[str]
