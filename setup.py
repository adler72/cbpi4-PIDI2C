from setuptools import setup

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='cbpi4-PIDI2C',
      version='0.0.5',
      description='CraftBeerPi4 PID Kettle Logic Plugin',
      author=['Marc Adler'],
      author_email='aeda@gmx.de',
      url='https://github.com/adler72/cbpi4-PIDI2C',
      license='GPLv3',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4-PIDI2C': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4-PIDI2C'],
      install_requires=[
            'cbpi',
      ],
      long_description=long_description,
      long_description_content_type='text/markdown'
     )
