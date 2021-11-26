from setuptools import setup

setup(
    name="fc-client",
    version="0.1.2",
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
)
