from setuptools import setup, find_packages
from setuptools import Distribution


class BinaryDistribution(Distribution):
    def is_pure(self):
        return False


def load_requirements(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file if not line.startswith('#')]


setup(
    name='luna-cli',
    version='1.0.2',
    packages=find_packages(),
    author='itsadead',
    install_requires=load_requirements('requirements.txt'),
    entry_points={
        'console_scripts': [
            'luna = luna_cli.main:cli',
        ],
    },
    distclass=BinaryDistribution
)