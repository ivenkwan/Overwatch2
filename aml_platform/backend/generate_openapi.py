import json
import os
import sys

# Ensure backend root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app

def main():
    openapi_schema = app.openapi()
    
    # Resolve the destination directory: docs/ at the root of the workspace
    # Since generate_openapi.py is in aml_platform/backend, its root is 2 levels up
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_dir = os.path.join(root_dir, "docs")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "openapi.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Successfully generated OpenAPI schema at {output_path}")

if __name__ == "__main__":
    main()
