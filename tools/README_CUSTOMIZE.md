# Template Customization Tool

This tool allows you to create custom HTML templates for your ReportFlow reports without modifying the core library.

## Usage
Import the `create_custom_template` function and provide your project path, desired theme color, and company name.

```python
from customize_template import create_custom_template

create_custom_template(
    project_path=".", 
    theme_color="#3498db", 
    company_name="My Enterprise"
)
```

This will generate a `custom_templates/report.html` file which you can then use with Jinja2 in your pipeline.
