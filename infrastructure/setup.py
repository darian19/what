from setuptools import setup, find_packages

requirements = map(str.strip, open("requirements.txt").readlines())

setup(
    name = "infrastructure",
    packages = find_packages(),
    version = "0.0.2",
    install_requires = requirements
)
