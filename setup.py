from setuptools import setup, find_packages

setup(
    name='hq-code-deployer',
    version='1.0.0',
    url='',
    include_package_data=True,
    license='',
    author='Ryan Belgrave',
    author_email='rbelgrave@covermymeds.com',
    description='Herqles Code Deployer Framework and Worker',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    install_requires=[
        'pyyaml==3.11',
        'virtualenv-api==2.1.4',
        'schematics==1.0.4'
    ],
    extras_require={
        'framework': [
            'hq-framework==1.0.0',
            'cherrypy',
            'sqlalchemy',
            'pika',
        ],
        'worker': [
            'hq-worker==1.0.0',
            'pika'
        ],
        'cli': [
            'hq-cli==1.0.0'
        ]
    },
    dependency_links=[
        'git+https://github.com/herqles-io/hq-framework.git#egg=hq-framework-1.0.0',
        'git+https://github.com/herqles-io/hq-worker.git#egg=hq-worker-1.0.0'
        'git+https://github.com/herqles-io/hq-cli.git#egg=hq-cli-1.0.0'
    ]
)
