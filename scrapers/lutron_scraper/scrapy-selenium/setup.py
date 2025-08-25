from setuptools import setup, find_packages

setup(
    name='scrapy-selenium',
    version='0.0.7',
    packages=['scrapy_selenium'],
    install_requires=[
        'scrapy>=2.0.0',
        'selenium>=4.0.0',
        'zope.interface>=5.1.0'
    ],
    author='Chris Pierfelice',
    author_email='chrispierfelice@gmail.com',
    description='Scrapy middleware to handle javascript pages using selenium',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/clemfromspace/scrapy-selenium',
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ]
)