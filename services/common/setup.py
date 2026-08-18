from setuptools import setup, find_packages

setup(
    name="poweros-common",
    version="0.1.0",
    description="Shared library, models, security, and schemas for POWER OS",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.7.0",
        "pydantic-settings>=2.2.0",
        "sqlalchemy>=2.0.29",
        "psycopg2-binary>=2.9.9",
        "pyjwt>=2.8.0",
        "bcrypt>=4.0.0",
        "cryptography>=42.0.5",
        "email-validator>=2.0.0",
    ],
    python_requires=">=3.10",
)
