# Terraform Infrastructure Sketch

Example Terraform configuration for deploying the ML service to AWS EKS.

---

## Module Structure
```
terraform/
├── main.tf              # Main configuration
├── variables.tf         # Input variables
├── outputs.tf           # Outputs
├── modules/
│   ├── eks/            # EKS cluster module
│   ├── ml-service/     # ML service deployment
│   └── monitoring/     # Prometheus/Grafana
```

---

## Example: `main.tf`
```hcl
# Provider configuration
provider "aws" {
  region = var.aws_region
}

# EKS Cluster
module "eks" {
  source = "./modules/eks"
  
  cluster_name    = "dnar-ml-production"
  cluster_version = "1.28"
  
  vpc_id     = var.vpc_id
  subnet_ids = var.subnet_ids
  
  node_groups = {
    ml_inference = {
      desired_size = 3
      min_size     = 3
      max_size     = 20
      
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      
      labels = {
        workload = "ml-inference"
      }
      
      taints = []
    }
    
    ml_gpu = {
      desired_size = 1
      min_size     = 0
      max_size     = 5
      
      instance_types = ["g4dn.xlarge"]
      capacity_type  = "SPOT"  # 70% cheaper
      
      labels = {
        workload = "ml-gpu"
      }
      
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NoSchedule"
      }]
    }
  }
}

# ML Service Deployment
module "ml_service" {
  source = "./modules/ml-service"
  
  cluster_name = module.eks.cluster_name
  namespace    = "ml-production"
  
  service_name    = "transaction-risk-scoring"
  image           = "gcr.io/dnar-prod/transaction-risk-scoring:v1.0.0"
  replicas        = 3
  
  resources = {
    requests = {
      cpu    = "500m"
      memory = "512Mi"
    }
    limits = {
      cpu    = "2000m"
      memory = "1Gi"
    }
  }
  
  autoscaling = {
    min_replicas = 3
    max_replicas = 20
    target_cpu   = 60
  }
  
  environment_variables = {
    MODEL_VERSION = "v1.0.0"
    ENVIRONMENT   = "production"
    LOG_LEVEL     = "INFO"
  }
}

# Monitoring Stack
module "monitoring" {
  source = "./modules/monitoring"
  
  cluster_name = module.eks.cluster_name
  namespace    = "monitoring"
  
  prometheus_enabled = true
  grafana_enabled    = true
  
  alerting = {
    pagerduty_key = var.pagerduty_integration_key
    slack_webhook = var.slack_webhook_url
  }
}

# Secret Management
resource "aws_secretsmanager_secret" "ml_api_key" {
  name = "dnar/ml-inference/api-key"
  
  tags = {
    Environment = "production"
    Service     = "ml-inference"
  }
}

# External Secrets Operator
resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  namespace  = "external-secrets-system"
  
  create_namespace = true
}
```

---

## Example: `variables.tf`
```hcl
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID for EKS cluster"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for EKS cluster"
  type        = list(string)
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "pagerduty_integration_key" {
  description = "PagerDuty integration key for alerts"
  type        = string
  sensitive   = true
}
```

---

## Deployment Commands
```bash
# Initialize Terraform
terraform init

# Plan changes
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan

# Get cluster credentials
aws eks update-kubeconfig --name dnar-ml-production

# Verify deployment
kubectl get pods -n ml-production
```

---

## Cost Estimation

| Component | Resource | Monthly Cost (AWS) |
|-----------|----------|-------------------|
| EKS Control Plane | 1 cluster | $73 |
| Worker Nodes (CPU) | 3x t3.medium | ~$90 |
| Worker Nodes (GPU) | 1x g4dn.xlarge (spot) | ~$80 |
| Load Balancer | NLB | ~$20 |
| **Total** | | **~$263/month** |

**Scaling to 20 pods**: ~$600/month