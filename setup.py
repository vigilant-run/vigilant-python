from setuptools import setup, find_packages

setup(
    name="vigilant-sdk",
    version="1.0.0",
    author="Vigilant Team",
    author_email="support@vigilant.run",
    url="https://vigilant.run",
    description="Python SDK for Vigilant (https://vigilant.run)",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "fastapi": ["fastapi>=0.68.0"],
    },
    python_requires=">=3.7",
)
