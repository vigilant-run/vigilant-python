from setuptools import setup, find_packages

VERSION = "1.0.1"

setup(
    name="vigilant-py",
    version=VERSION,
    description="Python SDK for the Vigilant logging platform",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-exporter-otlp-proto-grpc>=1.20.0",
        "protobuf>=4.24.0",
        "grpcio>=1.59.0",
    ],
    python_requires=">=3.7",
)
