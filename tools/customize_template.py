import os

def create_custom_template(project_path, theme_color="#2c3e50", company_name="My Company"):
    """
    Creates a custom HTML template for reports.
    """
    template_dir = os.path.join(project_path, "custom_templates")
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{{{ title }}}}</title>
        <style>
            body {{ font-family: 'Arial', sans-serif; margin: 40px; color: #333; }}
            .header {{ background-color: {theme_color}; color: white; padding: 20px; border-radius: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .footer {{ margin-top: 30px; font-size: 0.8em; color: #777; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{company_name} - {{{{ title }}}}</h1>
            <p>Generated at: {{{{ generated_at }}}}</p>
        </div>
        <div class="content">
            {{{{ table_html | safe }}}}
        </div>
        <div class="footer">
            <p>Data verified by ReportFlow Automation. Integrity Hash: {{{{ snapshots[0].sha256 if snapshots else 'N/A' }}}}</p>
        </div>
    </body>
    </html>
    """
    
    template_path = os.path.join(template_dir, "report.html")
    with open(template_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return template_path

if __name__ == "__main__":
    # Example usage
    path = create_custom_template(".", theme_color="#e74c3c", company_name="Ali Marandi Corp")
    print(f"Template created at: {path}")
