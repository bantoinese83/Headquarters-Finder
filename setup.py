"""
Setup script for Headquarters Finder application.

This script provides packaging and installation configuration for the
Headquarters Finder application.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "docs" / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="headquarters-finder",
    version="1.0.0",
    author="AI Assistant",
    author_email="ai@assistant.com",
    description="High-accuracy corporate headquarters data retrieval using Google Gemini 2.5 Pro API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ai-assistant/headquarters-finder",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "headquarters-finder=headquarters_finder.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "headquarters_finder": [
            "config.ini",
            "config_sample.ini",
        ],
    },
    zip_safe=False,
)
