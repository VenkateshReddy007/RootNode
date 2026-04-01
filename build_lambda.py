"""
RootNode - Lambda Build Script (Step 10)
==========================================
Automates the creation of an AWS Lambda deployment package for RootNode.

Performs:
  1. Creates a clean `rootnode_deploy` directory.
  2. Copies the modular `backend` package into the deployment folder.
  3. Generates `lambda_function.py` entrypoint wrapper.
  4. Installs strictly required third-party dependencies (networkx, pydantic) into `rootnode_deploy`.
  5. Zips the directory into `function.zip` (excluding boto3 to reduce size).
"""

import os
import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.join(PROJECT_ROOT, "rootnode_deploy")
BACKEND_SRC = os.path.join(PROJECT_ROOT, "backend")
ZIP_NAME = os.path.join(PROJECT_ROOT, "function")  # standard name, shutil adds .zip
ENTRYPOINT_FILE = os.path.join(DEPLOY_DIR, "lambda_function.py")

# Dependencies explicitly required for AWS Lambda.
# Boto3 is pre-installed in the Lambda runtime, so we exclude it.
REQUIREMENTS = ["networkx", "pydantic"]


def clean_directory(path: str):
    """Ensure the directory exists and is empty."""
    if os.path.exists(path):
        logging.info(f"Cleaning existing deployment directory: {path}")
        shutil.rmtree(path)
    os.makedirs(path)
    logging.info(f"Created clean directory: {path}")


def install_dependencies(target_dir: str):
    """Installs required pip packages into the target dir."""
    logging.info(f"Installing dependencies: {REQUIREMENTS} into {target_dir}")
    
    # Run pip install -t . <deps>
    cmd = [
        "python", "-m", "pip", "install",
        *REQUIREMENTS,
        "-t", target_dir,
        "--no-compile",       # Save space
        "--disable-pip-version-check",
        "--quiet"
    ]
    
    try:
        subprocess.run(cmd, check=True, cwd=target_dir)
        logging.info("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install dependencies: {e}")
        raise

    # Cleanup optional fat binaries / dist-infos to keep zip lean
    for item in os.listdir(target_dir):
        if item.endswith(".dist-info") or item == "__pycache__":
            shutil.rmtree(os.path.join(target_dir, item), ignore_errors=True)


def copy_source_code():
    """Copy the backend package to the deploy directory."""
    target_backend = os.path.join(DEPLOY_DIR, "backend")
    logging.info(f"Copying Source Code: {BACKEND_SRC} -> {target_backend}")
    
    # Use shutil.copytree but ignore __pycache__ folders
    shutil.copytree(
        BACKEND_SRC, 
        target_backend, 
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "pytest_cache")
    )


def generate_entrypoint():
    """Generate the root handler so AWS configured as lambda_function.lambda_handler works."""
    logging.info(f"Generating entrypoint: {ENTRYPOINT_FILE}")
    
    # We built the entire architecture modularly in backend/, but AWS Lambda 
    # expects a top-level file by default. This wrapper imports our work.
    code = '"""AWS Lambda Entry Point for RootNode"""\n'
    code += 'from backend.handler import lambda_handler\n'
    
    with open(ENTRYPOINT_FILE, "w", encoding="utf-8") as f:
        f.write(code)


def compress_deployment():
    """Zip the deployment folder."""
    logging.info(f"Compressing {DEPLOY_DIR} to {ZIP_NAME}.zip")
    
    # Check if old zip exists
    if os.path.exists(ZIP_NAME + ".zip"):
         os.remove(ZIP_NAME + ".zip")
         
    # Create the zip archive
    shutil.make_archive(ZIP_NAME, 'zip', DEPLOY_DIR)
    
    # Print size
    size_mb = os.path.getsize(ZIP_NAME + ".zip") / (1024 * 1024)
    logging.info(f"Deployment package created: {ZIP_NAME}.zip ({size_mb:.2f} MB)")


def main():
    try:
        logging.info("Starting RootNode Lambda Build Process...")
        
        # Step 1: Create Directory
        clean_directory(DEPLOY_DIR)
        
        # Step 2: Install dependencies inside rootnode_deploy
        install_dependencies(DEPLOY_DIR)
        
        # Step 3: Copy our backend source code
        copy_source_code()
        
        # Step 4: Generate lambda_function.py wrapper
        generate_entrypoint()
        
        # Step 5: Zip it up
        compress_deployment()
        
        logging.info("Build Process Complete! Ready to upload function.zip to AWS Lambda.")
        
    except Exception as e:
        logging.error(f"Build failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
