from setuptools import setup, find_packages

setup(
    name="contxt",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "click>=8.1.0",
        "markdownify>=0.11.0",
        "pyyaml>=6.0",
        "selenium>=4.1.0",
        "webdriver-manager>=3.8.0",
        "rich>=12.0.0",
        "pyperclip>=1.8.2",
        "tiktoken>=0.4.0",
        "questionary>=1.10.0",
    ],
    entry_points={
        "console_scripts": [
            "contxt=contxt.cli:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="Web Content Collector for LLM Context",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/contxt",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)