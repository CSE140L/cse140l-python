from setuptools import setup, find_packages

setup(
    name="cse140l",
    version="1.0.0",
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    include_package_data=True,
)
