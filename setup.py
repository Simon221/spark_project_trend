"""
Setup configuration for Spark Trend Analyzer package
"""

from setuptools import setup, find_packages
from pathlib import Path

# Lire le README
here = Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

# Lire les requirements
requirements_file = here / "requirements-openai.txt"
if requirements_file.exists():
    requirements = [line.strip() for line in requirements_file.readlines() 
                   if line.strip() and not line.startswith("#")]
else:
    requirements = []

setup(
    name="spark-trend-analyzer",
    version="1.0.0",
    description="AI-powered Spark data trend analysis platform with LangChain and OpenAI GPT-4o",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Simon Pierre Diouf",
    author_email="",
    url="https://github.com/yourusername/spark_project_trend",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    packages=find_packages(include=["src", "src.*"]),
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.990",
        ],
        "docs": [
            "sphinx>=5.0",
            "sphinx-rtd-theme>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "spark-trend-analyzer=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": ["api/*.html", "api/*.js"],
    },
)
