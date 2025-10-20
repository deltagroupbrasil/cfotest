# CFO Reports - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Prerequisites
- Flask server running on port 5002
- PostgreSQL database with transaction data
- Python 3.8+ environment

### Start the Server
```bash
cd web_ui
python app_db.py
```

Server should start on `http://localhost:5002`

---

## 📊 Available Reports

### 1. Cash Flow Statement
```bash
# Get yearly cash flow
curl "http://localhost:5002/api/reports/cash-flow-statement?period=yearly"
```

**Key Data**: Operating, Investing, and Financing cash flows

---

### 2. Budget vs Actual
```bash
# Monthly variance with historical budget
curl "http://localhost:5002/api/reports/budget-vs-actual?period=monthly&budget_method=historical_avg"
```

**Key Data**: Variance analysis, achievement rates, performance status

---

### 3. Trend Analysis
```bash
# 12-month trend with forecast
curl "http://localhost:5002/api/reports/trend-analysis?periods=12&include_forecast=true"
```

**Key Data**: Growth rates, trend directions, future projections

---

### 4. Risk Assessment
```bash
# Comprehensive risk evaluation
curl "http://localhost:5002/api/reports/risk-assessment?period=yearly"
```

**Key Data**: Risk scores, recommendations, health metrics

---

### 5. Working Capital
```bash
# Current working capital status
curl "http://localhost:5002/api/reports/working-capital?period=yearly"
```

**Key Data**: Current ratio, working capital trends, liquidity metrics

---

### 6. Financial Forecast
```bash
# 6-month linear forecast
curl "http://localhost:5002/api/reports/financial-forecast?forecast_periods=6&method=linear"
```

**Key Data**: Future projections, confidence scores, historical trends

---

## 🧪 Testing

### Run All Tests
```bash
python test_new_cfo_reports.py
```

### Test Individual Endpoint
```python
import requests

response = requests.get('http://localhost:5002/api/reports/cash-flow-statement?period=monthly')
print(response.json())
```

---

## 📖 Common Parameters

### Period Filters
- `period=monthly` - Last 30 days
- `period=quarterly` - Last 90 days
- `period=yearly` - Last 365 days
- `period=all_time` - All available data

### Date Ranges
- `start_date=2024-01-01`
- `end_date=2024-12-31`

### Entity Filtering
- `entity=Delta LLC` - Filter by specific business entity

---

## 🔍 Response Format

All endpoints return JSON in this format:

```json
{
  "success": true,
  "statement/report/forecast": {
    "report_type": "...",
    "report_name": "...",
    "generated_at": "2025-10-16T10:30:00",
    "generation_time_ms": 150,
    // ... report-specific data
  }
}
```

---

## ⚡ Performance Tips

1. **Use Date Filters**: Improves query speed significantly
   ```bash
   ?start_date=2025-01-01&end_date=2025-10-16
   ```

2. **Entity Filtering**: Reduces data scope
   ```bash
   ?entity=Delta+LLC
   ```

3. **Limit Forecast Periods**: Start with 3-6 periods
   ```bash
   ?forecast_periods=6
   ```

---

## 🐛 Troubleshooting

### Empty Data
- **Problem**: Report shows no data
- **Solution**: Check if transactions exist for the period
- **Command**: `SELECT COUNT(*) FROM transactions WHERE date >= '2024-01-01';`

### Slow Response
- **Problem**: Query takes too long
- **Solution**: Add date range and entity filters
- **Example**: `?start_date=2025-01-01&entity=Delta+LLC`

### Forecast Not Generated
- **Problem**: Forecast data is empty
- **Solution**: Need at least 3 historical periods
- **Check**: Ensure sufficient historical data exists

### Server Not Running
- **Problem**: Connection refused
- **Solution**: Start Flask server
- **Command**: `cd web_ui && python app_db.py`

---

## 📚 Full Documentation

For complete API documentation, see:
- **`CFO_REPORTS_DOCUMENTATION.md`** - Complete API reference
- **`IMPLEMENTATION_SUMMARY.md`** - Technical details
- **`CLAUDE.md`** - Project guidelines

---

## 🎯 Quick Reference Table

| Report | Endpoint | Key Purpose | Best For |
|--------|----------|-------------|----------|
| Cash Flow | `/api/reports/cash-flow-statement` | Cash movement analysis | Liquidity planning |
| Budget vs Actual | `/api/reports/budget-vs-actual` | Performance tracking | Accountability |
| Trend Analysis | `/api/reports/trend-analysis` | Historical patterns | Strategic planning |
| Risk Assessment | `/api/reports/risk-assessment` | Financial health | Risk management |
| Working Capital | `/api/reports/working-capital` | Short-term liquidity | Operations |
| Forecast | `/api/reports/financial-forecast` | Future projections | Budgeting |

---

## 💡 Pro Tips

1. **Start with Risk Assessment**: Gives overall health snapshot
2. **Use Trend Analysis for Planning**: Includes forecasting capability
3. **Monitor Working Capital Monthly**: Early warning for liquidity issues
4. **Compare Budget Methods**: Try all three budget calculation approaches
5. **Save Forecasts**: Track forecast accuracy over time

---

## 🔗 Quick Links

- **Test Suite**: `test_new_cfo_reports.py`
- **API Documentation**: `CFO_REPORTS_DOCUMENTATION.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **Project Guidelines**: `CLAUDE.md`

---

## 🆘 Getting Help

1. Check logs: `web_ui/app_db.py` output
2. Read documentation: `CFO_REPORTS_DOCUMENTATION.md`
3. Review test cases: `test_new_cfo_reports.py`
4. Check database: Ensure transactions table has data

---

**Last Updated**: October 16, 2025
**Version**: 1.0
