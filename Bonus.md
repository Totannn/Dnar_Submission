# CI/CD Pipeline for ML Inference Service

Complete CI/CD pipeline examples for production ML deployment.

---

## GitHub Actions Pipeline

**File**: `.github/workflows/deploy.yml`
```yaml
name: ML Inference CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: gcr.io
  PROJECT_ID: dnar-production
  SERVICE_NAME: transaction-risk-scoring

jobs:
  # Job 1: Code Quality & Testing
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov black flake8
      
      - name: Lint with flake8
        run: flake8 . --count --select=E9,F63,F7,F82
      
      - name: Format check with black
        run: black --check .
      
      - name: Run unit tests
        run: pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  # Job 2: Security Scanning
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'sarif'
          output: 'trivy-results.sarif'

  # Job 3: Build and Push Docker Image
  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:${{ github.sha }} .
      
      - name: Push to registry
        run: docker push ${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:${{ github.sha }}

  # Job 4: Deploy to Staging
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/${{ env.SERVICE_NAME }} \
            ${{ env.SERVICE_NAME }}=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            -n staging
          kubectl rollout status deployment/${{ env.SERVICE_NAME }} -n staging

  # Job 5: Deploy to Production (Manual Approval)
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/${{ env.SERVICE_NAME }} \
            ${{ env.SERVICE_NAME }}=${{ env.REGISTRY }}/${{ env.PROJECT_ID }}/${{ env.SERVICE_NAME }}:${{ github.sha }} \
            -n production
```
