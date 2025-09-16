# random_forest_train.py

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

# ====== 1. Load dataset ======
df = pd.read_csv("synthetic_hr_eda_windows.csv")

# ====== 2. Select only HR + EDA features ======
hr_features = ['hr_mean','hr_std','hr_min','hr_max','hr_range','hr_skew','hr_kurtosis']
eda_features = ['eda_mean','eda_std','eda_min','eda_max','eda_range','eda_skew','eda_kurtosis','eda_slope']

X = df[hr_features + eda_features]
y = df['label']

# ====== 3. Train/test split ======
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ====== 4. Train Random Forest ======
rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=None,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)

# ====== 5. Evaluate ======
y_pred = rf.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print(classification_report(y_test, y_pred))

# ====== 6. Save model ======
joblib.dump(rf, "stress_random_forest.pkl")
print(" Model saved as stress_random_forest.pkl")
