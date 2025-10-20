# CFO Reporting API - Comprehensive Documentation

## Overview

This document provides comprehensive documentation for all CFO reporting endpoints available in the DeltaCFOAgent system. The reporting API provides executive-level financial insights and analysis tools for comprehensive CFO dashboards.

**Base URL**: `http://localhost:5002` (development) or your deployed URL

---

## New CFO Reports (Recently Implemented)

### 1. Cash Flow Statement

**Endpoint**: `/api/reports/cash-flow-statement`

**Method**: `GET`

**Description**: Comprehensive Cash Flow Statement that classifies transactions into Operating, Investing, and Financing activities following standard accounting practices.

**Parameters**:
- `start_date` (optional): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format
- `period` (optional): 'monthly', 'quarterly', 'yearly', 'all_time' (default: 'all_time')
- `entity` (optional): Filter by specific business entity

**Response Structure**:
```json
{
  "success": true,
  "statement": {
    "statement_type": "CashFlowStatement",
    "statement_name": "Cash Flow Statement - All Time",
    "period": {
      "type": "all_time",
      "start_date": "2020-01-01",
      "end_date": "2025-10-16",
      "entity_filter": "All entities"
    },
    "operating_activities": {
      "total": 1234567.89,
      "categories": [
        {
          "category": "Revenue",
          "amount": 5000000.00,
          "count": 150
        }
      ],
      "description": "Cash flows from core business operations"
    },
    "investing_activities": {
      "total": -500000.00,
      "categories": [...],
      "description": "Cash flows from investments and capital expenditures"
    },
    "financing_activities": {
      "total": 250000.00,
      "categories": [...],
      "description": "Cash flows from debt, equity, and dividends"
    },
    "summary": {
      "beginning_cash_balance": 1000000.00,
      "net_cash_from_operating": 1234567.89,
      "net_cash_from_investing": -500000.00,
      "net_cash_from_financing": 250000.00,
      "net_change_in_cash": 984567.89,
      "ending_cash_balance": 1984567.89
    },
    "key_metrics": {
      "operating_cash_flow_ratio": 4.94,
      "free_cash_flow": 734567.89,
      "cash_flow_adequacy": 2.47
    },
    "generated_at": "2025-10-16T10:30:00",
    "generation_time_ms": 150
  }
}
```

**Example Usage**:
```bash
curl "http://localhost:5002/api/reports/cash-flow-statement?period=yearly"
```

---

### 2. Budget vs Actual Analysis

**Endpoint**: `/api/reports/budget-vs-actual`

**Methods**: `GET`, `POST`

**Description**: Compares actual financial performance against budget targets. Budget can be based on historical averages, growth projections, or fixed targets.

**Parameters**:
- `period` (optional): 'monthly', 'quarterly', 'yearly' (default: 'monthly')
- `budget_method` (optional): 'historical_avg', 'fixed_target', 'growth_based' (default: 'historical_avg')
- `growth_rate` (optional): Growth rate percentage for growth-based budgets (default: 10)
- `entity` (optional): Filter by specific business entity
- `budget_data` (optional): JSON object with budget targets (for fixed_target method)

**Response Structure**:
```json
{
  "success": true,
  "report": {
    "report_type": "BudgetVsActual",
    "report_name": "Budget vs Actual Analysis - Monthly",
    "period": {
      "type": "monthly",
      "start_date": "2025-09-16",
      "end_date": "2025-10-16",
      "entity_filter": "All entities"
    },
    "budget_method": "historical_avg",
    "variance_analysis": [
      {
        "category": "Revenue",
        "revenue": {
          "actual": 250000.00,
          "budget": 220000.00,
          "variance": 30000.00,
          "variance_percent": 13.64,
          "status": "favorable"
        },
        "expenses": {
          "actual": 75000.00,
          "budget": 80000.00,
          "variance": -5000.00,
          "variance_percent": -6.25,
          "status": "favorable"
        },
        "transaction_count": 45
      }
    ],
    "summary": {
      "revenue": {
        "actual": 250000.00,
        "budget": 220000.00,
        "variance": 30000.00,
        "variance_percent": 13.64,
        "achievement_rate": 113.64
      },
      "expenses": {
        "actual": 75000.00,
        "budget": 80000.00,
        "variance": -5000.00,
        "variance_percent": -6.25,
        "achievement_rate": 93.75
      },
      "net_income": {
        "actual": 175000.00,
        "budget": 140000.00,
        "variance": 35000.00,
        "variance_percent": 25.00
      }
    },
    "key_insights": {
      "revenue_performance": "Above Target",
      "expense_control": "Under Budget",
      "overall_performance": "Exceeding Expectations"
    }
  }
}
```

**Example Usage**:
```bash
# GET request with historical average budget
curl "http://localhost:5002/api/reports/budget-vs-actual?period=monthly&budget_method=historical_avg"

# POST request with growth-based budget
curl -X POST http://localhost:5002/api/reports/budget-vs-actual \
  -H "Content-Type: application/json" \
  -d '{"period": "quarterly", "budget_method": "growth_based", "growth_rate": 15}'
```

---

### 3. Trend Analysis with Forecasting

**Endpoint**: `/api/reports/trend-analysis`

**Method**: `GET`

**Description**: Multi-period trend analysis with period-over-period comparisons, growth rates, and optional forecasting using historical data patterns.

**Parameters**:
- `metric` (optional): 'revenue', 'expenses', 'profit', 'cash_flow', 'all' (default: 'all')
- `granularity` (optional): 'monthly', 'quarterly', 'yearly' (default: 'monthly')
- `periods` (optional): Number of historical periods to analyze (default: 12)
- `entity` (optional): Filter by specific business entity
- `include_forecast` (optional): Include forecast for future periods (true/false) (default: false)

**Response Structure**:
```json
{
  "success": true,
  "analysis": {
    "report_type": "TrendAnalysis",
    "report_name": "Trend Analysis - Monthly (12 periods)",
    "parameters": {
      "metric": "all",
      "granularity": "monthly",
      "periods_analyzed": 12,
      "entity_filter": "All entities",
      "forecast_included": true
    },
    "period_data": [
      {
        "period": "2024-10-01T00:00:00",
        "revenue": 250000.00,
        "expenses": 75000.00,
        "net_profit": 175000.00,
        "transaction_count": 45,
        "avg_revenue_transaction": 5555.56,
        "avg_expense_transaction": 1666.67,
        "growth_rates": {
          "revenue": 8.5,
          "expenses": -3.2,
          "profit": 15.7
        },
        "profit_margin": 70.0
      }
    ],
    "forecast": [
      {
        "period": "Forecast +1",
        "revenue": 260000.00,
        "expenses": 74000.00,
        "net_profit": 186000.00,
        "is_forecast": true
      }
    ],
    "summary_statistics": {
      "total_revenue": 3000000.00,
      "total_expenses": 900000.00,
      "total_profit": 2100000.00,
      "average_revenue_per_period": 250000.00,
      "average_expenses_per_period": 75000.00,
      "average_profit_per_period": 175000.00,
      "average_revenue_growth": 7.5,
      "average_expense_growth": -2.1,
      "average_profit_growth": 12.8
    },
    "trend_indicators": {
      "revenue_trend": "increasing",
      "expense_trend": "stable",
      "profit_trend": "increasing",
      "overall_health": "improving"
    },
    "key_insights": [
      "Revenue is increasing with average 7.5% growth per period",
      "Expenses are stable with average 2.1% decrease per period",
      "Profit trend is increasing with average 12.8% change per period",
      "Overall financial health is increasing"
    ]
  }
}
```

**Example Usage**:
```bash
# Basic trend analysis
curl "http://localhost:5002/api/reports/trend-analysis?granularity=monthly&periods=12"

# With forecasting
curl "http://localhost:5002/api/reports/trend-analysis?granularity=monthly&periods=12&include_forecast=true"
```

---

### 4. Risk Assessment Dashboard

**Endpoint**: `/api/reports/risk-assessment`

**Method**: `GET`

**Description**: Comprehensive risk assessment evaluating financial risks across liquidity, solvency, operational, and market risk categories with actionable recommendations.

**Parameters**:
- `entity` (optional): Filter by specific business entity
- `period` (optional): 'monthly', 'quarterly', 'yearly' (default: 'yearly')

**Response Structure**:
```json
{
  "success": true,
  "assessment": {
    "report_type": "RiskAssessment",
    "report_name": "Risk Assessment Dashboard - Yearly",
    "period": {
      "start_date": "2024-10-16",
      "end_date": "2025-10-16",
      "entity_filter": "All entities"
    },
    "overall_risk": {
      "score": 78.5,
      "level": "low",
      "rating": "Good"
    },
    "risk_categories": {
      "liquidity": {
        "score": 85.0,
        "level": "low",
        "metrics": {
          "current_ratio": 1.70,
          "months_of_runway": 8.5,
          "monthly_burn_rate": 75000.00
        }
      },
      "solvency": {
        "score": 72.0,
        "level": "low",
        "metrics": {
          "debt_to_income_ratio": 0.28,
          "expense_coverage": 357.14
        }
      },
      "operational": {
        "score": 75.0,
        "level": "low",
        "metrics": {
          "concentration_risk": 25.0,
          "largest_inflow": 500000.00,
          "largest_outflow": 150000.00
        }
      },
      "market": {
        "score": 82.0,
        "level": "low",
        "metrics": {
          "cash_flow_volatility": 45000.00,
          "volatility_ratio": 0.36
        }
      }
    },
    "recommendations": [
      {
        "category": "Overall",
        "severity": "low",
        "recommendation": "Financial health is strong. Maintain current practices and continue monitoring.",
        "action_items": [
          "Continue regular financial monitoring",
          "Maintain healthy cash reserves",
          "Explore growth opportunities",
          "Review and optimize operational efficiency"
        ]
      }
    ],
    "financial_summary": {
      "total_revenue": 3000000.00,
      "total_expenses": 900000.00,
      "net_position": 2100000.00,
      "transaction_count": 540,
      "active_months": 12
    }
  }
}
```

**Example Usage**:
```bash
curl "http://localhost:5002/api/reports/risk-assessment?period=yearly"
```

---

### 5. Working Capital Analysis

**Endpoint**: `/api/reports/working-capital`

**Method**: `GET`

**Description**: Analyzes current assets, current liabilities, and working capital trends to assess short-term financial health and operational efficiency.

**Parameters**:
- `entity` (optional): Filter by specific business entity
- `period` (optional): 'monthly', 'quarterly', 'yearly' (default: 'yearly')

**Response Structure**:
```json
{
  "success": true,
  "report": {
    "report_type": "WorkingCapitalAnalysis",
    "report_name": "Working Capital Analysis - Yearly",
    "period": {
      "current": {
        "start_date": "2024-10-16",
        "end_date": "2025-10-16"
      },
      "previous": {
        "start_date": "2023-10-16",
        "end_date": "2024-10-16"
      },
      "entity_filter": "All entities"
    },
    "current_period": {
      "current_assets": 1500000.00,
      "current_liabilities": 800000.00,
      "working_capital": 700000.00,
      "current_ratio": 1.88,
      "quick_ratio": 1.13,
      "working_capital_ratio": 46.67
    },
    "previous_period": {
      "current_assets": 1200000.00,
      "current_liabilities": 750000.00,
      "working_capital": 450000.00,
      "current_ratio": 1.60
    },
    "changes": {
      "working_capital_change": 250000.00,
      "working_capital_change_percent": 55.56,
      "current_ratio_change": 0.28,
      "trend": "improving"
    },
    "monthly_trend": [
      {
        "month": "2024-10-01T00:00:00",
        "current_assets": 125000.00,
        "current_liabilities": 65000.00,
        "working_capital": 60000.00,
        "current_ratio": 1.92
      }
    ],
    "health_assessment": {
      "status": "Good",
      "color": "green",
      "score": 93.75
    },
    "key_metrics": {
      "days_working_capital": 26.3,
      "working_capital_turnover": 2.14,
      "asset_efficiency": 187.5
    },
    "insights": [
      {
        "type": "success",
        "message": "Current ratio of 1.88 is within healthy range (1.0 - 3.0).",
        "recommendation": "Maintain current working capital management practices."
      },
      {
        "type": "success",
        "message": "Working capital increased by $250,000.00 (55.6%) compared to previous period.",
        "recommendation": "Continue current growth trajectory while maintaining operational efficiency."
      }
    ]
  }
}
```

**Example Usage**:
```bash
curl "http://localhost:5002/api/reports/working-capital?period=yearly"
```

---

### 6. Financial Forecast & Projections

**Endpoint**: `/api/reports/financial-forecast`

**Method**: `GET`

**Description**: AI-powered financial forecast using historical data and trend analysis to project future financial performance. Employs linear regression, moving averages, or weighted forecasting methods.

**Parameters**:
- `forecast_periods` (optional): Number of periods to forecast (default: 6)
- `granularity` (optional): 'monthly', 'quarterly' (default: 'monthly')
- `entity` (optional): Filter by specific business entity
- `historical_periods` (optional): Number of historical periods to analyze (default: 12)
- `method` (optional): 'linear', 'moving_average', 'weighted' (default: 'linear')

**Response Structure**:
```json
{
  "success": true,
  "forecast": {
    "report_type": "FinancialForecast",
    "report_name": "Financial Forecast - Monthly (6 periods)",
    "parameters": {
      "forecast_periods": 6,
      "historical_periods": 12,
      "granularity": "monthly",
      "method": "linear",
      "entity_filter": "All entities"
    },
    "historical_data": [
      {
        "period": "2024-10-01T00:00:00",
        "revenue": 250000.00,
        "expenses": 75000.00,
        "net_profit": 175000.00,
        "transaction_count": 45,
        "is_historical": true
      }
    ],
    "forecast_data": [
      {
        "period": "Forecast +1",
        "revenue": 260000.00,
        "expenses": 74000.00,
        "net_profit": 186000.00,
        "is_forecast": true,
        "confidence": 90.0
      },
      {
        "period": "Forecast +2",
        "revenue": 270000.00,
        "expenses": 73000.00,
        "net_profit": 197000.00,
        "is_forecast": true,
        "confidence": 85.0
      }
    ],
    "forecast_summary": {
      "projected_revenue": 1590000.00,
      "projected_expenses": 432000.00,
      "projected_profit": 1158000.00,
      "average_confidence": 82.5,
      "forecast_accuracy_score": 87.3
    },
    "methodology": {
      "method_used": "linear",
      "description": "Linear regression based on historical trends",
      "limitations": [
        "Forecasts assume continuation of historical trends",
        "External factors and market changes not accounted for",
        "Confidence decreases for longer-term projections",
        "Should be used as guidance, not definitive predictions"
      ]
    },
    "key_insights": [
      "Based on 12 periods of historical data",
      "Projected monthly revenue: $265,000.00",
      "Forecast confidence: 82.5%",
      "Accuracy indicator: 87.3%"
    ]
  }
}
```

**Example Usage**:
```bash
# Linear forecast
curl "http://localhost:5002/api/reports/financial-forecast?forecast_periods=6&method=linear"

# Moving average forecast
curl "http://localhost:5002/api/reports/financial-forecast?forecast_periods=3&method=moving_average"

# Weighted forecast with growth
curl "http://localhost:5002/api/reports/financial-forecast?forecast_periods=6&method=weighted&granularity=quarterly"
```

---

## Existing CFO Reports (Reference)

### Income Statement (P&L)
- **Endpoint**: `/api/reports/income-statement`
- **Simple Version**: `/api/reports/income-statement/simple`

### Balance Sheet
- **Endpoint**: `/api/reports/balance-sheet/simple`

### CFO Financial Ratios & KPIs
- **Endpoint**: `/api/reports/cfo-financial-ratios`

### CFO Executive Summary
- **Endpoint**: `/api/reports/cfo-executive-summary`

### Cash Dashboard
- **Endpoint**: `/api/reports/cash-dashboard`

### Cash Trend
- **Endpoint**: `/api/reports/cash-trend`

### Monthly P&L
- **Endpoint**: `/api/reports/monthly-pl`

### Entity Performance
- **Endpoint**: `/api/reports/entity-performance`

### Entity Summary
- **Endpoint**: `/api/reports/entity-summary`

### Sankey Flow Visualization
- **Endpoint**: `/api/reports/sankey-flow`

---

## Common Response Format

All endpoints follow a consistent response format:

**Success Response**:
```json
{
  "success": true,
  "statement/report/forecast": {
    // Report-specific data
  }
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

---

## Performance Considerations

- All reports include a `generation_time_ms` field showing how long the query took
- Simple endpoints (using direct SQL) are typically faster than complex ones
- For large datasets, consider using date range filters to improve performance
- Entity filters can significantly improve query performance

---

## Best Practices

1. **Date Ranges**: Always specify date ranges for production use to optimize query performance
2. **Entity Filtering**: Use entity filters when analyzing specific business units
3. **Caching**: Consider caching report results on the frontend for frequently accessed reports
4. **Error Handling**: Always check the `success` field before processing report data
5. **Forecasting**: Use multiple forecasting methods and compare results for better accuracy
6. **Risk Assessment**: Run risk assessments regularly (at least quarterly) for proactive management

---

## Integration Examples

### JavaScript/React Example
```javascript
async function fetchCashFlowStatement(period = 'yearly') {
  try {
    const response = await fetch(
      `http://localhost:5002/api/reports/cash-flow-statement?period=${period}`
    );
    const data = await response.json();

    if (data.success) {
      return data.statement;
    } else {
      throw new Error(data.error);
    }
  } catch (error) {
    console.error('Failed to fetch cash flow statement:', error);
    throw error;
  }
}
```

### Python Example
```python
import requests

def get_risk_assessment(period='yearly', entity=None):
    params = {'period': period}
    if entity:
        params['entity'] = entity

    response = requests.get(
        'http://localhost:5002/api/reports/risk-assessment',
        params=params
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data['assessment']

    raise Exception('Failed to fetch risk assessment')
```

---

## Support and Troubleshooting

### Common Issues

1. **Empty Data**: Ensure there are transactions in the database for the specified period
2. **Slow Performance**: Use date range filters and entity filters to reduce query scope
3. **Missing Forecasts**: Forecast generation requires at least 3 historical periods
4. **High Risk Scores**: Review the recommendations section for specific action items

### Logging

All endpoints log errors with detailed stack traces. Check the Flask application logs for debugging:

```bash
cd web_ui
python app_db.py
```

---

## Version History

- **v1.0** (2025-10-16): Initial implementation of 5 new CFO reports
  - Cash Flow Statement
  - Budget vs Actual Analysis
  - Trend Analysis with Forecasting
  - Risk Assessment Dashboard
  - Working Capital Analysis
  - Financial Forecast & Projections

---

## Future Enhancements

Planned improvements for future versions:

1. PDF/Excel export functionality for all reports
2. Email scheduled reports
3. Real-time alerts based on risk thresholds
4. Machine learning-based forecasting models
5. Comparative analysis across multiple entities
6. Custom KPI tracking and visualization
7. Integration with external accounting systems

---

## License

Copyright © 2025 Delta Mining. All rights reserved.
