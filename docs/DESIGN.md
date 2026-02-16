# ML Inference System - Design Document
## Transaction Risk Scoring for Crypto-Fiat Conversions

**Author**: TOTAN [Your Last Name]  
**Company**: Dnar  
**Date**: February 16, 2026  
**System**: Real-time Fraud Detection & AML Compliance Service

---

## 1. Architecture Overview

### Business Context

Dnar enables banks and financial institutions to offer crypto-to-fiat conversion services. This ML system provides **real-time transaction risk scoring** to comply with AML/KYC regulations and prevent fraud in institutional crypto transactions.

**Key Requirements**:
- **Sub-100ms latency** (real-time transaction approval)
- **99.9% uptime** (financial services SLA)
- **Regulatory compliance** (AML/KYC audit trails)
- **Security-first** (PCI-DSS, SOC 2)
- **Scalable** (handle transaction volume spikes)

### System Architecture
```
                    Internet
                       │
        ┌──────────────▼─────────────────┐
        │   Dnar API Gateway             │
        │  (Auth, Rate Limit, TLS)       │
        └──────────────┬─────────────────┘
                       │
        ┌──────────────▼─────────────────┐
        │   Kubernetes Service           │
        │   (Load Balancer)              │
        └──────────────┬─────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
┌──────▼─────┐  ┌─────▼──────┐  ┌────▼──────┐
│  Pod 1     │  │  Pod 2     │  │  Pod 3    │
│ FastAPI    │  │ FastAPI    │  │ FastAPI   │
│ + Model    │  │ + Model    │  │ + Model   │
└────────────┘  └────────────┘  └───────────┘
       │               │               │
       └───────────────┼───────────────┘
                       │
        ┌──────────────▼─────────────────┐
        │   Prometheus Metrics           │
        │   + Audit Log Stream           │
        └────────────────────────────────┘
```

**Data Flow**:
1. Transaction arrives at API gateway (authenticated)
2. Routed to healthy ML pod via load balancer
3. Features extracted and risk scored (<100ms)
4. Audit log created (compliance requirement)
5. Decision returned (APPROVE/REVIEW/REJECT)

---

## 2. Key Engineering Decisions

### Decision 1: Random Forest over Deep Learning
**Choice**: Scikit-learn Random Forest  
**Rationale**:
- **Low latency**: <5ms inference vs 50-100ms for neural nets
- **Explainability**: Feature importance for regulatory audits
- **Proven reliability**: Less prone to unexpected failures
- **Smaller model size**: ~500KB vs 100MB+ for DL models

**Trade-off**: Less accurate on complex patterns, but acceptable for v1.0 (ROC-AUC: 0.95+). Future: Gradient boosting if needed.

### Decision 2: Stateless Architecture
**Choice**: No session state, caching, or local storage  
**Rationale**:
- **Horizontal scaling**: Add pods without state synchronization
- **High availability**: Pods are fungible, simplifies disaster recovery
- **Compliance**: No PII stored locally, reduces data breach risk

**Trade-off**: Cannot cache historical patterns per user. Acceptable - feature engineering happens upstream in Dnar's data pipeline.

### Decision 3: Synchronous API over Batch
**Choice**: REST API (not async batch inference)  
**Rationale**:
- **Business requirement**: Real-time transaction approval (<100ms)
- **User experience**: Customers expect instant conversion quotes
- **Regulatory**: Transactions must be screened before execution

**Not Built**: Batch inference, message queues. For this use case, synchronous is correct.

### Decision 4: CPU-First Deployment
**Choice**: CPU pods with option to add GPU  
**Rationale**:
- **Cost efficiency**: Random Forest doesn't need GPU
- **Lower latency**: No GPU memory transfer overhead
- **Simpler ops**: Easier autoscaling, no GPU node management

**GPU Support**: Documented in k8s/README.md for future LLM-based fraud detection.

### Decision 5: Kubernetes over Serverless
**Choice**: Kubernetes Deployment (not Lambda/Cloud Run)  
**Rationale**:
- **Predictable latency**: Cold starts unacceptable for real-time transactions
- **Resource guarantees**: Need guaranteed CPU for SLA compliance
- **Cost at scale**: Cheaper than serverless at Dnar's transaction volume

**What I Intentionally Did NOT Build**:
- ❌ **Training pipeline**: Out of scope; focused on inference  
- ❌ **Feature store**: Assume Dnar has upstream data pipeline  
- ❌ **Model registry**: MLflow integration shown in docs, not implemented  
- ❌ **A/B testing**: Shadow mode pattern documented for future  

---

## 3. Production Considerations

### 3.1 Monitor Service Health

**Metrics** (via Prometheus):
```promql
# Technical metrics
transaction_risk_scores_total{risk_level, status}
transaction_risk_latency_seconds{model_version}
kube_pod_status_ready
kube_hpa_status_current_replicas

# Business metrics
high_risk_transactions_last_hour
fraud_prevention_rate
```

**Alerting Rules**:
```yaml
- alert: MLServiceDown
  expr: up{job="transaction-risk-scoring"} == 0
  for: 1m
  severity: critical

- alert: HighLatency
  expr: histogram_quantile(0.95, transaction_risk_latency_seconds) > 0.1
  for: 5m
  severity: critical
```

### 3.2 Monitor Model Performance & Detect Drift

**Three-Tier Monitoring**:

1. **Data Drift** (Feature Distribution)
   - Calculate PSI (Population Stability Index) per feature
   - Alert if PSI > 0.25 (significant drift)

2. **Prediction Drift** (Output Distribution)
   - Track % of HIGH/CRITICAL risk scores
   - Alert if deviation from baseline >20%

3. **Performance Drift** (Accuracy)
   - Weekly validation with labeled data
   - Calculate ROC-AUC, precision, recall
   - Alert if ROC-AUC < 0.90 (retrain needed)

**Automated Response**:
- Trigger: Model drift detected
- Action 1: Alert ML team via Slack/PagerDuty
- Action 2: Auto-trigger retraining pipeline
- Action 3: Deploy shadow model for A/B comparison
- Action 4: Auto-promote if metrics improve

### 3.3 Roll Back a Bad Model

**Scenario**: Deploy v2.0, but false positive rate spikes

**Rollback Strategy 1 - Kubernetes Native** (fastest):
```bash
# Immediate rollback (< 1 minute)
kubectl rollout undo deployment/transaction-risk-scoring
```

**Rollback Strategy 2 - ConfigMap** (controlled):
```bash
# Change model version in ConfigMap
kubectl patch configmap ml-config -p '{"data":{"model_version":"v1.0.0"}}'
kubectl rollout restart deployment/transaction-risk-scoring
```

**Rollback Strategy 3 - Blue-Green** (zero-risk):
- Keep v1 running, deploy v2 separately
- Route 10% traffic to v2 via Istio
- Monitor for 1 hour
- If metrics degrade: instant traffic shift back to v1

**Rollback Decision Matrix**:
| Severity | Time | Method |
|----------|------|--------|
| P0 (service down) | <1 min | kubectl rollout undo |
| P1 (high error rate) | <5 min | ConfigMap + restart |
| P2 (accuracy drop) | <30 min | Blue-green traffic shift |

### 3.4 Manage Secrets Securely

**Fintech Compliance Requirements**:
- **Encryption**: All secrets encrypted at rest (KMS)
- **Access control**: RBAC + audit logging
- **Rotation**: Quarterly rotation policy
- **No hardcoding**: Never in code/configs/Git

**Implementation - External Secrets Operator**:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ml-secrets
spec:
  secretStoreRef:
    name: aws-secrets-manager
  target:
    name: ml-secrets
  data:
  - secretKey: api-key
    remoteRef:
      key: dnar/ml-inference/api-key
```

**Best Practices**:
- ✅ Use Workload Identity (GCP) or IRSA (AWS)
- ✅ Secrets never logged or exposed in metrics
- ✅ Separate secrets per environment
- ✅ Automated secret rotation
- ✅ Audit all secret access

---

## 4. Scaling the System

### 4.1 Multiple Models

**Requirement**: Fraud detection, AML scoring, customer risk profiling

**Approach - Model Router Pattern**:
```
API Gateway → /score/fraud → Fraud Detection Pod
            → /score/aml → AML Compliance Pod
            → /score/customer → Customer Risk Pod
```

**Benefits**: Isolation, independent scaling, separate SLAs

### 4.2 Multiple Teams

**Requirement**: 5 ML teams deploying models independently

**Approach - Self-Service Platform**:
- **Namespace per team**: `team-fraud`, `team-risk`
- **Helm chart template**: `helm install my-model dnar-ml-chart`
- **Resource quotas**: Prevent one team from monopolizing cluster
- **Centralized monitoring**: All metrics flow to shared Prometheus

**Governance**:
- Teams own their models, deployments, monitoring
- Platform team maintains Helm chart, base images
- Automated compliance checks

### 4.3 Higher Traffic

**Current**: 1K transactions/sec  
**Target**: 50K transactions/sec

**Scaling Path**:

**Phase 1 (1K → 10K TPS)**: Horizontal scaling
- HPA: 3 → 30 pods
- Cost: ~$2K/month → ~$10K/month

**Phase 2 (10K → 30K TPS)**: Multi-region
- Deploy to 3 regions (us-east, us-west, eu-west)
- Global load balancer
- Cost: ~$10K/month → ~$25K/month

**Phase 3 (30K → 50K TPS)**: Caching + Optimization
- Redis cache for duplicate requests (5-min TTL)
- Model quantization (FP32 → FP16, 2x faster)
- Cost: ~$25K/month → $35K/month

---
