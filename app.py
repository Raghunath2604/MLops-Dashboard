from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import Response, JSONResponse
from fastapi.security import HTTPBearer
from transformers import pipeline
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
import time
import logging
import sys
import os
from datetime import datetime, date, timedelta
import uuid
from io import StringIO
import csv
import json

# Rate limiting and billing
from rate_limiter import get_rate_limiter
from billing import get_stripe_integration

# OpenTelemetry Tracing
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Import database and auth modules
from database import get_db, init_db, close_db
from models import User, PredictionRecord, ModelMetrics, Organization, APIKey, OrganizationMember, Subscription, SubscriptionTier
from auth import (
    generate_api_key, hash_api_key, create_access_token,
    verify_token, authenticate_with_api_key, authenticate_with_credentials
)

# ---------------------------------------------------
# 1. OpenTelemetry Jaeger Setup
# ---------------------------------------------------
jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_HOST", "jaeger"),
    agent_port=int(os.getenv("JAEGER_PORT", 6831)),
)

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Instrument SQLAlchemy and Requests first
SQLAlchemyInstrumentor().instrument()
RequestsInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

# ---------------------------------------------------
# 2. FastAPI App
# ---------------------------------------------------
app = FastAPI(title="BERT Sentiment Analysis API")

# Instrument the app after creation
FastAPIInstrumentor.instrument_app(app)

# ============================================
# MULTI-TENANT MIDDLEWARE
# ============================================

@app.middleware("http")
async def add_organization_context(request: Request, call_next):
    """
    Extract organization from API key and add to request.state
    This middleware runs on EVERY request to ensure org context
    """
    request.state.org_id = None
    request.state.user_id = None
    request.state.org = None
    request.state.user = None

    # Extract API key from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]  # Remove "Bearer " prefix

        # Get db session for auth check
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # Authenticate with API key
            auth_result = await authenticate_with_api_key(api_key, db)
            if auth_result:
                org, user, api_key_obj = auth_result
                request.state.org_id = org.id
                request.state.user_id = user.id
                request.state.org = org
                request.state.user = user

    response = await call_next(request)
    return response

# ---------------------------------------------------
# 2. Load Hugging Face Model
# ---------------------------------------------------
classifier = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

# ---------------------------------------------------
# 3. Logging Setup (for Loki / Promtail)
# ---------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# ---------------------------------------------------
# 3a. Database Initialization
# ---------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    from database import AsyncSessionLocal
    try:
        await init_db()
        logging.info("Database initialized successfully")

        # Create default user if it doesn't exist
        async with AsyncSessionLocal() as session:
            existing_user = await session.execute(
                select(User).where(User.username == "default")
            )
            if not existing_user.scalar_one_or_none():
                default_user = User(
                    username="default",
                    api_key=hash_api_key("default-key-change-me")
                )
                session.add(default_user)
                await session.commit()
                logging.info("Default user created for backward compatibility")

    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    try:
        await close_db()
        logging.info("Database connection closed")
    except Exception as e:
        logging.error(f"Database shutdown error: {str(e)}")


# ---------------------------------------------------
# HTTP Bearer security for API key authentication
# ---------------------------------------------------
security = HTTPBearer()

# ---------------------------------------------------
# 4. Prometheus Metrics
# ---------------------------------------------------
REQUEST_COUNT = Counter(
    "request_count",
    "Total API Requests"
)

ERROR_COUNT = Counter(
    "error_count",
    "Total API Errors"
)

LATENCY = Histogram(
    "latency_seconds",
    "Request Latency"
)

# ---------------------------------------------------
# 5. Middleware (Track metrics automatically)
# ---------------------------------------------------
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
        REQUEST_COUNT.inc()

        if response.status_code >= 400:
            ERROR_COUNT.inc()

        return response

    except Exception as e:
        ERROR_COUNT.inc()
        logging.error(f"Unhandled Error: {str(e)}")
        raise e

    finally:
        LATENCY.observe(time.time() - start_time)

# ---------------------------------------------------
# 5a. Rate Limiting Middleware (SaaS Feature)
# ---------------------------------------------------
@app.middleware("http")
async def rate_limit_check(request: Request, call_next):
    """
    Check rate limits and quotas for organization
    Returns 429 Too Many Requests if limit exceeded
    """
    # Skip rate limiting for public endpoints
    skip_paths = ["/health", "/", "/docs", "/openapi.json", "/metrics"]
    if request.url.path in skip_paths:
        return await call_next(request)

    # Get rate limiter
    rate_limiter = get_rate_limiter()

    # Only rate limit if user is authenticated
    if hasattr(request.state, 'org_id') and request.state.org_id:
        # Get organization tier
        from database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            org_result = await db.execute(
                select(Organization).where(Organization.id == request.state.org_id)
            )
            org = org_result.scalar_one_or_none()

            if org:
                # Check rate limit
                allowed, rate_info = rate_limiter.check_rate_limit(request.state.org_id, org.tier)

                if not allowed:
                    response = JSONResponse(
                        status_code=429,
                        content={
                            "error": "Rate limit exceeded",
                            "limit": rate_info["limit"],
                            "current": rate_info["current"],
                            "remaining": 0,
                            "retry_after": rate_info["retry_after"]
                        }
                    )
                    response.headers["Retry-After"] = str(rate_info["retry_after"])
                    return response

                # Check monthly quota
                allowed, quota_info = rate_limiter.check_monthly_quota(request.state.org_id, org.tier)

                if not allowed:
                    response = JSONResponse(
                        status_code=429,
                        content={
                            "error": "Monthly quota exceeded",
                            "quota_limit": quota_info["quota_limit"],
                            "usage": quota_info["usage"],
                            "remaining": 0,
                            "reset_date": quota_info["reset_date"]
                        }
                    )
                    return response

    response = await call_next(request)

    # Increment quota on successful requests
    if hasattr(request.state, 'org_id') and request.state.org_id and response.status_code < 400:
        rate_limiter.increment_quota(request.state.org_id)

    return response
@app.get("/")
def home():
    return {
        "message": "BERT Sentiment Analysis API Running",
        "model": "distilbert-base-uncased-finetuned-sst-2-english"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "BERT Sentiment Analysis API"
    }

# ---------------------------------------------------
# 7. Metrics Endpoint
# ---------------------------------------------------
@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# ---------------------------------------------------
# 8. Prediction Route (with Database Storage)
# ---------------------------------------------------
@app.get("/predict")
async def predict(text: str, request: Request, db: AsyncSession = Depends(get_db)):
    # Enforce authentication
    if not request.state.org_id or not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        start_inference = time.time()
        result = classifier(text)
        inference_time_ms = (time.time() - start_inference) * 1000

        label = result[0]["label"]
        score = float(result[0]["score"])

        # Store prediction in database with org context
        prediction_record = PredictionRecord(
            organization_id=request.state.org_id,
            user_id=request.state.user_id,
            input_text=text,
            prediction=label,
            confidence=score,
            inference_time_ms=inference_time_ms,
            request_id=uuid.uuid4()
        )
        db.add(prediction_record)
        await db.commit()

        logging.info(
            f"Prediction Success | Org={request.state.org_id} | Input={text} | Output={label} | Score={score} | Time={inference_time_ms:.2f}ms"
        )

        return {
            "input_text": text,
            "prediction": label,
            "confidence": score,
            "inference_time_ms": inference_time_ms
        }

    except Exception as e:
        await db.rollback()
        logging.error(
            f"Prediction Failed | Org={request.state.org_id} | Input={text} | Error={str(e)}"
        )
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------------------
# 9. Get Predictions
# ---------------------------------------------------
@app.get("/predictions")
async def get_predictions(request: Request, limit: int = 10, db: AsyncSession = Depends(get_db)):
    # Enforce authentication
    if not request.state.org_id or not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        query = select(PredictionRecord).where(
            and_(
                PredictionRecord.organization_id == request.state.org_id,
                PredictionRecord.user_id == request.state.user_id
            )
        ).order_by(PredictionRecord.id.desc()).limit(limit)
        result = await db.execute(query)
        predictions = result.scalars().all()

        return {
            "predictions": [
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "input_text": p.input_text,
                    "prediction": p.prediction,
                    "confidence": p.confidence,
                    "inference_time_ms": p.inference_time_ms,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None
                }
                for p in predictions
            ],
            "total": len(predictions)
        }
    except Exception as e:
        logging.error(f"Error fetching predictions for org {request.state.org_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------------------
# 10. Status Endpoint
# ---------------------------------------------------
@app.get("/status")
async def status(request: Request, db: AsyncSession = Depends(get_db)):
    # Enforce authentication
    if not request.state.org_id or not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        # Count org's predictions
        result = await db.execute(
            select(PredictionRecord).where(
                and_(
                    PredictionRecord.organization_id == request.state.org_id,
                    PredictionRecord.user_id == request.state.user_id
                )
            )
        )
        predictions = result.scalars().all()

        return {
            "status": "running",
            "total_predictions": len(predictions),
            "model": "distilbert-base-uncased-finetuned-sst-2-english"
        }
    except Exception as e:
        logging.error(f"Error in status for org {request.state.org_id}: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

# ---------------------------------------------------
# 11. Batch Predict
# ---------------------------------------------------
@app.post("/batch-predict")
async def batch_predict(texts: List[str], request: Request, db: AsyncSession = Depends(get_db)):
    # Enforce authentication
    if not request.state.org_id or not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        results = []

        for text in texts:
            result = classifier(text)
            label = result[0]["label"]
            score = float(result[0]["score"])

            results.append({
                "input_text": text,
                "prediction": label,
                "confidence": score
            })

            # Store prediction with org context
            prediction_record = PredictionRecord(
                organization_id=request.state.org_id,
                user_id=request.state.user_id,
                input_text=text,
                prediction=label,
                confidence=score,
                inference_time_ms=0,
                request_id=uuid.uuid4()
            )
            db.add(prediction_record)

        await db.commit()
        logging.info(f"Batch prediction completed for org {request.state.org_id}: {len(texts)} items")

        return {"results": results, "count": len(results)}

    except Exception as e:
        await db.rollback()
        logging.error(f"Batch prediction failed for org {request.state.org_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------------------
# 12. Export Predictions
# ---------------------------------------------------
@app.get("/predictions/export")
async def export_predictions(request: Request, format: str = "json", db: AsyncSession = Depends(get_db)):
    # Enforce authentication
    if not request.state.org_id or not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        result = await db.execute(
            select(PredictionRecord).where(
                and_(
                    PredictionRecord.organization_id == request.state.org_id,
                    PredictionRecord.user_id == request.state.user_id
                )
            )
        )
        predictions = result.scalars().all()

        data = [
            {
                "id": p.id,
                "user_id": p.user_id,
                "input_text": p.input_text,
                "prediction": p.prediction,
                "confidence": p.confidence,
                "inference_time_ms": p.inference_time_ms,
                "timestamp": p.timestamp.isoformat() if p.timestamp else None
            }
            for p in predictions
        ]

        if format == "csv":
            output = StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=predictions.csv"}
            )
        else:
            return Response(
                content=json.dumps(data, indent=2, default=str),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=predictions.json"}
            )

    except Exception as e:
        logging.error(f"Export failed for org {request.state.org_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------------------
# 13. Auth Routes
# ---------------------------------------------------
@app.post("/auth/register")
async def register(username: str, password: str, db: AsyncSession = Depends(get_db)):
    try:
        existing_user = await db.execute(
            select(User).where(User.username == username)
        )
        if existing_user.scalar_one_or_none():
            return JSONResponse(
                status_code=400,
                content={"error": "User already exists"}
            )

        api_key = generate_api_key()
        hashed_key = hash_api_key(api_key)

        # Create user with globally unique email
        new_user = User(
            username=username,
            email=f"{username}@{uuid.uuid4().hex[:8]}.local",
            api_key=hashed_key
        )
        db.add(new_user)
        await db.flush()  # Flush to get the user ID

        # Create organization for this user
        new_org = Organization(
            name=f"{username}'s Organization",
            slug=f"{username}-{uuid.uuid4().hex[:8]}",
            tier="free",
            is_active=True
        )
        db.add(new_org)
        await db.flush()  # Flush to get the org ID

        # Create org membership
        org_member = OrganizationMember(
            organization_id=new_org.id,
            user_id=new_user.id,
            role="admin"
        )
        db.add(org_member)

        # Create API key record
        api_key_record = APIKey(
            organization_id=new_org.id,
            name=f"Default key for {username}",
            key_hash=hashed_key,
            is_active=True
        )
        db.add(api_key_record)

        # Create free subscription
        free_tier_result = await db.execute(
            select(SubscriptionTier).where(SubscriptionTier.name == "free")
        )
        free_tier = free_tier_result.scalar_one_or_none()

        if free_tier:
            subscription = Subscription(
                organization_id=new_org.id,
                tier_id=free_tier.id,
                status="active"
            )
            db.add(subscription)

        await db.commit()

        logging.info(f"User registered: {username} with org: {new_org.slug}")

        return {
            "username": username,
            "api_key": api_key,
            "organization": new_org.slug
        }

    except Exception as e:
        await db.rollback()
        logging.error(f"Registration failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------------------
# 14. Sentiment Distribution (for Grafana)
# ---------------------------------------------------
@app.get("/sentiments")
async def get_sentiments(request: Request, db: AsyncSession = Depends(get_db)):
    # Enforce authentication
    if not request.state.org_id or not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        result = await db.execute(
            select(PredictionRecord).where(
                and_(
                    PredictionRecord.organization_id == request.state.org_id,
                    PredictionRecord.user_id == request.state.user_id
                )
            )
        )
        predictions = result.scalars().all()

        sentiments = {}
        for p in predictions:
            sentiments[p.prediction] = sentiments.get(p.prediction, 0) + 1

        return {
            "sentiments": sentiments
        }
    except Exception as e:
        logging.error(f"Error in sentiments for org {request.state.org_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------------------
# 15. Metrics Summary
# ---------------------------------------------------
@app.get("/model-metrics")
async def model_metrics(request: Request, db: AsyncSession = Depends(get_db)):
    # Enforce authentication
    if not request.state.org_id or not request.state.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    try:
        result = await db.execute(
            select(PredictionRecord).where(
                and_(
                    PredictionRecord.organization_id == request.state.org_id,
                    PredictionRecord.user_id == request.state.user_id
                )
            )
        )
        predictions = result.scalars().all()

        if not predictions:
            return {
                "total": 0,
                "avg_confidence": 0,
                "avg_inference_time_ms": 0
            }

        avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
        avg_inference = sum(p.inference_time_ms for p in predictions) / len(predictions)

        return {
            "total": len(predictions),
            "avg_confidence": round(avg_confidence, 4),
            "avg_inference_time_ms": round(avg_inference, 2)
        }
    except Exception as e:
        logging.error(f"Error in model metrics for org {request.state.org_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ---------------------------------------------------
# 16. BILLING ENDPOINTS (SaaS Features)
# ---------------------------------------------------

@app.get("/billing/subscription")
async def get_subscription(request: Request, db: AsyncSession = Depends(get_db)):
    """Get organization's current subscription details"""
    if not request.state.org_id:
        raise HTTPException(status_code=401, detail="API key required")

    try:
        # Get subscription
        sub_result = await db.execute(
            select(Subscription).where(Subscription.organization_id == request.state.org_id)
        )
        subscription = sub_result.scalar_one_or_none()

        if not subscription:
            return JSONResponse(status_code=404, content={"error": "No subscription found"})

        # Get tier details
        tier_result = await db.execute(
            select(SubscriptionTier).where(SubscriptionTier.id == subscription.tier_id)
        )
        tier = tier_result.scalar_one_or_none()

        # Get usage
        rate_limiter = get_rate_limiter()
        allowed, quota_info = rate_limiter.check_monthly_quota(request.state.org_id, tier.name if tier else "free")

        return {
            "subscription_id": subscription.id,
            "tier": tier.name if tier else "unknown",
            "status": subscription.status,
            "price_usd": tier.price_usd if tier else 0,
            "requests_per_month": tier.requests_per_month if tier else 0,
            "batch_limit": tier.batch_limit if tier else 100,
            "rate_limit_rpm": tier.rate_limit_rpm if tier else 10,
            "usage": quota_info.get("usage", 0),
            "remaining": quota_info.get("remaining", 0),
            "reset_date": quota_info.get("reset_date"),
            "billing_cycle_start": subscription.billing_cycle_start.isoformat() if subscription.billing_cycle_start else None,
            "billing_cycle_end": subscription.billing_cycle_end.isoformat() if subscription.billing_cycle_end else None
        }
    except Exception as e:
        logging.error(f"Error fetching subscription for org {request.state.org_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/billing/upgrade")
async def upgrade_subscription(tier_name: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Upgrade organization to a higher tier"""
    if not request.state.org_id:
        raise HTTPException(status_code=401, detail="API key required")

    try:
        # Validate tier
        tier_result = await db.execute(
            select(SubscriptionTier).where(SubscriptionTier.name == tier_name)
        )
        tier = tier_result.scalar_one_or_none()

        if not tier:
            return JSONResponse(status_code=400, content={"error": f"Tier not found: {tier_name}"})

        # Update subscription
        stripe = get_stripe_integration()
        success = await stripe.update_subscription(db, request.state.org_id, tier_name)

        if not success:
            return JSONResponse(status_code=500, content={"error": "Failed to upgrade subscription"})

        # Reset monthly quota for new tier
        rate_limiter = get_rate_limiter()
        rate_limiter.reset_quota(request.state.org_id)

        logging.info(f"Organization {request.state.org_id} upgraded to {tier_name}")

        return {
            "status": "success",
            "tier": tier_name,
            "new_requests_per_month": tier.requests_per_month,
            "message": f"Successfully upgraded to {tier_name} tier"
        }
    except Exception as e:
        logging.error(f"Error upgrading subscription for org {request.state.org_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/billing/usage")
async def get_usage(request: Request, db: AsyncSession = Depends(get_db)):
    """Get detailed usage statistics for organization"""
    if not request.state.org_id:
        raise HTTPException(status_code=401, detail="API key required")

    try:
        # Get organization and subscription
        org_result = await db.execute(
            select(Organization).where(Organization.id == request.state.org_id)
        )
        org = org_result.scalar_one_or_none()

        sub_result = await db.execute(
            select(Subscription).where(Subscription.organization_id == request.state.org_id)
        )
        subscription = sub_result.scalar_one_or_none()

        if not subscription:
            return JSONResponse(status_code=404, content={"error": "No subscription found"})

        # Get tier
        tier_result = await db.execute(
            select(SubscriptionTier).where(SubscriptionTier.id == subscription.tier_id)
        )
        tier = tier_result.scalar_one_or_none()

        # Get usage info
        rate_limiter = get_rate_limiter()
        allowed, quota_info = rate_limiter.check_monthly_quota(request.state.org_id, tier.name if tier else "free")

        # Get prediction counts
        pred_result = await db.execute(
            select(PredictionRecord).where(PredictionRecord.organization_id == request.state.org_id)
        )
        predictions = pred_result.scalars().all()

        return {
            "organization": org.name if org else "Unknown",
            "tier": tier.name if tier else "free",
            "usage_this_month": quota_info.get("usage", 0),
            "quota_limit": quota_info.get("quota_limit", 0),
            "remaining": quota_info.get("remaining", 0),
            "percentage_used": quota_info.get("percentage_used", 0),
            "reset_date": quota_info.get("reset_date"),
            "total_predictions_all_time": len(predictions),
            "average_confidence": round(sum(p.confidence for p in predictions) / len(predictions), 4) if predictions else 0,
            "average_inference_time_ms": round(sum(p.inference_time_ms for p in predictions) / len(predictions), 2) if predictions else 0
        }
    except Exception as e:
        logging.error(f"Error getting usage for org {request.state.org_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/billing/webhook")
async def handle_stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events (signature validation required in production)"""
    try:
        body = await request.body()
        event = json.loads(body)

        stripe = get_stripe_integration()
        success = stripe.handle_webhook(event)

        return {"status": "received", "processed": success}

    except Exception as e:
        logging.error(f"Webhook handling failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ---------------------------------------------------
# 17. FRONTEND SERVING
# ---------------------------------------------------
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("billing/") or full_path.startswith("auth/"):
            return JSONResponse(status_code=404, content={"error": "API route not found"})
            
        index_path = "frontend/dist/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse(status_code=404, content={"error": "Frontend not built"})
