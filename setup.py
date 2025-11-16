"""Setup configuration for claude-sync"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description (will create later)
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else "Git-like version control for Claude Code configurations"

setup(
    name="claude-sync",
    version="0.1.0",
    author="Nick Krzemienski",
    author_email="",
    description="Cross-machine sync utility for Claude Code configurations, skills, and MCP servers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/krzemienski/claude-sync",
    packages=find_packages(exclude=['tests', 'tests.*']),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=[
        "click>=8.1.0",
        "GitPython>=3.1.40",
        "paramiko>=3.0.0",
        "jinja2>=3.1.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "claude-sync=claude_sync.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
