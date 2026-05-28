import mlflow
import pandas as pd
mlflow.set_experiment("MLflow Quickstart")


df = pd.read_csv("./breast_cancer.csv")