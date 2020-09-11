from setuptools import setup

with open("README.md", "r") as readme:
    long_description = readme.read()

setup(
    name="mprisctl",
    description="Command line utility to control music players",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version="0.0.1",
    author="RangHo Lee",
    author_email="hello@rangho.me",
    url="https://github.com/RangHo/mprisctl",
    py_modules=['mprisctl'],
    entry_points={
        'console_scripts': ['mprisctl=mprisctl:main']
    }
)
