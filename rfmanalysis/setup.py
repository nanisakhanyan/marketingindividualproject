#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    author="Narine Isakhanyan",
    author_email='narine_isakhanyan@edu.aua.am',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Python package for RFM and Customer segmentation.",
    install_requires=['pandas>=1.2.4', 'numpy>=1.20.1', 'matplotlib>=3.3.4'],
    license="MIT license",
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords='rfmanalysis',
    name='rfmanalysis',
    packages=find_packages(include=['rfmanalysis', 'rfmanalysis.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/nanisakhanyan/marketingindividualproject.git',
    version='0.0.1',
    zip_safe=False,
)
