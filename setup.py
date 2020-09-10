from setuptools import setup


with open('./requirements.txt') as f:
    REQUIRED = [f'{req.strip()}' for req in f.readlines()]


with open('./README.md') as f:
    README = '\n'.join(f.readlines())


setup(
    name='ThoughtSpot CS Tools',
    version='0.1.0',
    description='Python programming interface to the ThoughtSpot API and platform',
    long_description=README,
    author='Customer Success @ ThoughtSpot',
    author_email='ps-na@thoughtspot.com',
    url='https://github.com/thoughtspot/ts_tools',
    license='MIT',
    packages=('thoughtspot_internal', ),
    install_requires=REQUIRED,
    python_requires='>=3.6'
)
