from distutils.core import setup

setup(
    # Application name:
    name="nibbler",

    # Version number (initial):
    version="0.1.0",

    # Application author details:
    author="Randall Rodakowski",
    author_email="randall.rodakowski@gmail.com",

    # Packages
    packages=["nibbler"],

    # Include additional files into the package
    include_package_data=True,

    # Details
    url="http://pypi.python.org/pypi/Nibbler_v010/",

    #
    license="LICENSE.txt",
    description="A simple RSS to email application. Nibbler aggregates your subscriptions and puts them in an email.",

    long_description=open("README.md").read(),

    # Dependent packages (distributions)
    install_requires=[
        "lxml",
        "SQLAlchemy",
        "feedparser",
        "opml",
        "Jinja2",
    ],
)
