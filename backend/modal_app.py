"""
MoveH API - Modal Deployment

Deploy the MoveH fact-checking API to Modal with persistent storage volume.

Usage:
    # Development mode (live reload)
    modal serve modal_app.py

    # Production deployment
    modal deploy modal_app.py

    # Create volume first (one-time setup)
    modal volume create moveh-storage
"""

import modal
from pathlib import Path

# Define the Modal app
app = modal.App("moveh-api")

# Create a persistent volume for PDF storage
volume = modal.Volume.from_name("moveh-storage", create_if_missing=True)

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

# Build the image step by step
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "fastapi[standard]>=0.122.0",
    "uvicorn>=0.38.0",
    "langchain>=1.1.0",
    "langchain-core>=1.1.0",
    "langchain-google-genai>=2.0.0",
    "langgraph>=0.2.0",
    "pydantic>=2.12.5",
    "python-dotenv>=1.2.1",
    "reportlab>=4.4.5",
    "rich>=14.2.0",
    "tavily-python>=0.5.0",
    "aptos-sdk>=0.7.0",
)

# Add local files/directories if they exist
if (SCRIPT_DIR / "agents").exists():
    print("✓ Adding agents directory")
    image = image.add_local_dir("agents", "/app/agents")
else:
    print("⚠️  Warning: 'agents' directory not found")

if (SCRIPT_DIR / "blockchain").exists():
    print("✓ Adding blockchain directory")
    image = image.add_local_dir("blockchain", "/app/blockchain")
else:
    print("⚠️  Warning: 'blockchain' directory not found")

if (SCRIPT_DIR / "api.py").exists():
    print("✓ Adding api.py")
    image = image.add_local_file("api.py", "/app/api.py")
else:
    print("⚠️  Warning: 'api.py' file not found")

# Volume mount path (must match storage directory in the app)
VOLUME_PATH = "/app/storage"


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
    secrets=[modal.Secret.from_name("moveh-secrets")],
    timeout=600,  # 10 minute timeout for long verifications
    memory=2048,  # 2GB memory
    cpu=2.0,  # 2 CPU cores
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def fastapi_app():
    """
    Serve the MoveH FastAPI application.
    
    The ASGI app is returned directly for Modal to serve.
    Volume is mounted at /app/storage for persistent PDF storage.
    """
    import sys
    import os
    
    # Add app directory to path for imports
    sys.path.insert(0, "/app")
    
    # Set storage directory to use the mounted volume
    os.environ["STORAGE_DIR"] = VOLUME_PATH
    
    # Ensure storage directory exists
    os.makedirs(VOLUME_PATH, exist_ok=True)
    
    # Import and return the FastAPI app
    from api import app as fastapi_application
    
    # Update the Shelby storage directory to use the volume
    from agents.shelby import Shelby
    
    # Patch the storage directory in the API module
    import api
    api.STORAGE_DIR = VOLUME_PATH
    api.shelby = Shelby(storage_dir=VOLUME_PATH)
    
    # Re-mount the static files directory with the new path
    from fastapi.staticfiles import StaticFiles
    
    # Remove existing mount if present and remount with volume path
    for route in list(fastapi_application.routes):
        if hasattr(route, 'path') and route.path == "/download":
            fastapi_application.routes.remove(route)
    
    fastapi_application.mount("/download", StaticFiles(directory=VOLUME_PATH), name="download")
    
    return fastapi_application


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
)
def cleanup_old_reports(days: int = 7):
    """
    Utility function to clean up old reports from the storage volume.
    
    Usage:
        modal run modal_app.py::cleanup_old_reports --days 7
    """
    import os
    import time
    
    cutoff = time.time() - (days * 24 * 60 * 60)
    deleted = 0
    
    for filename in os.listdir(VOLUME_PATH):
        filepath = os.path.join(VOLUME_PATH, filename)
        if os.path.isfile(filepath):
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                deleted += 1
    
    # Commit changes to volume
    volume.commit()
    
    return f"Deleted {deleted} files older than {days} days"


@app.function(
    image=image,
    volumes={VOLUME_PATH: volume},
)
def list_reports():
    """
    List all reports stored in the volume.
    
    Usage:
        modal run modal_app.py::list_reports
    """
    import os
    
    files = []
    for filename in os.listdir(VOLUME_PATH):
        filepath = os.path.join(VOLUME_PATH, filename)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append({
                "name": filename,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
    
    return files


@app.local_entrypoint()
def main():
    """
    Local entrypoint for testing.
    
    Usage:
        modal run modal_app.py
    """
    print("MoveH API Modal Deployment")
    print("=" * 40)
    print()
    print("Commands:")
    print("  modal serve modal_app.py     - Start development server with live reload")
    print("  modal deploy modal_app.py    - Deploy to production")
    print()
    print("Utility functions:")
    print("  modal run modal_app.py::list_reports")
    print("  modal run modal_app.py::cleanup_old_reports --days 7")
    print()
    print("Volume: moveh-storage")
    print("Mount path: /app/storage")