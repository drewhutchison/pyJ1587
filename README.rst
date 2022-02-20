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

.. include:: doc/format.rst

****************
Package overview
****************

************
Building doc
************

``pip install -r requirements-doc.txt`` then
``cd doc && make html``.
Doc will be generated in ``doc/build/html``.

************
Running test
************

*********
Changelog
*********

****
TODO
****

- installer
- Parsing of bytestream to Message objects
- __str__ representation

.. include:: doc/additional_resources.rst