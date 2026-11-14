import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import xgboost as xgb

df = pd.read_csv(r'C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\yolopose\dataset_path\dataset.csv')

X = df.drop(['label', 'image_name'], axis=1) 
y = df['label'].map({'Suspicious': 0, 'Normal': 1})

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Create and configure the XGBoost classifier
model = xgb.XGBClassifier(
    n_estimators=50,              # Number of trees (iterations)
    eval_metric='logloss',        # Evaluation metric for classification
    objective='binary:logistic',  # Binary classification task
    tree_method='hist',           # Optimized tree method for faster training
    eta=0.1,                      # Learning rate
    max_depth=3,                  # Maximum tree depth (controls model complexity)
    enable_categorical=True       # Enable if using categorical features (if applicable)
)

# Train the model on the training data
model.fit(X_train, y_train)

# Output the model details
print(model)

# Make predictions on the test set
y_pred = model.predict(X_test)

# Evaluate the model's accuracy
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy}")

# Save the trained model to a file
model.save_model(r"C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\trained_model.json")
