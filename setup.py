from setuptools import setup, find_namespace_packages

# TODO add requirements
REQUIRES = []

# Semantic Versioning (https://semver.org/)
_MAJOR_VERSION = '0'
_MINOR_VERSION = '1'
_PATCH_VERSION = '0'

_VERSION_SUFFIX = 'dev'

# Example, '0.1.0-dev' or '1.0.0'
__version__ = '.'.join([
    _MAJOR_VERSION,
    _MINOR_VERSION,
    _PATCH_VERSION,
])
if _VERSION_SUFFIX:
  __version__ = '{}-{}'.format(__version__, _VERSION_SUFFIX)


setup(
    name="BuildingControlSimulator",
    keywords="building simulator simulation control research HVAC",
    version=__version__,
    author="Tom Stesco",
    author_email="tom.s@ecobee.com",
    description="building simulation for controls research",
    package_dir={"": "src/python"},
    packages=find_namespace_packages(where="src/python"),
    install_requires=REQUIRES,
)
