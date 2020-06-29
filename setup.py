from setuptools import setup, find_packages

setup(
    name='py-tql',
    version='1.0',
    python_requires='>3.6',
    description='This package contains tools and libraries for working with ThoughtSpot by CS users.',
    long_description_content_type="text/markdown",
    url='https://thoughtspot.com',
    author='Bill Back',
    author_email='bill.back@thoughtspot.com',
    license='MIT',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'requests',
        'unicodecsv',
        'urllib3'
    ]
)
