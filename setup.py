from setuptools import setup, find_packages
from codecs import open
from os import path
import json

# Generate the merged schema file when setting up the package.
from ckanext.cdp.cdp_schema import save_merged_schema
save_merged_schema()

# Get the absolute path to the directory where this setup.py resides.
here = path.abspath(path.dirname(__file__))

# Read the README file to use as the long package description.
try:
    with open(path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except IOError:
    long_description = ''

setup(
    # Basic metadata about the package.
    name='ckanext-cdp',
    version='0.0.1',
    description='A sample CKAN extension for demonstration purposes',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/opend-team/ckanext-cdp',
    author='opend team',
    author_email='contact@example.com',
    license='AGPL',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='CKAN',
    # Automatically discover all packages in the project except those excluded.
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    # Define the namespace packages used.
    namespace_packages=['ckanext'],
    install_requires=[],
    include_package_data=True,
    # Define additional files to include in the package distribution.
    package_data={
        'ckanext.thai_gdc': ['ckan_dataset.json'], 
        'ckanext.cdp': [
            'templates/*.html',
            'templates/scheming/*.html',
            'templates/scheming/form_snippets/*.html',
            'public/*',
            'ckan_dataset_cdp.json',
            'ckan_dataset_original.json'
        ],
    },
    # Register the plugin entry point so CKAN can load the plugin.
    entry_points={
        'ckan.plugins': [
            'cdp = ckanext.cdp.plugin:CdpPlugin',
        ],
    },
    # Define how messages are extracted for translation.
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)