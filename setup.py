from setuptools import find_packages
from setuptools import setup

README = open('README').read()

setup(name='mt-data-api',
      packages=find_packages(),
      version='0.0.4',
      description='A port of mt-data-api-sdk-swift.',
      long_description=README,
      author='Masahiro IUCHI',
      author_email='masahiro.iuchi@gmail.com',
      url='https://github.com/masiuchi/mt-data-api-sdk-python',
      license='MIT License',
      keywords='movabletype data-api sdk',
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
      )
