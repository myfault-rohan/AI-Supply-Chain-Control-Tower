import os
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import DATASET_DIR
PROCESSED_DIR = os.path.join(DATASET_DIR, "processed files")

def generate_pdf_report():
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"executive_report_{datetime.now().strftime('%Y%m%d')}.pdf")
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    Story = []
    
    # 1. Cover
    Story.append(Paragraph("AI Supply Chain Control Tower", styles['Title']))
    Story.append(Paragraph(f"Executive Daily Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    Story.append(Spacer(1, 20))
    
    # Load Data
    def load_df(name):
        p = os.path.join(PROCESSED_DIR, name)
        return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
        
    health_df = load_df("supply_chain_health.csv")
    sup_df = load_df("supplier_performance.csv")
    ware_df = load_df("warehouse_utilization.csv")
    cost_df = load_df("cost_analysis.csv")
    reorder_df = load_df("reorder_recommendations.csv")
    
    # 2. Executive Summary Table
    Story.append(Paragraph("Executive Summary", styles['Heading2']))
    total_products = len(health_df)
    crit = (health_df["health_status"] == "CRITICAL").sum() if not health_df.empty else 0
    warn = (health_df["health_status"] == "WARNING").sum() if not health_df.empty else 0
    score = health_df["health_score"].mean() if not health_df.empty else 0
    
    summary_data = [
        ["Metric", "Value"],
        ["Total Products", str(total_products)],
        ["Critical Products", str(crit)],
        ["Warning Products", str(warn)],
        ["Avg Health Score", f"{score:.1f}%"]
    ]
    t = Table(summary_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    Story.append(t)
    Story.append(Spacer(1, 20))
    
    # 3. Top 5 Critical
    Story.append(Paragraph("Top 5 Critical Products", styles['Heading2']))
    if not health_df.empty:
        crit_df = health_df[health_df["health_status"] == "CRITICAL"].head(5)
        crit_data = [["Product", "Stock", "Days Until Stockout"]]
        for _, r in crit_df.iterrows():
            crit_data.append([str(r['product_id']), str(r['current_stock']), str(r['days_until_stockout'])])
        t2 = Table(crit_data)
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.darkred),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        Story.append(t2)
    Story.append(Spacer(1, 20))
    
    # 4. Supplier League Table
    Story.append(Paragraph("Supplier Performance", styles['Heading2']))
    if not sup_df.empty:
        s_df = sup_df.sort_values("reliability_score", ascending=False).head(5)
        s_data = [["Supplier", "Reliability %", "Delay Rate %"]]
        for _, r in s_df.iterrows():
            s_data.append([str(r['supplier_id']), f"{r['reliability_score']}%", f"{r['delay_rate']}%"])
        Story.append(Table(s_data, style=TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])))
    Story.append(Spacer(1, 20))
    
    # 5. Warehouses
    Story.append(Paragraph("Warehouse Utilization", styles['Heading2']))
    if not ware_df.empty:
        w_data = [["Warehouse", "Utilization %", "Status"]]
        for _, r in ware_df.iterrows():
            w_data.append([str(r['warehouse_id']), f"{r['utilization_percent']}%", str(r['status'])])
        Story.append(Table(w_data, style=TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black)])))
    Story.append(Spacer(1, 20))
    
    # 6. Cost Risk
    Story.append(Paragraph("Cost Risk Exposure", styles['Heading2']))
    if not cost_df.empty:
        total_risk = cost_df["total_cost_impact"].sum()
        Story.append(Paragraph(f"Total Financial Exposure: ${total_risk:,.2f}", styles['Normal']))
    Story.append(Spacer(1, 20))
    
    # 7. Actions
    Story.append(Paragraph("Recommended Actions", styles['Heading2']))
    if not reorder_df.empty:
        acts = reorder_df[reorder_df["stockout_risk"]].head(5)
        for _, r in acts.iterrows():
            Story.append(Paragraph(f"• {r['alert_message']}", styles['Normal']))
    Story.append(Spacer(1, 30))
    
    # Footer
    Story.append(Paragraph("Confidential — AI Supply Chain Control Tower", styles['Italic']))
    
    doc.build(Story)
    return pdf_path

if __name__ == "__main__":
    print(generate_pdf_report())
