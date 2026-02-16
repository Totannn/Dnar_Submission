# Kubernetes Deployment Guide

## Overview

Production-ready Kubernetes deployment for transaction risk scoring service in Dnar's crypto-to-fiat platform.

**Design Principles**:
- ✅ **High Availability**: 99.9% uptime SLA for banking operations
- ✅ **Security-First**: Banking-grade security (PCI-DSS, SOC 2)
- ✅ **Low Latency**: <100ms P95 for real-time transaction approval
- ✅ **Scalability**: Auto-scale from 3 to 20 pods based on load
- ✅ **Compliance**: Audit trails, encryption, network isolation

---

## Architecture Components

### 1. Deployment (`deployment.yaml`)

**Key Features**:
- **3 replicas minimum** (high availability)
- **Zero-downtime updates** (maxUnavailable: 0)
- **Pod anti-affinity** (spread across nodes)
- **Resource requests & limits** (guaranteed resources)
- **Health probes** (liveness, readiness, startup)
- **Security context** (non-root, read-only filesystem)
- **InitContainer** (model loading from cloud storage)

**Resource Allocation**:
```yaml
resources:
  requests:
    memory: 512Mi    # Guaranteed minimum
    cpu: 500m        # 0.5 CPU cores
  limits:
    memory: 1Gi      # Maximum allowed
    cpu: 2000m       # 2 CPU cores (burst capacity)
```

**Rationale**:
- **High CPU request**: Ensures low latency for real-time scoring
- **4:1 limit ratio**: Allows burst capacity during traffic spikes
- **Memory**: Adequate for model (~300KB) + FastAPI + request buffering

### 2. Service (`service.yaml`)

**Type**: ClusterIP (internal-only)

**Why Not LoadBalancer**:
- Dnar has API Gateway (handles TLS, auth, rate limiting)
- Internal service reduces attack surface
- Cost optimization (no cloud load balancer needed)

**Includes**:
- **NetworkPolicy**: Firewall rules for compliance
- **ServiceAccount**: RBAC for security
- **ConfigMap**: Centralized configuration

### 3. HorizontalPodAutoscaler (`hpa.yaml`)

**Scaling Metrics**:
1. **CPU utilization** (60% target) - Primary metric
2. **Memory utilization** (70% target)
3. **Request latency** (100ms P95) - Custom metric
4. **Requests per second** (500 RPS/pod) - Custom metric

**Scaling Behavior**:
```yaml
scaleUp:
  - Add 50% or 3 pods every 30s (whichever is larger)
  - Fast response to traffic spikes

scaleDown:
  - Remove 25% or 1 pod every 2 minutes (conservative)
  - 10-minute stabilization window
  - Avoid flapping during normal fluctuations
```

**Why Conservative Scale-Down**:
- Transaction volume can spike unpredictably
- Better to maintain capacity than risk latency spikes
- Cost of extra pod < cost of SLA violation

---

## Design Decisions

### Decision 1: 3 Replicas Minimum
**Choice**: Always run 3+ pods  
**Rationale**: 
- High availability (can lose 1 pod without impact)
- Zero-downtime deployments
- Load distribution
**Trade-off**: Higher cost (~$200/month vs $67 for 1 pod), but necessary for banking SLA

### Decision 2: maxUnavailable: 0
**Choice**: Never allow pods to go below 3 during updates  
**Rationale**: 
- Zero-downtime requirement for real-time transactions
- Users never experience service disruption
**Trade-off**: Slower deployments (~5 min vs 2 min), acceptable for production safety

### Decision 3: Pod Anti-Affinity
**Choice**: Force pods to run on different nodes  
**Rationale**:
- Node failure doesn't take down all replicas
- Better fault tolerance
**Trade-off**: Requires more nodes in cluster

### Decision 4: Non-Root Container
**Choice**: Run as UID 1000, not root  
**Rationale**:
- Security best practice for banking
- Prevents privilege escalation
- Compliance requirement (PCI-DSS)
**Trade-off**: Slightly more complex permissions

### Decision 5: Read-Only Filesystem
**Choice**: Container filesystem is immutable  
**Rationale**:
- Prevents malware from modifying files
- Compliance requirement
- Easier to debug (logs show exactly what's wrong)
**Trade-off**: Need emptyDir volumes for /tmp

---

## GPU Support

### When to Use GPUs

**Current**: CPU-based Random Forest (no GPU needed)

**Future Use Cases**:
- **Deep learning models** (LSTM, Transformer for fraud detection)
- **LLM-powered**: Analyzing transaction descriptions with BERT
- **Computer vision**: Document verification (KYC)

### Enable GPU Support

**1. Install NVIDIA GPU Operator**
```bash
helm install --wait --generate-name \
  -n gpu-operator --create-namespace \
  nvidia/gpu-operator
```

**2. Update Deployment**
```yaml
resources:
  limits:
    nvidia.com/gpu: "1"  # Request 1 GPU
```

**3. GPU Sharing (Cost Optimization)**

For inference workloads that don't need full GPU:
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    nvidia.com/mps: "50"  # 50% of GPU
```

**Benefits**:
- Run 2-4 inference services per GPU
- 60-80% cost reduction
- Maintain low latency

**4. Node Selection**
```yaml
nodeSelector:
  accelerator: nvidia-tesla-t4  # Cheaper than A100 for inference

tolerations:
- key: "nvidia.com/gpu"
  operator: "Equal"
  value: "true"
  effect: "NoSchedule"
```

---

## Scaling Strategies

### Horizontal Scaling

**Current Configuration**:
- **Min replicas**: 3 (always-on for HA)
- **Max replicas**: 20 (handle peak load)
- **Capacity**: 500 RPS/pod = 10K RPS total

**Scaling Triggers**:
```
CPU >60% → Scale up
Latency P95 >100ms → Scale up
Memory >70% → Scale up
```

**Example Scaling Event**:
```
Time    Load    Pods    Action
08:00   1K RPS  3       Baseline
09:00   3K RPS  6       +3 pods (CPU 70%)
09:30   6K RPS  12      +6 pods (CPU 75%)
10:00   9K RPS  18      +6 pods (approaching max)
12:00   4K RPS  18      Hold (stabilization window)
12:15   4K RPS  13      -5 pods (scale down slowly)
```

### Vertical Scaling

**For Larger Models**:
```yaml
# Current: 512Mi / 1Gi
# Large model: 2Gi / 4Gi

resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

**When to Vertical Scale**:
- Model size increases (ensemble models, deep learning)
- Need more CPU for faster inference
- Burst capacity insufficient

### Multi-Region Deployment

**For Global Scale** (50K+ TPS):
```
┌─────────────────────────────────────────┐
│       Global Load Balancer              │
│   (AWS Global Accelerator / CloudFlare) │
└──────────┬─────────────┬────────────────┘
           │             │
    ┌──────▼──────┐  ┌──▼──────────┐
    │  US Region  │  │  EU Region  │
    │  (EKS)      │  │  (EKS)      │
    │  10 pods    │  │  10 pods    │
    └─────────────┘  └─────────────┘
```

**Benefits**:
- Lower latency (geo-proximity)
- Disaster recovery
- Regulatory compliance (data residency)

---

## Security & Compliance

### Container Security
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  capabilities:
    drop: ["ALL"]
```

**Security Benefits**:
- ✅ No privilege escalation
- ✅ No file system tampering
- ✅ Minimal attack surface

### Network Security
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
```

**Benefits**:
- Firewall at pod level
- Prevent lateral movement
- Compliance requirement (PCI-DSS)

### RBAC
```yaml
serviceAccount: transaction-risk-scoring
```

**Principle of Least Privilege**:
- Service account has minimal permissions
- Cannot access other namespaces
- Audit trail of all actions

---

## Deployment Commands

### Apply manifests
```bash
kubectl apply -f k8s/
```

### Verify deployment
```bash
kubectl get pods -l app=transaction-risk-scoring
kubectl get svc transaction-risk-scoring
kubectl get hpa
```

### Check logs
```bash
kubectl logs -l app=transaction-risk-scoring --tail=100 -f
```

### Rolling update
```bash
kubectl set env deployment/transaction-risk-scoring MODEL_VERSION=v2.0.0
kubectl rollout status deployment/transaction-risk-scoring
```

### Rollback
```bash
kubectl rollout undo deployment/transaction-risk-scoring
```

---

## Monitoring

### Prometheus Metrics

The service exposes metrics at `/metrics`:
- `transaction_risk_scores_total{model_version, risk_level, status}`
- `transaction_risk_latency_seconds{model_version}`

### Example Queries
```promql
# P95 latency
histogram_quantile(0.95, transaction_risk_latency_seconds)

# Requests per second
rate(transaction_risk_scores_total[5m])

# Error rate
rate(transaction_risk_scores_total{status="error"}[5m])
```

---

## Cost Analysis

### Current Configuration (3 pods)

**AWS EKS**:
- Instance: t3.medium (2 vCPU, 4GB RAM)
- Cost: ~$0.0416/hour × 3 = ~$90/month
- Capacity: 1,500 RPS

### Peak Load (20 pods)

- Cost: ~$0.0416/hour × 20 = ~$600/month
- Capacity: 10,000 RPS

### Optimization Strategies

**1. Spot Instances** (70% savings)
**2. Right-Sizing** (monitor actual usage)
**3. Cluster Autoscaler** (scale nodes with pods)

---

## Production Checklist

- [x] **Security**: Non-root, NetworkPolicy, RBAC
- [x] **Availability**: 3 replicas, PDB, anti-affinity
- [x] **Monitoring**: Prometheus metrics, health checks
- [x] **Scaling**: HPA configured and tested
- [x] **Performance**: Resource requests/limits optimized
- [x] **Disaster Recovery**: Rollback procedures documented
- [x] **Compliance**: Audit logging, encryption, network isolation

---

**Ready for production deployment in Dnar's crypto-to-fiat platform!**