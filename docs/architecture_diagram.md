# AI Supply Chain Control Tower Architecture

```text
                         User
                          │
                          ▼
                Streamlit Dashboard
                          │
                          ▼
                     FastAPI API
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   Risk Engine      Feature Analytics      AI Advisor
                          │
                          ▼
                Machine Learning Models
                          │
                          ▼
                    Spark Processing
                          │
                          ▼
                     Kafka Streaming
                          │
                          ▼
                  Supply Chain Data
```
