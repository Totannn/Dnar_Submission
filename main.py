"""
ML Inference Service - Transaction Risk Scoring
Production-ready service for real-time fraud detection and AML compliance

Business Context (Dnar):
- Real-time crypto-to-fiat transaction risk assessment
- AML (Anti-Money Laundering) compliance scoring
- Fraud detection for institutional transactions
- Regulatory compliance (KYC/AML requirements)
"""
import os
import pickle
import logging
import time
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel, Field, validator
import numpy as np
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi.responses import Response
import hashlib
import uuid

# Configure logging - FIXED: Removed correlation_id from format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics for observability
PREDICTION_COUNTER = Counter(
    'transaction_risk_scores_total',
    'Total transaction risk assessments',
    ['model_version', 'risk_level', 'status']
)

PREDICTION_LATENCY = Histogram(
    'transaction_risk_latency_seconds',
    'Transaction risk scoring latency',
    ['model_version'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

HIGH_RISK_TRANSACTIONS = Gauge(
    'high_risk_transactions_last_hour',
    'Count of high-risk transactions in last hour'
)

MODEL_DRIFT_SCORE = Gauge(
    'model_drift_psi_score',
    'Population Stability Index for drift detection'
)

# Global model and configuration
model = None
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# Audit log storage
audit_logs = []


class TransactionFeatures(BaseModel):
    """Transaction features for risk scoring"""
    transaction_amount_usd: float = Field(..., ge=0)
    sender_age_days: int = Field(..., ge=0)
    transactions_last_24h: int = Field(..., ge=0, le=1000)
    avg_transaction_amount: float = Field(..., ge=0)
    sender_country_risk_score: float = Field(..., ge=0, le=1)
    is_new_recipient: bool
    hour_of_day: int = Field(..., ge=0, le=23)
    
    @validator('transaction_amount_usd')
    def validate_amount(cls, v):
        if v > 1_000_000:
            raise ValueError("Transaction amount exceeds maximum limit")
        return v


class RiskScoreRequest(BaseModel):
    """Request schema for transaction risk scoring"""
    transaction_id: str
    features: TransactionFeatures
    customer_id: Optional[str] = None


class RiskScoreResponse(BaseModel):
    """Response schema for risk assessment"""
    transaction_id: str
    risk_score: float
    risk_level: str
    recommendation: str
    model_version: str
    timestamp: str
    correlation_id: str
    features_hash: str
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    model_version: str
    environment: str
    uptime_seconds: float


SERVICE_START_TIME = time.time()


def load_model():
    """Load the ML model from disk"""
    global model
    # FIXED: Use relative path for Windows compatibility
    model_path = os.getenv("MODEL_PATH", "models/model.pkl")
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        logger.info(f"Model loaded successfully: {model_path}, version: {MODEL_VERSION}")
        return model
    except FileNotFoundError:
        logger.error(f"Model file not found at {model_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise


def create_audit_log(
    transaction_id: str,
    risk_score: float,
    risk_level: str,
    recommendation: str,
    correlation_id: str,
    customer_id: Optional[str] = None
):
    """Create audit log entry for regulatory compliance"""
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "model_version": MODEL_VERSION,
        "environment": ENVIRONMENT,
        "correlation_id": correlation_id
    }
    audit_logs.append(audit_entry)
    logger.info(f"Audit log created, correlation_id={correlation_id}")
    return audit_entry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown"""
    logger.info(f"Starting ML inference service - Environment: {ENVIRONMENT}")
    load_model()
    yield
    logger.info("Shutting down ML inference service")


app = FastAPI(
    title="Transaction Risk Scoring API",
    description="Real-time ML-powered fraud detection and AML compliance",
    version=MODEL_VERSION,
    lifespan=lifespan
)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests for traceability"""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    uptime = time.time() - SERVICE_START_TIME
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_version": MODEL_VERSION,
        "environment": ENVIRONMENT,
        "uptime_seconds": uptime
    }


@app.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """Readiness check endpoint"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    uptime = time.time() - SERVICE_START_TIME
    return {
        "status": "ready",
        "model_loaded": True,
        "model_version": MODEL_VERSION,
        "environment": ENVIRONMENT,
        "uptime_seconds": uptime
    }


@app.post("/score", response_model=RiskScoreResponse)
async def score_transaction(
    request: RiskScoreRequest,
    x_api_key: Optional[str] = Header(None),
    x_correlation_id: Optional[str] = Header(None)
):
    """Score transaction risk in real-time"""
    start_time = time.time()
    correlation_id = x_correlation_id or str(uuid.uuid4())
    
    if model is None:
        PREDICTION_COUNTER.labels(
            model_version=MODEL_VERSION,
            risk_level="ERROR",
            status="error"
        ).inc()
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Convert features to numpy array
        features_dict = request.features.dict()
        feature_vector = np.array([
            features_dict['transaction_amount_usd'],
            features_dict['sender_age_days'],
            features_dict['transactions_last_24h'],
            features_dict['avg_transaction_amount'],
            features_dict['sender_country_risk_score'],
            1 if features_dict['is_new_recipient'] else 0,
            features_dict['hour_of_day']
        ]).reshape(1, -1)
        
        # Hash features for audit trail
        features_hash = hashlib.sha256(
            str(features_dict).encode()
        ).hexdigest()
        
        # Make prediction
        with PREDICTION_LATENCY.labels(model_version=MODEL_VERSION).time():
            risk_score = float(model.predict_proba(feature_vector)[0][1])
        
        # Determine risk level and recommendation
        if risk_score < 0.3:
            risk_level = "LOW"
            recommendation = "APPROVE"
        elif risk_score < 0.6:
            risk_level = "MEDIUM"
            recommendation = "REVIEW"
        elif risk_score < 0.8:
            risk_level = "HIGH"
            recommendation = "REVIEW"
        else:
            risk_level = "CRITICAL"
            recommendation = "REJECT"
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Update metrics
        PREDICTION_COUNTER.labels(
            model_version=MODEL_VERSION,
            risk_level=risk_level,
            status="success"
        ).inc()
        
        if risk_level in ["HIGH", "CRITICAL"]:
            HIGH_RISK_TRANSACTIONS.inc()
        
        # Create audit log
        create_audit_log(
            transaction_id=request.transaction_id,
            risk_score=risk_score,
            risk_level=risk_level,
            recommendation=recommendation,
            correlation_id=correlation_id,
            customer_id=request.customer_id
        )
        
        logger.info(
            f"Transaction scored: {request.transaction_id}, "
            f"risk={risk_score:.3f}, level={risk_level}, "
            f"recommendation={recommendation}, correlation_id={correlation_id}"
        )
        
        return {
            "transaction_id": request.transaction_id,
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "recommendation": recommendation,
            "model_version": MODEL_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "features_hash": features_hash,
            "processing_time_ms": round(processing_time_ms, 2)
        }
    
    except ValueError as e:
        PREDICTION_COUNTER.labels(
            model_version=MODEL_VERSION,
            risk_level="ERROR",
            status="validation_error"
        ).inc()
        logger.error(f"Validation error: {e}, correlation_id={correlation_id}")
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    
    except Exception as e:
        PREDICTION_COUNTER.labels(
            model_version=MODEL_VERSION,
            risk_level="ERROR",
            status="error"
        ).inc()
        logger.error(f"Prediction error: {e}, correlation_id={correlation_id}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    x_api_key: Optional[str] = Header(None)
):
    """Retrieve audit logs"""
    return {
        "total": len(audit_logs),
        "logs": audit_logs[-limit:]
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Transaction Risk Scoring API",
        "version": MODEL_VERSION,
        "environment": ENVIRONMENT,
        "business_context": "Real-time fraud detection for crypto-fiat transactions",
        "endpoints": {
            "score": "/score (POST)",
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics",
            "audit": "/audit-logs",
            "docs": "/docs"
        }
    }