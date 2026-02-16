# API Examples - Transaction Risk Scoring

Complete examples of API requests and responses for testing.

---

## 1. Health Check

### Request
```bash
curl http://localhost:8000/health
```

### Response
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "v1.0.0",
  "environment": "production",
  "uptime_seconds": 125.34
}
```

**HTTP Status**: `200 OK`

---

## 2. Readiness Check

### Request
```bash
curl http://localhost:8000/ready
```

### Response (Ready)
```json
{
  "status": "ready",
  "model_loaded": true,
  "model_version": "v1.0.0",
  "environment": "production",
  "uptime_seconds": 130.45
}
```

**HTTP Status**: `200 OK`

### Response (Not Ready)
```json
{
  "detail": "Model not loaded"
}
```

**HTTP Status**: `503 Service Unavailable`

---

## 3. LOW Risk Transaction (Legitimate)

### Request
```bash
curl -X POST http://localhost:8000/score ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo-key-123" ^
  -d "{\"transaction_id\":\"txn_legit_001\",\"features\":{\"transaction_amount_usd\":500.0,\"sender_age_days\":365,\"transactions_last_24h\":2,\"avg_transaction_amount\":450.0,\"sender_country_risk_score\":0.1,\"is_new_recipient\":false,\"hour_of_day\":14}}"
```

### Response
```json
{
  "transaction_id": "txn_legit_001",
  "risk_score": 0.0234,
  "risk_level": "LOW",
  "recommendation": "APPROVE",
  "model_version": "v1.0.0",
  "timestamp": "2026-02-16T00:30:00.123456",
  "correlation_id": "abc123-def456-ghi789",
  "features_hash": "sha256:a1b2c3d4e5f6...",
  "processing_time_ms": 12.34
}
```

**HTTP Status**: `200 OK`

**Interpretation**:
- Risk Score: 2.34% (very low fraud probability)
- **Recommendation**: APPROVE transaction automatically
- Processing time: 12ms (well within 100ms SLA)
- This is a safe transaction with established account

**Why LOW Risk?**
- ✅ Regular amount ($500)
- ✅ Old account (365 days)
- ✅ Normal transaction frequency (2/day)
- ✅ Known recipient
- ✅ Normal business hours (2 PM)
- ✅ Low-risk country (0.1/1.0)

---

## 4. MEDIUM Risk Transaction (Requires Review)

### Request
```bash
curl -X POST http://localhost:8000/score ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo-key-123" ^
  -d "{\"transaction_id\":\"txn_medium_001\",\"features\":{\"transaction_amount_usd\":8000.0,\"sender_age_days\":45,\"transactions_last_24h\":5,\"avg_transaction_amount\":1200.0,\"sender_country_risk_score\":0.5,\"is_new_recipient\":true,\"hour_of_day\":22}}"
```

### Response
```json
{
  "transaction_id": "txn_medium_001",
  "risk_score": 0.4567,
  "risk_level": "MEDIUM",
  "recommendation": "REVIEW",
  "model_version": "v1.0.0",
  "timestamp": "2026-02-16T00:35:00.456789",
  "correlation_id": "xyz789-uvw456-rst123",
  "features_hash": "sha256:d4e5f6g7h8i9...",
  "processing_time_ms": 15.67
}
```

**HTTP Status**: `200 OK`

**Interpretation**:
- Risk Score: 45.67% (moderate fraud probability)
- **Recommendation**: Flag for manual review
- Requires human verification before approval
- Not quite high enough to auto-reject

**Why MEDIUM Risk?**
- ⚠️ Large amount ($8,000)
- ⚠️ Relatively new account (45 days)
- ⚠️ Higher than usual frequency (5 transactions)
- ⚠️ New recipient (first time)
- ⚠️ Late hour (10 PM)
- ⚠️ Medium-risk country (0.5/1.0)

---

## 5. HIGH Risk Transaction (Suspicious)

### Request
```bash
curl -X POST http://localhost:8000/score ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo-key-123" ^
  -d "{\"transaction_id\":\"txn_high_001\",\"features\":{\"transaction_amount_usd\":25000.0,\"sender_age_days\":10,\"transactions_last_24h\":10,\"avg_transaction_amount\":800.0,\"sender_country_risk_score\":0.75,\"is_new_recipient\":true,\"hour_of_day\":1}}"
```

### Response
```json
{
  "transaction_id": "txn_high_001",
  "risk_score": 0.7234,
  "risk_level": "HIGH",
  "recommendation": "REVIEW",
  "model_version": "v1.0.0",
  "timestamp": "2026-02-16T01:00:00.789012",
  "correlation_id": "pqr456-mno123-jkl789",
  "features_hash": "sha256:g7h8i9j0k1l2...",
  "processing_time_ms": 18.92
}
```

**HTTP Status**: `200 OK`

**Interpretation**:
- Risk Score: 72.34% (high fraud probability)
- **Recommendation**: Immediate manual review required
- Very suspicious pattern - likely fraud
- Should be escalated to fraud team

**Why HIGH Risk?**
- 🚨 Very large amount ($25,000)
- 🚨 Very new account (10 days)
- 🚨 Extremely high frequency (10 in 24h)
- 🚨 Amount 30x larger than average
- 🚨 New recipient
- 🚨 Suspicious hour (1 AM)
- 🚨 High-risk country (0.75/1.0)

---

## 6. CRITICAL Risk Transaction (Likely Fraud)

### Request
```bash
curl -X POST http://localhost:8000/score ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo-key-123" ^
  -d "{\"transaction_id\":\"txn_fraud_001\",\"features\":{\"transaction_amount_usd\":50000.0,\"sender_age_days\":3,\"transactions_last_24h\":15,\"avg_transaction_amount\":500.0,\"sender_country_risk_score\":0.9,\"is_new_recipient\":true,\"hour_of_day\":3}}"
```

### Response
```json
{
  "transaction_id": "txn_fraud_001",
  "risk_score": 1.0,
  "risk_level": "CRITICAL",
  "recommendation": "REJECT",
  "model_version": "v1.0.0",
  "timestamp": "2026-02-16T03:00:00.123456",
  "correlation_id": "stu901-vwx234-yza567",
  "features_hash": "sha256:j0k1l2m3n4o5...",
  "processing_time_ms": 14.23
}
```

**HTTP Status**: `200 OK`

**Interpretation**:
- Risk Score: 100% (maximum fraud probability)
- **Recommendation**: REJECT transaction immediately
- Classic fraud pattern - do not process
- Block and flag account for investigation

**Why CRITICAL Risk?**
- 🔴 Massive amount ($50,000)
- 🔴 Brand new account (3 days old!)
- 🔴 Extreme velocity (15 transactions in 24h)
- 🔴 Amount 100x larger than average
- 🔴 Very high-risk country (0.9/1.0)
- 🔴 New recipient
- 🔴 Middle of night (3 AM)

**This is a CLASSIC fraud pattern!**

---

## 7. Error - Amount Exceeds Limit

### Request
```bash
curl -X POST http://localhost:8000/score ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo-key-123" ^
  -d "{\"transaction_id\":\"txn_invalid_001\",\"features\":{\"transaction_amount_usd\":2000000.0,\"sender_age_days\":180,\"transactions_last_24h\":3,\"avg_transaction_amount\":900.0,\"sender_country_risk_score\":0.2,\"is_new_recipient\":false,\"hour_of_day\":14}}"
```

### Response
```json
{
  "detail": "Invalid input: Transaction amount exceeds maximum limit"
}
```

**HTTP Status**: `400 Bad Request`

**Reason**: Transaction amount ($2M) exceeds the $1M limit

---

## 8. Error - Missing Required Fields

### Request
```bash
curl -X POST http://localhost:8000/score ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo-key-123" ^
  -d "{\"transaction_id\":\"txn_invalid_002\",\"features\":{\"transaction_amount_usd\":1000.0}}"
```

### Response
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "features", "sender_age_days"],
      "msg": "Field required"
    },
    {
      "type": "missing",
      "loc": ["body", "features", "transactions_last_24h"],
      "msg": "Field required"
    }
  ]
}
```

**HTTP Status**: `422 Unprocessable Entity`

**Reason**: Missing required feature fields

---

## 9. Prometheus Metrics

### Request
```bash
curl http://localhost:8000/metrics
```

### Response (excerpt)
```
# HELP transaction_risk_scores_total Total transaction risk assessments
# TYPE transaction_risk_scores_total counter
transaction_risk_scores_total{model_version="v1.0.0",risk_level="LOW",status="success"} 1234.0
transaction_risk_scores_total{model_version="v1.0.0",risk_level="MEDIUM",status="success"} 234.0
transaction_risk_scores_total{model_version="v1.0.0",risk_level="HIGH",status="success"} 56.0
transaction_risk_scores_total{model_version="v1.0.0",risk_level="CRITICAL",status="success"} 12.0

# HELP transaction_risk_latency_seconds Transaction risk scoring latency
# TYPE transaction_risk_latency_seconds histogram
transaction_risk_latency_seconds_bucket{le="0.01",model_version="v1.0.0"} 1100.0
transaction_risk_latency_seconds_bucket{le="0.025",model_version="v1.0.0"} 1450.0
transaction_risk_latency_seconds_bucket{le="0.05",model_version="v1.0.0"} 1520.0
transaction_risk_latency_seconds_bucket{le="0.1",model_version="v1.0.0"} 1536.0
transaction_risk_latency_seconds_sum{model_version="v1.0.0"} 23.456
transaction_risk_latency_seconds_count{model_version="v1.0.0"} 1536.0

# HELP high_risk_transactions_last_hour Count of high-risk transactions
# TYPE high_risk_transactions_last_hour gauge
high_risk_transactions_last_hour 68.0
```

**Analysis**:
- Total transactions scored: 1,536
- Low risk: 80.3% (1,234)
- Medium risk: 15.2% (234)
- High risk: 3.6% (56)
- Critical risk: 0.8% (12)
- Average latency: ~15ms (23.456 / 1536)
- P95 latency: <50ms

---

## 10. Audit Logs

### Request
```bash
curl http://localhost:8000/audit-logs?limit=3 ^
  -H "X-API-Key: admin-key-456"
```

### Response
```json
{
  "total": 1536,
  "logs": [
    {
      "timestamp": "2026-02-16T03:00:00.123456",
      "transaction_id": "txn_fraud_001",
      "customer_id": "cust_hash_xyz789",
      "risk_score": 1.0,
      "risk_level": "CRITICAL",
      "recommendation": "REJECT",
      "model_version": "v1.0.0",
      "environment": "production",
      "correlation_id": "stu901-vwx234-yza567"
    },
    {
      "timestamp": "2026-02-16T01:00:00.789012",
      "transaction_id": "txn_high_001",
      "customer_id": "cust_hash_pqr456",
      "risk_score": 0.7234,
      "risk_level": "HIGH",
      "recommendation": "REVIEW",
      "model_version": "v1.0.0",
      "environment": "production",
      "correlation_id": "pqr456-mno123-jkl789"
    },
    {
      "timestamp": "2026-02-16T00:35:00.456789",
      "transaction_id": "txn_medium_001",
      "customer_id": "cust_hash_xyz789",
      "risk_score": 0.4567,
      "risk_level": "MEDIUM",
      "recommendation": "REVIEW",
      "model_version": "v1.0.0",
      "environment": "production",
      "correlation_id": "xyz789-uvw456-rst123"
    }
  ]
}
```

**Use Cases**:
- Regulatory compliance reporting
- Incident investigation
- Performance analysis
- Model drift detection

---

## 11. Risk Level Summary

| Risk Level | Risk Score Range | Recommendation | Action |
|------------|------------------|----------------|--------|
| **LOW** | 0.0 - 0.3 | APPROVE | Auto-approve transaction |
| **MEDIUM** | 0.3 - 0.6 | REVIEW | Flag for manual review |
| **HIGH** | 0.6 - 0.8 | REVIEW | Immediate manual review |
| **CRITICAL** | 0.8 - 1.0 | REJECT | Block transaction, investigate |

---

## 12. Testing with Python
```python
import requests

BASE_URL = "http://localhost:8000"

# Test health check
response = requests.get(f"{BASE_URL}/health")
print(f"Health: {response.json()}")

# Test transaction scoring
transaction = {
    "transaction_id": "txn_python_001",
    "features": {
        "transaction_amount_usd": 1000.0,
        "sender_age_days": 180,
        "transactions_last_24h": 3,
        "avg_transaction_amount": 900.0,
        "sender_country_risk_score": 0.2,
        "is_new_recipient": False,
        "hour_of_day": 14
    }
}

response = requests.post(
    f"{BASE_URL}/score",
    json=transaction,
    headers={"X-API-Key": "demo-key-123"}
)

result = response.json()
print(f"Risk Score: {result['risk_score']}")
print(f"Risk Level: {result['risk_level']}")
print(f"Recommendation: {result['recommendation']}")
print(f"Latency: {result['processing_time_ms']}ms")
```

---

## 13. Load Testing

### Using `hey` (HTTP load generator)
```bash
# Install hey
go install github.com/rakyll/hey@latest

# Run load test: 1000 requests, 10 concurrent
hey -n 1000 -c 10 ^
  -m POST ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo-key-123" ^
  -d "{\"transaction_id\":\"txn_load_test\",\"features\":{\"transaction_amount_usd\":1000.0,\"sender_age_days\":180,\"transactions_last_24h\":3,\"avg_transaction_amount\":900.0,\"sender_country_risk_score\":0.2,\"is_new_recipient\":false,\"hour_of_day\":14}}" ^
  http://localhost:8000/score
```

**Expected Results**:
```
Summary:
  Total:        2.1234 secs
  Requests/sec: 471.23
  
  Average:      0.0212 secs
  Fastest:      0.0089 secs
  Slowest:      0.0567 secs

Status code distribution:
  [200] 1000 responses

Latency distribution:
  10% in 0.0123 secs
  25% in 0.0156 secs
  50% in 0.0212 secs
  75% in 0.0289 secs
  90% in 0.0367 secs
  95% in 0.0423 secs
  99% in 0.0512 secs
```

**Analysis**:
- ✅ Throughput: 471 RPS (excellent)
- ✅ P95 latency: 42ms (well below 100ms SLA)
- ✅ Zero errors (100% success rate)

---

## 14. Integration with Dnar Platform

### Crypto-to-Fiat Conversion Flow
```python
# Example: Dnar backend integration
def process_crypto_conversion(
    customer_id: str,
    amount_usd: float,
    from_crypto: str,  # "USDC" or "USDT"
    to_fiat: str       # "NGN", "GHS", "KES"
):
    # Step 1: Extract transaction features
    features = {
        "transaction_amount_usd": amount_usd,
        "sender_age_days": get_account_age(customer_id),
        "transactions_last_24h": count_recent_transactions(customer_id),
        "avg_transaction_amount": get_avg_amount(customer_id),
        "sender_country_risk_score": get_country_risk(customer_id),
        "is_new_recipient": check_if_new_recipient(customer_id),
        "hour_of_day": datetime.now().hour
    }
    
    # Step 2: Score transaction risk
    risk_result = requests.post(
        "http://ml-service/score",
        json={
            "transaction_id": f"conv_{uuid.uuid4()}",
            "features": features
        },
        headers={"X-API-Key": os.getenv("ML_API_KEY")}
    ).json()
    
    # Step 3: Decision logic
    if risk_result['recommendation'] == 'APPROVE':
        # Proceed with conversion
        return execute_conversion(amount_usd, from_crypto, to_fiat)
    
    elif risk_result['recommendation'] == 'REVIEW':
        # Require additional verification
        return {
            "status": "pending_review",
            "message": "Additional verification required",
            "risk_score": risk_result['risk_score']
        }
    
    else:  # REJECT
        # Block transaction
        return {
            "status": "rejected",
            "message": "Transaction flagged as high-risk",
            "risk_score": risk_result['risk_score']
        }
```

---

## 15. Monitoring Queries (Prometheus/Grafana)
```promql
# Average latency (P95)
histogram_quantile(0.95, 
  sum(rate(transaction_risk_latency_seconds_bucket[5m])) by (le)
)

# Requests per second
rate(transaction_risk_scores_total[5m])

# Error rate
rate(transaction_risk_scores_total{status="error"}[5m]) 
/ 
rate(transaction_risk_scores_total[5m])

# High-risk transaction percentage
(
  sum(rate(transaction_risk_scores_total{risk_level="HIGH"}[1h])) + 
  sum(rate(transaction_risk_scores_total{risk_level="CRITICAL"}[1h]))
) / sum(rate(transaction_risk_scores_total[1h]))

# Model drift score (alert if >0.25)
model_drift_psi_score
```

---

