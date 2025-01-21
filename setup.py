from setuptools import setup, find_packages

# Import __version__
exec(open("mysql_mimic/version.py").read())

setup(
    name="mysql-mimic",
    version=__version__,
    description="A python implementation of the mysql server protocol",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/kelsin/mysql-mimic",
    author="Christopher Giroir",
    author_email="kelsin@valefor.com",
    license="MIT",
    packages=find_packages(include=["mysql_mimic", "mysql_mimic.*"]),
    python_requires=">=3.6",
    install_requires=["sqlglot"],
    extras_require={
        "dev": [
            "aiomysql",
            "mypy",
            "mysql-connector-python",
            "black",
            "coverage",
            "freezegun",
            "gssapi",
            "k5test",
            "pylint",
            "pytest",
            "pytest-asyncio",
            "sphinx",
            "sqlalchemy",
            "twine",
            "wheel",
        ],
        "krb5": ["gssapi"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: SQL",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
