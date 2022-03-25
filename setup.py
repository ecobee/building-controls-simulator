from setuptools import setup, find_namespace_packages

REQUIRES = []

# Semantic Versioning (https://semver.org/)
_MAJOR_VERSION = "0"
_MINOR_VERSION = "6"
_PATCH_VERSION = "0"

_VERSION_SUFFIX = "alpha"

__version__ = ".".join(
    [
        _MAJOR_VERSION,
        _MINOR_VERSION,
        _PATCH_VERSION,
    ]
)
if _VERSION_SUFFIX:
    __version__ = "{}-{}".format(__version__, _VERSION_SUFFIX)

setup(
    name="BuildingControlsSimulator",
    keywords="building simulator simulation controls EnergyPlus research HVAC thermal heating air conditioning",
    version=__version__,
    author="Tom Stesco",
    author_email="tom.s@ecobee.com",
    description="building co-simulations for controls research",
    package_dir={"": "src/python"},
    packages=find_namespace_packages(where="src/python"),
    install_requires=REQUIRES,
    python_requires=">=3.8",
)
