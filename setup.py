import setuptools

setuptools.setup(
    name="mstr-rest-requests",
    version="0.0.4",
    author="Paul Bailey",
    author_email="bailey@dreamshake.net",
    description="Easily make requests to the MicroStrategy REST API",
    packages=setuptools.find_packages(),
    install_requires=[
        "requests",
        "requests-toolbelt"
    ]
)
