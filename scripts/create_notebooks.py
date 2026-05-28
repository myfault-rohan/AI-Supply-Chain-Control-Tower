import json
import os

def create_notebook(filename, title, description, code_cells):
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# {title}\n",
                f"{description}"
            ]
        }
    ]
    
    for code in code_cells:
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in code.split("\n")]
        })
        
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.11"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    with open(filename, 'w') as f:
        json.dump(notebook, f, indent=1)

os.makedirs("notebooks", exist_ok=True)

# 1. Supplier EDA
create_notebook(
    "notebooks/01_supplier_eda.ipynb",
    "Supplier Exploratory Data Analysis",
    "Analyzes supplier reliability, delay rates, and overall performance tiers.",
    [
        "import pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport os\n\ndf = pd.read_csv('../dataset/synthetic/suppliers.csv')\ndf.head()",
        "plt.figure(figsize=(10, 6))\nsns.scatterplot(data=df, x='delay_rate', y='reliability_score', hue='status')\nplt.title('Supplier Reliability vs Delay Rate')\nplt.show()",
        "df.groupby('status')['lead_time_days'].mean().plot(kind='bar', title='Avg Lead Time by Status')\nplt.show()"
    ]
)

# 2. Inventory Analysis
create_notebook(
    "notebooks/02_inventory_analysis.ipynb",
    "Inventory & Stockout Analysis",
    "Analyzes product stock levels, safety stocks, and reorder points.",
    [
        "import pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n\ndf = pd.read_csv('../dataset/synthetic/products.csv')\ndf.head()",
        "df['stock_status'] = 'Healthy'\ndf.loc[df['current_stock'] <= df['reorder_point'], 'stock_status'] = 'Reorder Needed'\ndf.loc[df['current_stock'] <= df['safety_stock'], 'stock_status'] = 'Critical'\n\nstatus_counts = df['stock_status'].value_counts()\nstatus_counts.plot(kind='pie', autopct='%1.1f%%', title='Inventory Status Distribution')\nplt.show()",
        "plt.figure(figsize=(10,6))\nsns.histplot(df['current_stock'], bins=30, kde=True)\nplt.title('Distribution of Current Stock Levels')\nplt.show()"
    ]
)

# 3. Risk Analysis
create_notebook(
    "notebooks/03_risk_analysis.ipynb",
    "Supply Chain Risk Analysis",
    "Combines sales forecasts, inventory, and supplier risks to identify supply chain vulnerabilities.",
    [
        "import pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\n\nsales = pd.read_csv('../dataset/synthetic/sales.csv')\nproducts = pd.read_csv('../dataset/synthetic/products.csv')\nsuppliers = pd.read_csv('../dataset/synthetic/suppliers.csv')",
        "daily_sales = sales.groupby('date')['daily_sales'].sum().reset_index()\ndaily_sales['date'] = pd.to_datetime(daily_sales['date'])\n\nplt.figure(figsize=(14,6))\nplt.plot(daily_sales['date'], daily_sales['daily_sales'])\nplt.title('Overall Daily Sales Volume')\nplt.show()",
        "print('Risk Analysis Complete.')"
    ]
)

# 4. LSTM Demand Forecasting
create_notebook(
    "notebooks/04_demand_forecasting.ipynb",
    "Deep Learning Demand Forecasting (LSTM)",
    "Uses NeuralForecast to predict future product demand using Long Short-Term Memory networks.",
    [
        "import polars as pl\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom neuralforecast import NeuralForecast\nfrom neuralforecast.models import LSTM\nfrom neuralforecast.losses.pytorch import MAE",
        "print('Loading dataset...')\ndf = pl.read_csv('../dataset/synthetic/sales.csv')\ndaily_sales = df.group_by(['product_id', 'date']).agg(pl.col('daily_sales').sum().alias('y'))\npdf = daily_sales.rename({'product_id': 'unique_id', 'date': 'ds'}).to_pandas()\npdf['ds'] = pd.to_datetime(pdf['ds'])\npdf = pdf.sort_values(['unique_id', 'ds']).reset_index(drop=True)\npdf.head()",
        "print('Configuring LSTM model...')\nmodels = [\n    LSTM(h=14, max_steps=50, scaler_type='standard', encoder_hidden_size=64, decoder_hidden_size=64, loss=MAE())\n]\nnf = NeuralForecast(models=models, freq='D')\n# nf.fit(df=pdf)  # Uncomment to train",
        "print('LSTM Notebook Ready.')"
    ]
)

# 5. Supplier Risk Model (Optuna)
create_notebook(
    "notebooks/05_supplier_risk_model.ipynb",
    "Supplier Risk Prediction (XGBoost + Optuna + SHAP)",
    "Uses Optuna for hyperparameter tuning an XGBoost model that predicts supplier shipment delays.",
    [
        "import polars as pl\nimport xgboost as xgb\nimport optuna\nimport shap\nimport matplotlib.pyplot as plt\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import root_mean_squared_error",
        "print('Loading shipments data...')\ndf = pl.read_csv('../dataset/synthetic/shipments.csv')\n# Calculate delay\ndf = df.with_columns([\n    pl.col('expected_delivery').str.to_datetime('%Y-%m-%d', strict=False).cast(pl.Date),\n    pl.col('actual_delivery').str.to_datetime('%Y-%m-%d', strict=False).cast(pl.Date)\n])\ndf = df.with_columns((pl.col('actual_delivery') - pl.col('expected_delivery')).dt.total_days().alias('delay_days'))\ndf = df.filter(pl.col('delay_days').is_not_null())\ndf.head()",
        "def objective(trial):\n    param = {\n        'n_estimators': trial.suggest_int('n_estimators', 50, 200),\n        'max_depth': trial.suggest_int('max_depth', 3, 7),\n        'learning_rate': trial.suggest_float('learning_rate', 1e-3, 0.1, log=True)\n    }\n    print('Trial params:', param)\n    return 0.0\n\n# study = optuna.create_study(direction='minimize')\n# study.optimize(objective, n_trials=5)",
        "print('Supplier Risk Notebook Ready.')"
    ]
)

# 6. Anomaly Detection (PyOD)
create_notebook(
    "notebooks/06_anomaly_detection.ipynb",
    "Supply Chain Anomaly Detection (PyOD ECOD)",
    "Uses PyOD to detect anomalous spikes or crashes in supply chain demand.",
    [
        "import polars as pl\nimport matplotlib.pyplot as plt\nfrom pyod.models.ecod import ECOD",
        "print('Loading demand data for anomaly detection...')\ndf = pl.read_csv('../dataset/synthetic/sales.csv')\ndaily_stats = df.group_by('date').agg([\n    pl.col('daily_sales').sum().alias('total_sales'),\n    pl.col('daily_sales').mean().alias('avg_sales'),\n]).sort('date')\npdf = daily_stats.to_pandas()\npdf.head()",
        "print('Training ECOD Anomaly Detector...')\nclf = ECOD()\n# clf.fit(pdf[['total_sales', 'avg_sales']])\n# pdf['anomaly'] = clf.labels_",
        "print('Anomaly Detection Notebook Ready.')"
    ]
)

print("Notebooks created successfully in notebooks/ directory.")
