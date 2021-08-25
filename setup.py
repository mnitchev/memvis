from setuptools import setup, find_packages


setup(
    name='memvis',
    version='0.1',
    packages=find_packages(),
    install_requires=['python-ptrace', 'prettytable'],
    author='Mario Nitchev',
    author_email='mail@ala.bala',
    description='Memory Visualisation',
    entry_points = {
        'console_scripts': [
            'memvis = memvis.memvis:run',
        ],
    },
    license='',
    keywords='memory, visualisation, console, proc',
    url='https://github.com/mnitchev/memvis/',
    test_suite='tests'
)
