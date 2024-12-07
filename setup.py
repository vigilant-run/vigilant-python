from setuptools import setup, find_packages
from vigilant.version import VERSION

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip()
                    and not line.startswith("#")]

setup(
    name="vigilant-py",
    version=VERSION,
    description="Python SDK for the Vigilant logging platform",
    url="https://github.com/vigilant-run/vigilant-python",
    packages=find_packages(exclude=["tests*"]),
    install_requires=requirements,
    python_requires=">=3.7",
)
