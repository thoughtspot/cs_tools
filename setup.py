from setuptools import setup, find_packages


with open('./requirements.txt') as f:
    REQUIRED = [f'{req.strip()}' for req in f.readlines()]


with open('./README.md') as f:
    README = '\n'.join(f.readlines())


setup(
    name='cs_tools',
    version='0.1.0',
    description='Python programming interface to the ThoughtSpot API and platform',
    long_description=README,
    author='Customer Success @ ThoughtSpot',
    author_email='ps-na@thoughtspot.com',
    url='https://github.com/thoughtspot/cs_tools',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    install_requires=REQUIRED,
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'cs_tools = cs_tools.cli:run',
        ]
    }
)
