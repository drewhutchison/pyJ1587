"""
This module contains several classes of intended-immutable record objects used
for representing J1587 messages and their components.

The fundamental representation is the :py:class:`Message` class.
Each :py:class:`Message` instance has a MID and a nonempty list of
:py:class:`Parameter` instances.
Each :py:class:`Parameter` instance has a :py:class:`PID` instance, representing
its ID, and a value, held as a python :py:class:`bytes`.
Since the formatting of a parameter's value depends on its PID, the PID class
contains an enum :py:class:`PID.PidLength` with each instance offering a value
determined by its index.

In pseudo-UML:

.. code::

         class <Message>
   --------------------------
   int mid
   [<Parameter>] parameters


   abstract class <Parameter>
   --------------------------
   <PID> pid
   bytes value


          class <PID>
   --------------------------
   int i
   virtual <PidLength> length


        enum <PidLength>
   --------------------------
   SINGLE
   DOUBLE
   VARIABLE
   DLESCAPE

:py:class:`Parameter` is marked abstract because some of its behaviors depend
on the length correseponding to its PID.
For instance, parameters with a :py:attr:`PID.PidLength.DLESCAPE` PID contain
an addressee, but no other value types do.
For OO purity, these are implemented as subclasses:
:py:class:`FixedLengthParameter`,
:py:class:`VariableLengthParameter`, and
:py:class:`DataLinkEscapeParameter`.

The :py:class:`Message` class
=============================

.. autoclass:: Message
   :members:

The :py:class:`Parameter` class and subclasses
==============================================

.. autoclass:: Parameter
   :members:
   :show-inheritance:

.. autoclass:: FixedLengthParameter
   :members:
   :inherited-members:
   :show-inheritance:

.. autoclass:: VariableLengthParameter
   :members:
   :inherited-members:

.. autoclass:: DataLinkEscapeParameter
   :members:
   :inherited-members:

The :py:class:`PID` class
=========================

.. autoclass:: PID
   :members:

"""

from __future__ import annotations

import abc
from enum import Enum, auto
from typing import List, Union

__version__ = '0.1'


class PID:
    """
    Representation of parameter identification characters (PID).

    This is solely determined by its index :py:attr:`i`.
    This is used to provide two virtual attributes:
    :py:attr:`length`, a :py:class:`PID.PidLength` indicating the length of its
    corresponding parameter's value, and
    :py:attr:`is_extended`, indicating whether it is a page-1 or page-2 PID.
    """

    class PidLength(Enum):
        """
        Enumeration of possible parameter data lengths.
        """
        SINGLE = auto()
        DOUBLE = auto()
        VARIABLE = auto()
        DLESCAPE = auto()

        @staticmethod
        def from_i(i: int) -> PID.PidLength:
            """
            Return instance appropriate to the supplied index.

            :param i: PID index
            :return: instance appropriate to representing this index.
            :raise ValueError: if index does not correspond to a valid length.
            """
            if 0 <= i <= 127 or 256 <= i <= 383:
                return PID.PidLength.SINGLE
            elif 128 <= i <= 191 or 384 <= i <= 447:
                return PID.PidLength.DOUBLE
            elif 192 <= i <= 253 or 448 <= i <= 509:
                return PID.PidLength.VARIABLE
            elif i == 254 or i == 510:
                return PID.PidLength.DLESCAPE
            else:
                raise ValueError('PID index out of range')

    def __init__(self, i: int):
        """
        :param i: index of this PID, in the range [0..510] (excluding 255)
        """
        if not 0 <= i <= 511:
            raise ValueError(f'{i} out of range for PID')
        elif i == 255:
            raise ValueError('PID 255 should not be instantiated')
        elif i == 511:
            raise ValueError('Page 2 extension is not supported')
        self._i = i

    def __eq__(self, other):
        return self.i == other.i

    def to_bytes(self) -> bytes:
        """
        :return: length-1 :py:class:`bytes` representation of the LSB of this PID.

        .. note::
           This might not be what you are expecting, since
           ``PID(i).to_bytes() == PID(j).to_bytes()`` does not necessarily mean
           that ``i == j``, nor is ``PID(i).to_bytes()`` necessarily the
           :py:class:`bytes` representation of ``i``.

           This behavior derives from the way that page-2 PIDs are escaped;
           see the messaging format and/or implementation of
           :py:meth:`Message.to_bytes` for why.
        """
        return (self._i % 256).to_bytes(1, 'little')

    @property
    def i(self) -> int:
        """Index of this PID in range [0..510]"""
        return self._i

    @property
    def is_extended(self) -> bool:
        """True if this is a page-2 PID, False if it is page-1"""
        return self.i > 255

    @property
    def length(self) -> PID.PidLength:
        """Length of this PID's value"""
        return PID.PidLength.from_i(self.i)


class Parameter(abc.ABC):
    """
    Representation of a "Parameter", that is, a combination of a PID and a
    value.

    For reasons described above, this class inherits :py:class:`abc.ABC` and
    should not be instantiated by itself.
    Instead, use one of its subclasses below.

    :py:attr:`value` is stored and returned as :py:class:`bytes`, since
    interpretation of these (as signed/unsigned, int, float, or ascii, etc) is
    determined also by the PID in a manner determined by the SAE specification
    and beyond the scope of this implementation.
    Future versions might include convenience methods for casting this, though
    doing so from the :py:class:`bytes` object is not difficult.
    """

    def __init__(self,
                 pid: PID,
                 value: bytes,
                 length: int):
        if len(value) > length:
            raise ValueError(f'value {value} exceeds length {length} of '
                             f'"{self.__class__.__name__}" instance')

        self._pid = pid
        self._value = value
        self._varlength = length

    def __eq__(self, other):
        return self.pid == other.pid and self.value == other.value

    @property
    def pid(self) -> PID:
        """:py:class:`PID` of the Parameter"""
        return self._pid

    @property
    def value(self) -> bytes:
        """Value of the parameter"""
        return self._value

    @abc.abstractmethod
    def to_bytes(self) -> bytes:
        """
        :return: :py:class:`bytes` representation of the Parameter, including the LSB
                 of the PID, the value, and any interstitial characters required
                 by the specific type.
        """
        pass  # b/c abstract


class FixedLengthParameter(Parameter):
    """
    Represents Parameter with data field of fixed length, i.e.
    :py:attr:`PID.PidLength` of
    :py:class:`PID.PidLength.SINGLE` or :py:class:`PID.PidLength.DOUBLE`.

    :paramref:`value` should not exceed the length corresponding to
    :paramref:`pid` and, if necessary will be left-padded with zeros to make up
    this length in the return of :py:meth:`to_bytes`.
    """

    def __init__(self, pid: PID, value: bytes):

        if pid.length is PID.PidLength.SINGLE:
            super().__init__(pid, value, 1)
        elif pid.length is PID.PidLength.DOUBLE:
            super().__init__(pid, value, 2)
        elif pid.length is PID.PidLength.VARIABLE:
            raise ValueError('variable-length parameters should use class '
                             'VariableLengthParameter')
        elif pid.length is PID.PidLength.DLESCAPE:
            raise ValueError('data link parameters should use class'
                             f' {DataLinkEscapeParameter.__name__}')
        else:
            raise RuntimeError('should be unreachable')

    def to_bytes(self) -> bytes:
        return self.pid.to_bytes() + self.value.rjust(self._varlength, b'\x00')


class VariableLengthParameter(Parameter):
    """
    Represents Parameter with data field of variable length, and thus with
    :py:attr:`PID.PidLength` of :py:class:`PID.PidLength.VARIABLE`.

    :param length: If specified, must be at least as large as ``len(value)``, or
                   else :py:exc:`ValueError` will be raised.
                   If greater, :paramref:`value` will be zero-left-padded in the
                   return of :py:meth:`to_bytes` to make up the difference.
                   If not specified, defaults to ``len(value)``.
    """

    def __init__(self,
                 pid: PID,
                 value: bytes,
                 length: Union[int, None] = None):

        if pid.length is not PID.PidLength.VARIABLE:
            raise ValueError(f'{self.__class__.__name__} instance must '
                             f'have VARIABLE length PID')

        if length is not None:
            if len(value) > length:
                raise ValueError(f'value {value} exceeds specified length '
                                 f'{length}.')
            super().__init__(pid, value, length)
        else:
            super().__init__(pid, value, len(value))

    def to_bytes(self) -> bytes:
        length = self._varlength.to_bytes(1, 'little')
        return self.pid.to_bytes() + length + self.value


class DataLinkEscapeParameter(Parameter):
    """
    Represents Data Link Escape Parameter, i.e. with
    :py:attr:`PID.PidLength` of :py:class:`PID.PidLength.DLESCAPE`.

    Provided it does not overrun the allowed length, :py:attr:`value` will be
    returned verbatim by :py:meth:`to_bytes`, and without any additional
    padding.

    :param addressee: MID of addressee
    """

    def __init__(self,
                 pid: PID,
                 addressee: int,
                 value: bytes):

        if pid.length is not PID.PidLength.DLESCAPE:
            raise ValueError(f'{self.__class__.__name__} instance must '
                             f'have ESCAPE PID')

        if not 0 <= addressee <= 255:
            raise ValueError('addressee must be between 0 and 255')

        super().__init__(pid, value, len(value))
        self._addressee = addressee

    @property
    def addressee(self) -> int:
        """MID of this message's addressee"""
        return self._addressee

    def to_bytes(self) -> bytes:
        addresseebytes = self.addressee.to_bytes(1, 'little')
        return self.pid.to_bytes() + addresseebytes + self.value


class Message:
    """
    Representation of a J1587 message.

    :param mid: MID of the message, 0 <= mid <= 255, subsequently available
        as :py:attr:`mid` and :py:attr:`mid_as_bytes`.

    :param parameters: List of :py:class:`Parameter` instances,
        subsequently available as :py:attr:`parameters`.

    Aside from range-checking of :paramref:`mid`, no validation is performed
    upon initialization.
    This is intentional, since :py:attr:`parameters` is not immutable.
    In fact, it may be desirable to modify this list after the
    :py:class:`Message` instance is instantiated.

    Thus, it's not guaranteed that a general instance will successfully return
    :py:meth:`to_bytes`, and there's no easier way to check than by attempting
    such a call and checking for ValueError.
    """

    def __init__(self,
                 mid: int,
                 parameters: List[Parameter]):

        if not 0 <= mid <= 255:
            raise ValueError(f'{mid} out of range for MID')
        self._mid = mid

        self._parameters = parameters

    def __eq__(self, other):
        return (self.mid == other.mid
                and len(self.parameters) == len(other.parameters)
                and all(p1 == p2
                        for p1, p2
                        in zip(self.parameters, other.parameters))
                )

    @property
    def mid(self) -> int:
        """MID of the message as :py:class:`int`"""
        return self._mid

    @property
    def mid_as_bytes(self) -> bytes:
        """MID of the message as :py:class:`bytes`"""
        return self.mid.to_bytes(1, 'little')

    @property
    def parameters(self) -> List[Parameter]:
        """List of :py:class:`Parameter` s in this message"""
        return self._parameters

    def to_bytes(self) -> bytes:
        """
        Calculates and returns :py:class:`bytes` representation of this message,
        including checksum.

        This calls :py:meth:`check_parameters` and will fail for any of the
        reasons listed there if :py:attr:`parameters` is invalid.
        It also calls :py:meth:`append_checksum` and will fail if
        :py:attr:`parameters` would lead to a message of length exceeding the
        allowed 21 bytes.

        :return: representation of this message suitable for passing to pyserial
            or whatever.
        :raises ValueError: according to the behavior of
            :py:meth:`check_parameters` and :py:meth:`append_checksum`.
        """
        contents = (self.mid_as_bytes
                    + (b'\xff'
                       if self.check_parameters(self.parameters)
                       else b'')
                    + b''.join(parameter.to_bytes()
                               for parameter in self.parameters))
        return self.append_checksum(contents)

    @staticmethod
    def check_parameters(parameters: List[Parameter]) -> bool:
        """Checks that the following conditions are met:

        1) :paramref:`parameters` is nonempty
        2) Every element of :paramref:`parameters` is an instance of
           :py:class:`Parameter`
        3) All or no members of :paramref:`parameters` are extended
        4) If any parameter is a data link escape, it is the final one in the
           list

        :param parameters: list of parameters to check
        :raises ValueError: if any of these conditions is not met.
        :returns: whether all or no parameters are extended."""

        if not parameters:
            raise ValueError

        if not all(isinstance(parameter, Parameter)
                   for parameter in parameters):
            raise ValueError('non-Parameter instance found in list')

        is_dles = [isinstance(parameter, DataLinkEscapeParameter)
                   for parameter in parameters]
        if any(is_dles):
            # if we're here, we have at least one DLE.
            # Thus we require the last element be a DLE.
            # If there is more than one, at least one of those is not the last
            # element.
            if not is_dles[-1] or sum(is_dles) > 1:
                raise ValueError(f'{DataLinkEscapeParameter.__name__} must be '
                                 f'last parameter in list.')

        allare = all((parameter.pid.is_extended
                      for parameter in parameters))
        noneare = all((not parameter.pid.is_extended
                       for parameter in parameters))

        if allare or noneare:
            return allare
        raise ValueError('Cannot mix extended and unextended parameters in'
                         'same message')

    @staticmethod
    def calc_checksum(s: bytes) -> int:
        """
        Calculates checksum of `s` according to the method described in the
        standard and returns.

        :param s: :py:class:`bytes` in
        :return: the checksum
        """
        return -sum(memoryview(s)) % 256

    @classmethod
    def append_checksum(cls, s: bytes) -> bytes:
        """
        Calculates checksum of `s` and appends, including checking to make sure
        the resulting message is not greater than 21 bytes in length.

        :param s: :py:class:`bytes` in
        :return:  :paramref:`s` with checksum appended.
            Checksum is one byte in length so this will have length 1 greater
            than :paramref:`s`.
        :raises ValueError: if ``len(s) > 20``
        """

        l = len(s)
        if l > 20:
            raise ValueError(f'"{s}" (length {l}) exceeds max length 20')
        return s + cls.calc_checksum(s).to_bytes(1, 'little')

    @classmethod
    def strip_checksum(cls, s: bytes) -> bytes:
        # TODO doc, test
        head = s[:-1]
        expected_checksum = cls.calc_checksum(head)
        provided_checksum = s[-1]
        if expected_checksum != provided_checksum:
            raise ValueError(f'Error parsing "{s}": '
                             f'provided checksum {provided_checksum} differs'
                             f'from expected value {expected_checksum}')
        return head
