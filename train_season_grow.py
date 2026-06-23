import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import joblib

# 1. Load dataset
df = pd.read_csv("season_grow_dataset.csv")

# Features and targets
X = df[["crop", "temp_mean", "rain_mean", "ph_mean"]]
y_season = df["season_label"]
y_days = df["days_to_harvest"]

cat_features = ["crop"]
num_features = ["temp_mean", "rain_mean", "ph_mean"]

preprocess = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
        ("num", "passthrough", num_features),
    ]
)

# 2. Season model (classification)
season_model = Pipeline(
    steps=[
        ("preprocess", preprocess),
        ("clf", RandomForestClassifier(n_estimators=200, random_state=42)),
    ]
)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_season, test_size=0.2, random_state=42
)

season_model.fit(X_train, y_train)
print("Season model train accuracy:", season_model.score(X_train, y_train))
print("Season model test accuracy:", season_model.score(X_test, y_test))

joblib.dump(season_model, "season_model.pkl")

# 3. Days-to-harvest model (regression)
days_model = Pipeline(
    steps=[
        ("preprocess", preprocess),
        ("reg", RandomForestRegressor(n_estimators=200, random_state=42)),
    ]
)

X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(
    X, y_days, test_size=0.2, random_state=42
)

days_model.fit(X_train_d, y_train_d)
print("Days model train R^2:", days_model.score(X_train_d, y_train_d))
print("Days model test R^2:", days_model.score(X_test_d, y_test_d))

joblib.dump(days_model, "days_model.pkl")

print("✅ Models saved: season_model.pkl, days_model.pkl")