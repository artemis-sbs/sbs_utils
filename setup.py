import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sbs_utils",
    version="0.2.0",
    author="Doug Reichard",
    author_email="demo@email.com",
    description="A small demo package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dougreichard/sbs_utils",
    packages=setuptools.find_packages(
        where='sbs_utils'
    ),
    
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)