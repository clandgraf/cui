
from setuptools import setup

setup(
    name =             "cui",
    version =          "0.0.1",
    author =           "Christoph Landgraf",
    author_email =     "christoph.landgraf@googlemail.com",
    description =      "A Text UI Framework for Python",
    license =          "BSD",
    url =              "https://github.com/clandgraf/cui",
    packages =         ['cui', 'cui_tools'],
    entry_points =     {'console_scripts': [
        'cui = cui.__main__:main',
        'cuicli = cui_client.__main__:main',
    ]}
)
