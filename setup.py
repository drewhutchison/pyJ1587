from distutils.core import setup
from pyJ1587 import __version__

setup(
    name='pyJ1587',
    version=__version__,
    description='Syntactic (de)serialization of SAE J1587 messages',
    packages=['pyJ1587']
)