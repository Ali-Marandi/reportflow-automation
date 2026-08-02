import json
import os

def add_data_source(config_path, name, source_type, location, data_format="csv"):
    """
    Adds or updates a data source in the configuration file.
    """
    if not os.path.exists(config_path):
        # Create a basic config if it doesn't exist
        config = {"title": "Automated Report", "sources": [], "output_formats": ["html", "csv", "json"]}
    else:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

    new_source = {
        "name": name,
        "type": source_type,
        "format": data_format
    }

    if source_type == "file":
        new_source["path"] = location
    else:
        new_source["url"] = location

    # Update if exists, otherwise append
    config["sources"] = [s for s in config["sources"] if s["name"] != name]
    config["sources"].append(new_source)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    return config

if __name__ == "__main__":
    # Example usage
    add_data_source("config.json", "Example API", "url", "https://api.example.com/data", "json")
    print("Source added to config.json")
