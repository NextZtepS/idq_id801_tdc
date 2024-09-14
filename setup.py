from setuptools import setup, find_packages

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="idq_id801",
    description="Python library for interfacing with IDQ ID801 Time to Digital Converter",
    version="1.0.1",
    author="NextZtepS",
    author_email="natdanaiongarjvaja@gmail.com",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "numpy",
        "pandas",
        "matplotlib",
    ],
    extras_require={
        "dev": [
            "pytest",
            "twine",
        ],
    },
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NextZtepS/idq_id801_tdc",
    license="MIT",
)