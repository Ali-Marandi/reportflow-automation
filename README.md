# ReportFlow Automation 🚀

**ReportFlow** is a professional-grade Python tool for automated financial reporting. It enables reliable ingestion of financial data from multiple sources (local files and remote URLs), ensures data integrity via SHA256 provenance, and generates standardized reports in HTML, CSV, and JSON formats.

## Key Features

- 🛠 **Multi-Source Ingestion**: Support for local CSV/JSON files and remote HTTP/HTTPS endpoints.
- 🛡 **Data Provenance**: Every record is tracked back to its source with SHA256 checksums and retrieval timestamps.
- 🔄 **Reliability**: Built-in retries and configurable timeouts for network sources.
- 📊 **Professional Reporting**: Generates beautiful, responsive HTML reports using Bootstrap and Jinja2.
- 🧹 **Smart Normalization**: Automatic cleaning and type conversion of financial data using Pandas.
- 🏗 **Config-Driven**: Define your reporting pipeline in a simple JSON configuration file.

## Installation

```bash
pip install reportflow-automation
```

## Quick Start

1. Create a `config.json` file:

```json
{
  "title": "Monthly Market Analysis",
  "sources": [
    {
      "name": "Market Rates",
      "type": "url",
      "url": "https://api.example.com/rates.csv",
      "format": "csv"
    },
    {
      "name": "Inventory Data",
      "type": "file",
      "path": "./data/inventory.json",
      "format": "json"
    }
  ],
  "output_formats": ["html", "csv", "json"]
}
```

2. Run the tool:

```bash
reportflow config.json --output ./reports
```

## Development

### Requirements
- Python 3.10+
- Pandas, Pydantic, Jinja2, Requests, Click

### Running Tests
```bash
python -m unittest discover tests
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author
**Ali Marandi** - [Marandi@outlook.com](mailto:Marandi@outlook.com)
