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
Someone with a need to generate or simulate J1587 traffic might find it
similarly useful.
If you're just looking to *consume* J1587 data, you might be better served by
one of the `related projects <Related projects>`_, some of which include
semantic interpretation of the data, direct integration with pyserial, *etc*.

****************
SAE J1587 Format
****************

.. include:: doc/format.rst

****************
Package overview
****************

************
Building doc
************

************
Running test
************

****************
Related projects
****************

- https://github.com/ainfosec/pretty_j1587,
  a command-line tool and support libraries, implemented in python,
  for interpreting a J1587 data stream in light of the semantic information
  contained in the J1708 and J1587 specification documents.