from setuptools import setup, find_packages

setup(
    name='MyMinecraftLauncher',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'flet',
        'minecraft-launcher-lib',
        'packaging',
        'paramiko',
    ],
    entry_points={
        'console_scripts': [
            'minecraft-launcher = src.launcher:main',
        ],
    },
)
