****************
SAE J1587 Format
****************

Messages
--------

A J1587 *message* is composed of a one-byte *message ID* (``MID``),
followed by a list of one or more *parameters* (up to 19 bytes),
and concluding with a one-byte *checksum*.


.. code::


   Message
   -------

       [ MID ] [ Parameter List ] [ Checksum ]
      |   1   |     ??? < 20     |     1      |

The MID is the ID of the device transmitting the message.
A list of these values is provided in the SAE standard and is outside the scope
of present discussion.

Parameters
----------

Each *parameter* consists of a *parameter identification* number (``PID``),
followed by a data payload.
Valid PIDs are in the range ``[0..511]``.
PIDs in the range ``[0..254]`` are *page-1* PIDs, which are represented simply
by the one-byte unsigned representation of their index.
PIDs in the range ``[256..511]`` are *page-2* PIDs.
These are represented by one byte, which is their index minus 256 (equivalently,
the LSB of their index).

Page-2 PIDs are distinguished by the presence of an escape byte, 255, at the
beginning of the parameter list (immediately following the MIB).
Thus, *a single message must contain only parameters with either page-1 or
page-2 PIDs*, and parameters cannot be mixed between the two types.

.. code::


   Page-1 parameter list
   ---------------------

       [ PID ] [ Value ] ( [ PID ] [ Value ] ( . . . ))
      |   1   |   ???    |    1   |   ???   |  . . .

   Page-2 parameter list
   ---------------------

       [ 0xFF ] [ LSB(PID) ] [ Value ] ( [ LSB(PID) ] [ Value ] ( . . . ))
      |    1   |     1      |   ???    |      1      |   ???   |  . . .

The PID 255 is unrepresentable, since it serves to escape the page-2 PIDs.
The PID 511 is reserved for a similar purpose, although this extension is not
defined in J-1587.

The length needed by a parameter's value depends on the PID of the parameter.
These are described below.

Single-length parameters
^^^^^^^^^^^^^^^^^^^^^^^^

PIDs whose LSB lies in the range ``[0..127]`` are assigned a single character to
represent their data, which immediately follows the PID representation.

Note that the interpretation of this byte (*viz*. signed or unsigned, char, or
otherwise) depends on the particular PID.

.. code::

   Single-length parameter
   -----------------------

       [ PID ∈ [0..127] ] [ Data ]
      |         1        |    1   |

Double-length parameters
^^^^^^^^^^^^^^^^^^^^^^^^

PIDs whose LSB lies in the range ``[128..191]`` are assigned two characters to
represent their data, which immediately follow the PID representation.

Note that the interpretation of these byte (*viz*. signed or unsigned, char, or
otherwise) depends on the particular PID.

.. code::

   Double-length parameter
   -----------------------

       [ PID ∈ [128..191] ] [ Data ]
      |          1         |    1   |

Variable-length parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^

PIDs whose LSB lies in the range ``[192..253]`` may contain data of variable
length.
The length of this data is represented by a single byte, which follows the PID.
This many bytes of data will then follow.


.. code::

   Variable-length parameter
   -------------------------

       [ PID ∈ [192..253] ] [ Length n ] [ Data ]
      |          1         |      1     |    n   |

Note that this length cannot be arbitrarily large and, in particular, must not
be such that the total message length exceeds the allowed space of 21 bytes.

As before, interpretation of data depends on the PID and is outside the scope
of present discussion.

Data link escape parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^

PIDs whose LSB is 254 represent a *data link escape*.
This is provided to allow for the transmission of  special commands,
configuration data, or suchlike to a specific device, whose MIB follows the PID.
All following bytes up to the message checksum are considered to be part of the
escaped parameter value, thus *no other parameters may follow a data link escape
parameter in a single message*

.. code::

   Data link escape parameter
   --------------------------

       [ 254 ] [ Recipient MIB] [ Data ]
      |   1   |        1       |   ???  |

