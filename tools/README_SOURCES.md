# Data Source Management Tool

Easily add or update data sources in your `config.json` file programmatically.

## Usage
Use the `add_data_source` function to append new file-based or URL-based sources.

```python
from manage_data_sources import add_data_source

add_data_source(
    config_path="config.json",
    name="Live Market Data",
    source_type="url",
    location="https://api.finance.com/v1/latest",
    data_format="json"
)
```
