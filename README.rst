#######
pyJ1587
#######

This is a simple, low-level serializer/deserializer for the SAE J1587 messaging
format syntax.
It provides an object-oriented implementation of the message components, range
and value checking, checksum generation and verification, *etc*.

I wrote this when I needed to generate a large number of J1587 messages and
wanted to avoid making the sort of bit-level errors that are common to a more
ad-hoc implementation.
Someone needing to generate or simulate J1587 traffic might find it
similarly useful.
If you're just looking to *consume* J1587 data, you might be better served by
one of the `additional resources <Additional resources>`_, some of which include
semantic interpretation of the data, direct integration with pyserial, *etc*.

**************
Message format
**************

See `here <./doc/format.rst>`_

****************
Package overview
****************

The module provides several read-only record classes for representing the
concepts described above.

The ``Message`` class is represents messages, which can be output as ``bytes``
(including checksum and framing data) via its ``to_bytes()`` method.
It is initialized with an integer MID and a nonempty list of ``Parameter``
instances.
Implementations of this are
``FixedLengthParameter``,
``VariableLengthParameter``, and
``DataLinkEscapeParameter``
(depending on the length and format of the parameter's value).
Each of these is instantiated with a ``PID`` instance and a suitably-sized
``bytes`` object representing this value.

As an example::

    >>> from pyJ1587 import *

    >>> Message(
            195,
            [VariableLengthParameter(
                PID(501),
                b'Hello world'
            )]
        ).to_bytes()

    b'\xc3\xff\xf5\x0bHello world\x02'

More complete documentation is available when built as described in the next
section.

************
Building doc
************

``pip install -r requirements-doc.txt`` then
``cd doc && make html``.
Doc will be generated in ``doc/build/html``.

************
Running test
************

For now,

``python -m unittest discover -s pyJ1587/test/``

*********
Changelog
*********

0.1
---

Initial release


0.2
---

- Implement `__str__` and `__eq__` methods
- Implement `Message.from_bytes`

****
TODO
****

- Improve installer, publish to pypi
- Document more examples
- Add test cases
- Define CI to run test and automate doc generation
- Clean up API; most utility methods should be hidden

********************
Additional resources
********************

See `here <./doc/additional_resources.rst>`_