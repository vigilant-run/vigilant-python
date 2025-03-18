from setuptools import setup, find_packages

VERSION = "2.0.1"

setup(
    name="vigilant-py",
    version=VERSION,
    description="Python SDK for the Vigilant logging platform",
    packages=find_packages(exclude=["tests*"]),
    install_requires=["requests>=2.31.0"],
    python_requires=">=3.7",
)
