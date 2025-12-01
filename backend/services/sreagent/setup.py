"""Setup script for sreagent package."""

from setuptools import setup, find_packages

setup(
    name="sreagent",
    version="0.1.0",
    description="Kubernetes Troubleshooting Chat Agent with MCP Integration",
    packages=find_packages(),
    install_requires=[
        "google-adk>=0.1.0",
        "google-genai>=0.1.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
        "mcp>=0.9.0",
        "kubernetes>=28.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0",
    ],
    python_requires=">=3.10",
)

