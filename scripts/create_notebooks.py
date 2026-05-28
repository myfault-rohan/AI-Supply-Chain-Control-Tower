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
        "daily_sales = sales.groupby('date')['quantity'].sum().reset_index()\ndaily_sales['date'] = pd.to_datetime(daily_sales['date'])\n\nplt.figure(figsize=(14,6))\nplt.plot(daily_sales['date'], daily_sales['quantity'])\nplt.title('Overall Daily Sales Volume')\nplt.show()",
        "print('Risk Analysis Complete.')"
    ]
)

print("Notebooks created successfully in notebooks/ directory.")
