import setuptools

setuptools.setup(
    name="mstr-rest-requests",
    version="0.0.1",
    author="Paul Bailey",
    author_email="bailey@dreamshake.net",
    description="A custom subclass of sessions Session object for interacting with the MicroStrategy REST API",
    packages=setuptools.find_packages(),
    install_requires=[
        "requests",
        "requests-toolbelt"
    ]
)
