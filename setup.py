from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='usnparser',
    version='5.0.0',
    description='A Python 3 script to parse the NTFS USN journal',
    long_description=long_description,
    url='https://github.com/digitalsleuth/USN-Journal-Parser',
    author='Adam Witt, Corey Forman',
    author_email='corey@digitalsleuth.ca',
    license='Apache Software License',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Information Technology',
        'Topic :: Security',
        'License :: OSI Approved :: Apache Software License'
    ],
    python_requires=">=3",
    packages=find_packages(),
    scripts=['usnparser/usn.py']
)
