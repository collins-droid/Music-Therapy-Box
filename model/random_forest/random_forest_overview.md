# Random Forest Overview

## What is Random Forest?

Random Forest is an ensemble machine learning algorithm that combines multiple decision trees to make more accurate and robust predictions. It's particularly well-suited for classification and regression tasks, and is known for its high accuracy, resistance to overfitting, and ability to handle various types of data.

## How Random Forest Works

### 1. **Bootstrap Aggregating (Bagging)**
- Creates multiple training datasets by sampling with replacement from the original dataset
- Each tree is trained on a different subset of the data
- This reduces variance and prevents overfitting

### 2. **Random Feature Selection**
- At each split in each tree, only a random subset of features is considered
- This adds randomness and reduces correlation between trees
- Typically uses √n features for classification (where n is total features)

### 3. **Voting/Averaging**
- For classification: Majority vote among all trees
- For regression: Average of all tree predictions
- Final prediction is more stable and accurate than individual trees

## Key Advantages

### **High Accuracy**
- Often achieves better performance than single decision trees
- Works well with both categorical and numerical features
- Handles missing values gracefully

### **Robustness**
- Less prone to overfitting compared to single trees
- Works well with noisy data
- Handles outliers better than many other algorithms

### **Feature Importance**
- Provides built-in feature importance scores
- Helps identify which features contribute most to predictions
- Useful for feature selection and understanding

### **No Preprocessing Required**
- Works with raw data without extensive preprocessing
- Handles different scales of features automatically
- No need for feature normalization

## Implementation in Music Therapy Box

### **Dataset**
- Uses synthetic HR (Heart Rate) and EDA (Electrodermal Activity) data
- Features extracted from physiological signals:
  - **HR Features**: mean, std, min, max, range, skew, kurtosis
  - **EDA Features**: mean, std, min, max, range, skew, kurtosis, slope
- Binary classification: Stress (1) vs No Stress (0)

### **Model Configuration**
```python
RandomForestClassifier(
    n_estimators=200,    # Number of trees
    max_depth=None,      # No depth limit
    random_state=42,     # For reproducibility
    n_jobs=-1           # Use all CPU cores
)
```

### **Performance Results**
- **Accuracy**: 94.5%
- **Precision**: 95% (macro average)
- **Recall**: 94% (macro average)
- **F1-Score**: 94% (macro average)

### **Feature Importance**
The model can identify which physiological features are most predictive:
- Heart rate variability patterns
- EDA response characteristics
- Statistical moments of signal distributions

## Why Random Forest for Stress Detection?

### **1. Physiological Signal Characteristics**
- Physiological signals are inherently noisy and variable
- Random Forest's robustness handles this noise well
- Multiple trees can capture different patterns in the data

### **2. Feature Richness**
- 15 different statistical features from HR and EDA
- Random Forest excels with multiple features
- Feature importance helps understand stress indicators

### **3. Real-time Performance**
- Fast prediction once trained
- No complex preprocessing needed
- Suitable for embedded systems

### **4. Interpretability**
- Feature importance provides insights
- Can understand which physiological changes indicate stress
- Useful for medical/psychological interpretation

## Model Files

### **Training Script**: `random_forest_train.py`
- Loads synthetic dataset
- Trains Random Forest classifier
- Evaluates performance
- Saves trained model

### **Trained Model**: `stress_random_forest.pkl`
- Serialized Random Forest model
- Loaded by `stress_predictor.py` for real-time predictions
- Contains all learned parameters and tree structures

### **Dataset**: `synthetic_hr_eda_windows.csv`
- 1000 samples of synthetic physiological data
- Balanced classes (518 no-stress, 482 stress)
- 15 features + 1 label column

## Usage in Production

### **Prediction Pipeline**
1. **Data Collection**: Real-time HR and EDA from sensors
2. **Feature Extraction**: Calculate statistical features from signal windows
3. **Prediction**: Feed features to Random Forest model
4. **Decision**: Trigger music therapy based on stress prediction

### **Integration**
- Model loaded once at startup
- Fast prediction for real-time stress detection
- Confidence scores for decision thresholds
- Prediction history for trend analysis

## Limitations and Considerations

### **Model Limitations**
- Trained on synthetic data (may not generalize to real users)
- Binary classification (no stress levels)
- Fixed feature set (may miss other important patterns)

### **Data Requirements**
- Requires sufficient training data
- Needs representative samples of both stress states
- Quality of physiological data affects performance

### **Computational Requirements**
- Memory usage scales with number of trees
- Training time increases with dataset size
- Prediction is fast but requires model loading

## Future Improvements

### **Model Enhancements**
- Train on real physiological data
- Multi-class stress levels (low, medium, high)
- Online learning for personalization
- Ensemble with other algorithms

### **Feature Engineering**
- Additional physiological features (temperature, movement)
- Time-series features (trends, patterns)
- Cross-modal feature interactions
- Domain-specific feature selection

### **Performance Optimization**
- Model compression for embedded deployment
- Feature selection based on importance
- Hyperparameter optimization
- Cross-validation for robust evaluation

## References

- Breiman, L. (2001). Random forests. Machine learning, 45(1), 5-32.
- WESAD Dataset: Schmidt, P., et al. (2018). Introducing WESAD, a Multimodal Dataset for Wearable Stress and Affect Detection.
- Scikit-learn Random Forest Documentation: https://scikit-learn.org/stable/modules/ensemble.html#random-forests

---

*This Random Forest implementation serves as the core machine learning component for stress detection in the Music Therapy Box, providing reliable real-time predictions based on physiological signals.*
