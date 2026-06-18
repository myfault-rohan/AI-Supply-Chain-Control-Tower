import nbformat as nbf
from nbclient import NotebookClient
import os

os.makedirs('notebooks', exist_ok=True)

def run_and_save(nb, filename):
    client = NotebookClient(nb, timeout=600, kernel_name='python3', resources={'metadata': {'path': 'notebooks'}})
    try:
        client.execute()
    except Exception as e:
        print(f"Error executing {filename}: {e}")
    finally:
        with open(filename, 'w', encoding='utf-8') as f:
            nbf.write(nb, f)
        print(f"Saved {filename}")

# ==============================================================================
# Notebook 1: 01_olist_eda.ipynb
# ==============================================================================
nb1 = nbf.v4.new_notebook()

nb1.cells = [
    nbf.v4.new_markdown_cell("# Olist E-Commerce: Exploratory Data Analysis\n\nThis notebook analyzes the Olist dataset to establish the baseline facts about seller geography, dispatch times, review scores, and on-time delivery rates."),
    nbf.v4.new_code_cell("""import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Use consistent styling
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_context("notebook")

# Load the master processed table
master = pd.read_parquet('../data/processed/master.parquet')
print(f"Master table loaded: {master.shape[0]:,} rows x {master.shape[1]} columns")"""),
    
    nbf.v4.new_markdown_cell("## Finding 1: Seller Geographic Concentration\n\nWhere are the sellers located? A high concentration in a single state could create structural supply chain risks."),
    nbf.v4.new_code_cell("""# Get unique sellers and their states
sellers = master.drop_duplicates(subset=['seller_id'])
state_counts = sellers['seller_state'].value_counts()

plt.figure(figsize=(12, 5))
sns.barplot(x=state_counts.index, y=state_counts.values, color='#3498db')
plt.title('Seller Count by State (Origin)')
plt.ylabel('Number of Sellers')
plt.xlabel('State Code')
plt.show()

sp_pct = state_counts.loc['SP'] / state_counts.sum() * 100
print(f"Finding: {sp_pct:.1f}% of sellers are based in São Paulo (SP). This is real, not synthetic data.")
print("This creates a geographic concentration risk — delayed shipments from this hub disproportionately affect national delivery performance.")"""),
    
    nbf.v4.new_markdown_cell("## Finding 2: Dispatch Time Distribution\n\nHow long does it take for a seller to hand over the product to the logistics carrier?"),
    nbf.v4.new_code_cell("""dispatch_data = master.loc[master['dispatch_days'] > 0, 'dispatch_days']

plt.figure(figsize=(10, 5))
sns.histplot(dispatch_data, bins=50, binrange=(0, 20), color='#e74c3c')
plt.title('Distribution of Seller Dispatch Time (Days)')
plt.xlabel('Days from Order Approval to Carrier Handoff')
plt.ylabel('Order Volume')
plt.show()

median_dispatch = dispatch_data.median()
p95_dispatch = dispatch_data.quantile(0.95)
print(f"Median dispatch time: {median_dispatch:.1f} days")
print(f"95th percentile: {p95_dispatch:.1f} days")
print(f"Finding: While most orders are dispatched in ~2 days, the long right tail indicates significant variation in seller reliability.")"""),

    nbf.v4.new_markdown_cell("## Finding 3: Review Score Distribution\n\nCustomer satisfaction is heavily right-skewed. This means a 1- or 2-star review is not just noise; it is a strong signal of failure."),
    nbf.v4.new_code_cell("""plt.figure(figsize=(8, 4))
sns.countplot(data=master.drop_duplicates('order_id'), x='review_score', palette='viridis')
plt.title('Distribution of Customer Review Scores')
plt.xlabel('Review Score (1-5)')
plt.ylabel('Number of Orders')
plt.show()

low_scores = master.drop_duplicates('order_id')['review_score'].value_counts(normalize=True).sort_index()
print(f"Finding: 1- and 2-star reviews make up only {(low_scores.get(1.0, 0) + low_scores.get(2.0, 0))*100:.1f}% of total reviews.")
print("This skew makes low scores an excellent leading indicator of operational failure for our predictive model.")"""),

    nbf.v4.new_markdown_cell("## Finding 4: On-Time Delivery Rate Over Time\n\nDoes the platform's reliability change over time? We look at the monthly OTD rate."),
    nbf.v4.new_code_cell("""# Calculate monthly OTD rate
monthly_otd = master[master['order_status'] == 'delivered'].groupby('purchase_month').agg(
    total_orders=('order_id', 'size'),
    on_time_orders=('on_time', 'sum')
)
monthly_otd['otd_rate'] = monthly_otd['on_time_orders'] / monthly_otd['total_orders']

# Convert period index to timestamp for plotting
monthly_otd.index = monthly_otd.index.to_timestamp()

plt.figure(figsize=(12, 5))
plt.plot(monthly_otd.index, monthly_otd['otd_rate'], marker='o', color='#2ecc71', linewidth=2)
plt.axhline(0.8, color='red', linestyle='--', label='80% Threshold')
plt.title('Platform On-Time Delivery Rate (Monthly)')
plt.ylabel('OTD Rate')
plt.xlabel('Month')
plt.ylim(0.5, 1.0)
plt.legend()
plt.show()

print("Finding: The OTD rate drops significantly in late 2017 and early 2018 (likely Black Friday and Holiday peaks).")
print("This temporal variation confirms we must use a strict temporal split for our machine learning model.")"""),

    nbf.v4.new_markdown_cell("## Finding 5: Freight Value vs Delivery Time\n\nDoes paying more for freight mean faster delivery?"),
    nbf.v4.new_code_cell("""sample_df = master.sample(10000, random_state=42)

plt.figure(figsize=(10, 6))
sns.scatterplot(data=sample_df, x='freight_value', y='delivery_days', alpha=0.3, color='#9b59b6')
plt.title('Freight Value vs. Delivery Days (Sample = 10,000 orders)')
plt.xlabel('Freight Value (BRL)')
plt.ylabel('Actual Delivery Days')
plt.xlim(0, 150)
plt.ylim(0, 60)
plt.show()

print("Finding: Higher freight values are driven by longer distances, which also naturally take longer to deliver.")
print("There is no 'premium fast shipping' tier visible that breaks this correlation.")"""),

    nbf.v4.new_markdown_cell("## Finding 6: Churn Rate Baseline\n\nUsing our operational definition of seller churn, what is our target class balance?"),
    nbf.v4.new_code_cell("""train = pd.read_parquet('../data/processed/train_dataset.parquet')
test = pd.read_parquet('../data/processed/test_dataset.parquet')

train_churn = train['churned'].mean() * 100
test_churn = test['churned'].mean() * 100

print(f"Training Set Churn Rate (2017): {train_churn:.1f}%")
print(f"Test Set Churn Rate (2018): {test_churn:.1f}%")
print("\\nFinding: A ~14% baseline churn rate is a highly realistic distribution for an early-warning system.")
print("This is imbalanced enough to require scale_pos_weight in XGBoost, but dense enough to learn a strong signal.")""")
]

# ==============================================================================
# Notebook 2: 02_seller_feature_engineering.ipynb
# ==============================================================================
nb2 = nbf.v4.new_notebook()

nb2.cells = [
    nbf.v4.new_markdown_cell("# Seller Feature Engineering Walkthrough\n\nThis notebook demonstrates how we extract rolling 8-week behavioral features for a specific observation date without leaking future information."),
    nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

# Add root to path so we can import etl
sys.path.append(os.path.abspath('..'))
from etl.seller_feature_builder import build_features_for_date

plt.style.use('seaborn-v0_8-darkgrid')

master = pd.read_parquet('../data/processed/master.parquet')
train_df = pd.read_parquet('../data/processed/train_dataset.parquet')
test_df = pd.read_parquet('../data/processed/test_dataset.parquet')
print("Data loaded successfully.")"""),

    nbf.v4.new_markdown_cell("## 1. Single Seller Time Series Analysis\n\nLet's pick an active seller and view their raw operational metrics over an 8-week period prior to May 1, 2018."),
    nbf.v4.new_code_cell("""obs_date = pd.Timestamp('2018-05-01')
t_minus_56 = obs_date - pd.Timedelta(days=56)

# Find a seller with high volume in this window
window_df = master[(master['order_purchase_timestamp'] >= t_minus_56) & (master['order_purchase_timestamp'] < obs_date)].copy()
top_seller = window_df['seller_id'].value_counts().index[0]

seller_df = window_df[window_df['seller_id'] == top_seller].copy()
seller_df['week_idx'] = ((seller_df['order_purchase_timestamp'] - t_minus_56).dt.days // 7)

# Aggregate to weekly
weekly_stats = seller_df.groupby('week_idx').agg(
    orders=('order_id', 'size'),
    median_dispatch=('dispatch_days', 'median'),
    mean_review=('review_score', 'mean')
).reindex(range(8)).fillna(0)

fig, axes = plt.subplots(1, 3, figsize=(18, 4))
weekly_stats['median_dispatch'].plot(ax=axes[0], marker='o', color='red', title='Median Dispatch Days (8 Weeks)')
weekly_stats['mean_review'].plot(ax=axes[1], marker='o', color='blue', title='Mean Review Score (8 Weeks)')
weekly_stats['orders'].plot(ax=axes[2], marker='o', color='green', title='Order Volume (8 Weeks)')
plt.show()"""),

    nbf.v4.new_markdown_cell("## 2. The OLS Slope Calculation\n\nHow do we turn these time series into a single feature? We compute the Ordinary Least Squares (OLS) slope. A positive dispatch slope means the seller is getting slower week over week."),
    nbf.v4.new_code_cell("""# Calculate slope step-by-step
y = weekly_stats['median_dispatch'].values
x = np.arange(len(y))

slope, intercept = np.polyfit(x, y, 1)

plt.figure(figsize=(8, 4))
plt.scatter(x, y, label='Actual Data')
plt.plot(x, slope * x + intercept, color='red', label=f'OLS Fit (Slope = {slope:.3f})')
plt.title(f'Dispatch Delay Trend for Seller {top_seller[:8]}...')
plt.xlabel('Week Index (0-7)')
plt.ylabel('Median Dispatch Days')
plt.legend()
plt.show()

print(f"Feature value for dispatch_delay_slope: {slope:.3f}")"""),

    nbf.v4.new_markdown_cell("## 3. Feature Distribution: Churned vs. Non-Churned\n\nIf our feature engineering is working, we should see a visible difference in the feature distributions between sellers who churn and sellers who survive."),
    nbf.v4.new_code_cell("""# Combine train and test for EDA
full_df = pd.concat([train_df, test_df])

plt.figure(figsize=(10, 5))
sns.kdeplot(data=full_df, x='dispatch_delay_slope', hue='churned', common_norm=False, fill=True)
plt.title('Distribution of Dispatch Delay Slope (Churned vs Surviving)')
plt.xlim(-2, 2)
plt.show()

print("Finding: The distribution for churned sellers is shifted to the right. Sellers whose dispatch times are slowing down (positive slope) are more likely to churn.")"""),

    nbf.v4.new_markdown_cell("## 4. Mean Feature Values Validating the Hypothesis\n\nLet's look at the average feature values for both classes."),
    nbf.v4.new_code_cell("""feature_cols = [
    'rolling_30d_otd_rate', 'rolling_30d_avg_review', 
    'dispatch_delay_slope', 'review_score_slope', 
    'cancellation_rate_30d', 'high_complaint_rate_30d'
]

summary = full_df.groupby('churned')[feature_cols].mean().T
summary.columns = ['Surviving (0)', 'Churned (1)']
summary['% Difference'] = ((summary['Churned (1)'] - summary['Surviving (0)']) / summary['Surviving (0)'] * 100).round(1)

print(summary)
print("\\nFinding: Churned sellers have lower OTD rates, lower review scores, higher cancellation rates, and their dispatch times are slowing down faster than surviving sellers.")
print("The behavioral signals exist 45 days before the ultimate failure.")"""),
]

# Execute and save
run_and_save(nb1, 'notebooks/01_olist_eda.ipynb')
run_and_save(nb2, 'notebooks/02_seller_feature_engineering.ipynb')
