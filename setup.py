from setuptools import setup, find_packages

setup(
    name="cse140l",
    version="1.0.0",
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    include_package_data=True,
    install_requires=[
        'toml~=0.10.2',
        'setuptools~=70.0.0',
        'Jinja2~=3.1.4',
        'pydantic~=2.10.0'
    ]
)
