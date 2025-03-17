from setuptools import setup

setup(
    # Application name:
    name="nibbler-rss",

    # Version number (initial):
    version="0.3.0",

    # Application author details:
    author="Randall Rodakowski",
    author_email="randall.rodakowski@gmail.com",

    # Packages
    packages=["nibbler"],

    # Include additional files into the package
    package_data={
        'nibbler': ['resources/*', 'templates/*'],
    },
    include_package_data=True,

    # Details
    url="https://github.com/rrodakowski/nibbler",

    #
    license="LICENSE.txt",
    description="A simple RSS to email application. Nibbler aggregates your subscriptions and puts them in an email.",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),

    # Dependent packages (distributions)
    install_requires=[
        "lxml==5.1.0",
        "SQLAlchemy==2.0.39",
        "feedparser==6.0.11",
        "Jinja2==3.1.6",
    ],

    entry_points={
        'console_scripts': [
            # "name_of_executable = module.with:function_to_execute"
            "nibbler = nibbler.__main__:main"
        ]
    },
)
