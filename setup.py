from setuptools import setup, find_packages

setup(
    name="vigilant-py",
    version="3.0.1",
    author="Vigilant Team",
    author_email="support@vigilant.run",
    url="https://vigilant.run",
    description="Python SDK for Vigilant (https://vigilant.run)",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "requests>=2.28.0",
    ],
    python_requires=">=3.7",
)
