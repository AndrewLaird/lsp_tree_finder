from setuptools import setup, find_packages

setup(
    name='lsp_tree_finder',  
    version='0.2',  
    packages=find_packages(),  
    url='https://github.com/AndrewLaird/lsp_tree_finder',  
    author='Andrew Laird',  
    author_email='lairdandrew11@gmail.com',  # Your email
    description='Command line too to search for pattern inside of call tree under selected function',  # A brief description of your package
    long_description=open('README.md').read(),  # Longer description from the README
    long_description_content_type='text/markdown',  # Specify the README format
    install_requires=[  # A list of dependencies your package needs
        'numpy',
        'matplotlib',
        # etc.
    ],
    classifiers=[  
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    entry_points={  # Command-line scripts
        'console_scripts': [
            'lsp_tree_finder=lsp_tree_finder.main:cli',  # Replace with your package, module, and function
        ],
    },
)
