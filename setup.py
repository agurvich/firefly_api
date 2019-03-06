import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="firefly_api-agurvich",
    version="0.0.1",
    author="Alex Gurvich",
    author_email="agurvich@u.northwestern.edu",
    description="The python API for Firefly, a browser-based particle viewer.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agurvich/firefly_api",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD2 License",
        "Operating System :: OS Independent",
    ],
    py_modules=["options","reader","particlegroup"]
)
