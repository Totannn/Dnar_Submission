"""
Train a fraud detection model for transaction risk scoring
Simulates real-world fintech ML training for AML/fraud detection
"""
import pickle
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

def generate_synthetic_data(n_samples=10000):
    """
    Generate synthetic transaction data for fraud detection
    
    Features:
    - transaction_amount_usd
    - sender_age_days
    - transactions_last_24h
    - avg_transaction_amount
    - sender_country_risk_score
    - is_new_recipient
    - hour_of_day
    
    Target: is_fraudulent (0=legit, 1=fraud)
    """
    np.random.seed(42)
    
    # Generate legitimate transactions (90%)
    n_legit = int(n_samples * 0.9)
    legit_data = np.column_stack([
        np.random.lognormal(mean=7, sigma=1.5, size=n_legit),  # amount (lower)
        np.random.randint(30, 1000, size=n_legit),  # account age (older)
        np.random.poisson(2, size=n_legit),  # transactions/24h (normal)
        np.random.lognormal(mean=6.5, sigma=1, size=n_legit),  # avg amount
        np.random.beta(2, 8, size=n_legit),  # country risk (lower)
        np.random.choice([0, 1], size=n_legit, p=[0.8, 0.2]),  # new recipient
        np.random.randint(0, 24, size=n_legit)  # hour
    ])
    legit_labels = np.zeros(n_legit)
    
    # Generate fraudulent transactions (10%)
    n_fraud = n_samples - n_legit
    fraud_data = np.column_stack([
        np.random.lognormal(mean=9, sigma=2, size=n_fraud),  # amount (higher)
        np.random.randint(1, 60, size=n_fraud),  # account age (newer)
        np.random.poisson(8, size=n_fraud),  # transactions/24h (high)
        np.random.lognormal(mean=6, sigma=1.5, size=n_fraud),  # avg amount
        np.random.beta(8, 2, size=n_fraud),  # country risk (higher)
        np.random.choice([0, 1], size=n_fraud, p=[0.3, 0.7]),  # new recipient
        np.random.choice([0, 1, 2, 3, 4, 22, 23], size=n_fraud)  # odd hours
    ])
    fraud_labels = np.ones(n_fraud)
    
    # Combine and shuffle
    X = np.vstack([legit_data, fraud_data])
    y = np.concatenate([legit_labels, fraud_labels])
    
    # Shuffle
    indices = np.random.permutation(len(X))
    X = X[indices]
    y = y[indices]
    
    return X, y


def train_model():
    """Train fraud detection model"""
    print("Generating synthetic transaction data...")
    X, y = generate_synthetic_data(n_samples=10000)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Fraud rate: {y.mean():.2%}")
    
    # Train Random Forest classifier
    print("\nTraining Random Forest model...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight='balanced',  # Handle imbalanced data
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Evaluate on test set
    print("\nEvaluating model...")
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Legitimate', 'Fraudulent']))
    
    roc_auc = roc_auc_score(y_test, y_proba)
    print(f"\nROC-AUC Score: {roc_auc:.4f}")
    
    # Feature importance
    feature_names = [
        'transaction_amount_usd',
        'sender_age_days',
        'transactions_last_24h',
        'avg_transaction_amount',
        'sender_country_risk_score',
        'is_new_recipient',
        'hour_of_day'
    ]
    
    print("\nFeature Importance:")
    for name, importance in zip(feature_names, model.feature_importances_):
        print(f"  {name}: {importance:.4f}")
    
    # Save model
    os.makedirs("models", exist_ok=True)
    model_path = "models/model.pkl"
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    print(f"\nModel saved to {model_path}")
    print(f"Model size: {os.path.getsize(model_path) / 1024:.2f} KB")
    
    # Save metadata
    metadata = {
        "model_type": "RandomForestClassifier",
        "n_features": 7,
        "feature_names": feature_names,
        "roc_auc": roc_auc,
        "training_samples": len(X_train),
        "fraud_rate": float(y.mean())
    }
    
    with open("models/metadata.pkl", 'wb') as f:
        pickle.dump(metadata, f)
    
    print("\nMetadata saved to models/metadata.pkl")
    
    return model, roc_auc


if __name__ == "__main__":
    model, roc_auc = train_model()
    print("\n✅ Training complete!")
    print(f"Model performance: ROC-AUC = {roc_auc:.4f}")
    print("Ready for deployment")