import os

from setuptools import setup, Command
from about import __version__


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):  # pylint: disable=no-self-use
        os.system("rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info ./__pycache__")


setup(
    name="fc-client",
    version=__version__,
    author="Larry Shen",
    author_email="larry.shen@nxp.com",
    license="MIT",
    python_requires=">=3.6",
    packages=["fc_client"],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
    entry_points={
        "console_scripts": [
            "fc-client = fc_client.client:main",
        ]
    },
    install_requires=["prettytable==2.2.1", "labgrid==0.4.0"],
    cmdclass={
        "clean": CleanCommand,
    },
)
