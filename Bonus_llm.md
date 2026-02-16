# Deploying LLMs for Advanced Fraud Detection

Notes on deploying Large Language Models for advanced ML workloads at Dnar.

---

## Use Cases for LLMs at Dnar

### 1. Transaction Description Analysis
```
User input: "Sending money to uncle for medical emergency"
LLM analyzes: Sentiment, urgency, common fraud patterns
Risk signal: MEDIUM (common fraud excuse)
```

### 2. Customer Support Chatbot
```
Customer: "Why was my transaction flagged?"
LLM: Explains risk factors in plain language
Compliance: Maintains audit trail
```

### 3. Enhanced KYC
```
Document analysis: Verify ID documents using vision models
NLP verification: Cross-check customer statements
```

---

## LLM Deployment Architecture
```
┌─────────────────────────────────────────┐
│         LLM Inference Service           │
├─────────────────────────────────────────┤
│                                         │
│  1. Model Serving (vLLM)                │
│     • Multi-GPU support                 │
│     • Continuous batching               │
│     • KV cache optimization             │
│     • PagedAttention                    │
│                                         │
│  2. Model Size Options                  │
│     • 7B params: 1x A10G GPU (~$0.50/h)│
│     • 13B params: 1x A100 (~$3/h)      │
│     • 70B params: 4x A100 (~$12/h)     │
│                                         │
│  3. Cost Optimization                   │
│     • Spot instances (70% savings)      │
│     • Dynamic batching                  │
│     • Quantization (4-bit, 8-bit)       │
│     • Model caching                     │
└─────────────────────────────────────────┘
```

---

## Recommended Stack: vLLM

### Why vLLM?
- **10-20x faster** than standard PyTorch serving
- **Continuous batching**: Process requests as they arrive
- **PagedAttention**: Efficient memory management
- **Multi-GPU**: Scales to large models

### Deployment Example
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-fraud-detection
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        - --model
        - meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size
        - "1"
        - --gpu-memory-utilization
        - "0.9"
        
        resources:
          limits:
            nvidia.com/gpu: "1"
        
        env:
        - name: HUGGING_FACE_HUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: hf-token
              key: token
```

---

## Performance Benchmarks

| Model | GPU | Throughput | Latency (P95) | Cost/1M tokens |
|-------|-----|------------|---------------|----------------|
| Llama-2 7B | A10G | 180 tok/s | 2.5s | $0.50 |
| Llama-2 13B | A100 | 120 tok/s | 4.2s | $2.00 |
| Llama-2 70B | 4x A100 | 80 tok/s | 8.5s | $8.00 |

**With 4-bit Quantization**:
- 40% faster inference
- 75% less memory
- Minimal accuracy loss (<2%)

---

## Cost Optimization Strategies

### 1. Quantization
```python
# 4-bit quantization with bitsandbytes
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-chat-hf",
    quantization_config=quantization_config
)
```

**Savings**: Run 13B model on single GPU instead of 2 GPUs

### 2. Spot Instances
```yaml
nodeSelector:
  node.kubernetes.io/lifecycle: spot

tolerations:
- key: "spot"
  operator: "Equal"
  value: "true"
```

**Savings**: 70% cost reduction

### 3. Dynamic Batching
```python
# vLLM automatically batches requests
# No code changes needed
# 5-10x throughput improvement
```

---

## Scaling Pattern

### Small Scale (Development)
```
1 pod × 1 GPU (A10G spot)
Cost: ~$80/month
Throughput: ~500 requests/day
```

### Medium Scale (Production)
```
3 pods × 1 GPU each (A10G spot)
Cost: ~$240/month
Throughput: ~5K requests/day
```

### Large Scale (Enterprise)
```
10 pods × 1 GPU each (A100 spot)
Cost: ~$2,400/month
Throughput: ~50K requests/day
```

---

## Monitoring LLM Performance
```python
# Custom metrics for LLM monitoring
llm_token_generation_rate = Gauge(
    'llm_tokens_per_second',
    'Token generation rate'
)

llm_queue_length = Gauge(
    'llm_request_queue_length',
    'Number of requests waiting'
)

llm_gpu_memory_used = Gauge(
    'llm_gpu_memory_bytes',
    'GPU memory usage'
)
```

**Critical Alerts**:
- Token generation rate < 50 tok/s (slow inference)
- Queue length > 10 (backlog building)
- GPU memory > 90% (risk of OOM)

---

## Security Considerations

### 1. Prompt Injection Protection
```python
def sanitize_prompt(user_input: str) -> str:
    # Remove instruction-like patterns
    forbidden_patterns = [
        "ignore previous instructions",
        "system:",
        "assistant:",
    ]
    # Validate and sanitize
    return sanitized_input
```

### 2. Output Filtering
```python
def filter_sensitive_output(llm_response: str) -> str:
    # Redact PII
    # Remove hallucinated data
    # Validate factual claims
    return filtered_response
```

### 3. Rate Limiting
```yaml
# Prevent abuse
apiVersion: v1
kind: LimitRange
metadata:
  name: llm-rate-limit
spec:
  limits:
  - max:
      requests.per.second: "10"
    type: Pod
```

---

---
