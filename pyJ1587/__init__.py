"""
pyJ1587
-------

Simple library for formatting and parsing SAE J1587 protocol packets.
"""

import abc
from enum import Enum, auto
from typing import List, Union

# We're going to be calling int.to_bytes and int.from_bytes a LOT
# These take a string argument 'big' or 'little', with other values raising
# ValueError.
# To avoid fatfingering the magic strings, and to allow better code
# introspection, we therefore define the following constant.
# Best practice is to use this whenever calling either of these functions.
_LITTLE_ENDIAN = 'little'


class PidLength(Enum):
    SINGLE = auto()
    DOUBLE = auto()
    VARIABLE = auto()
    DLESCAPE = auto()


class PID:
    """
    Class representing parameter identification characters.
    """
    def __init__(self, i: int):
        if not 0 <= i <= 511:
            raise ValueError(f'{i} out of range for PID')
        elif i == 255:
            raise ValueError('PID 255 should not be instantiated')
        elif i == 511:
            raise ValueError('Page 2 extension is not supported')
        self._i = i

    def to_bytes(self) -> bytes:
        return (self._i % 256).to_bytes(1, _LITTLE_ENDIAN)

    @property
    def i(self) -> int:
        return self._i

    @property
    def is_extended(self) -> bool:
        return self.i > 255

    @property
    def length(self) -> PidLength:
        return self.length_from_i(self.i)

    @staticmethod
    def length_from_i(i: int) -> PidLength:
        if 0 <= i <= 127 or 256 <= i <= 383:
            return PidLength.SINGLE
        elif 128 <= i <= 191 or 384 <= i <= 447:
            return PidLength.DOUBLE
        elif 192 <= i <= 253 or 448 <= i <= 509:
            return PidLength.VARIABLE
        elif i == 254 or i == 510:
            return PidLength.DLESCAPE
        else:
            raise RuntimeError('Should be unreachable')


class Parameter(abc.ABC):
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

    @property
    def pid(self) -> PID:
        return self._pid

    @property
    def value(self):
        return self._value

    @abc.abstractmethod
    def to_bytes(self) -> bytes:
        pass


class FixedLengthParameter(Parameter):
    def __init__(self, pid: PID, value: bytes):

        if pid.length is PidLength.SINGLE:
            super().__init__(pid, value, 1)
        elif pid.length is PidLength.DOUBLE:
            super().__init__(pid, value, 2)
        elif pid.length is PidLength.VARIABLE:
            raise ValueError('variable-length parameters should use class'
                             'VariableLengthParameter')
        elif pid.length is PidLength.DLESCAPE:
            raise ValueError('data link parameters should use class'
                             f' {DataLinkEscapeParameter.__name__}')
        else:
            raise RuntimeError('should be unreachable')

    def to_bytes(self) -> bytes:
        return self.pid.to_bytes() + self.value


class VariableLengthParameter(Parameter):
    def __init__(self,
                 pid: PID,
                 value: bytes,
                 length: Union[int, None] = None):

        if pid.length is not PidLength.VARIABLE:
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
        length = self._varlength.to_bytes(1, _LITTLE_ENDIAN)
        return self.pid.to_bytes() + length + self.value


class DataLinkEscapeParameter(Parameter):
    def __init__(self,
                 pid: PID,
                 addressee: int,
                 value: bytes):

        if pid.length is not PidLength.DLESCAPE:
            raise ValueError(f'{self.__class__.__name__} instance must '
                             f'have ESCAPE PID')

        if not 0 <= addressee <= 255:
            raise ValueError('addressee must be between 0 and 255')

        super().__init__(pid, value, len(value))
        self._addressee = addressee

    @property
    def addressee(self) -> int:
        return self._addressee

    def to_bytes(self) -> bytes:
        addresseebytes = self.addressee.to_bytes(1, _LITTLE_ENDIAN)
        return self.pid.to_bytes() + addresseebytes + self.value


class Message:
    def __init__(self,
                 mid: int,
                 parameters: List[Parameter]):

        if not 0 <= mid <= 255:
            raise ValueError(f'{mid} out of range for MID')
        self._mid = mid

        parameters and self.check_parameters(parameters)
        self._parameters = parameters

    @property
    def mid(self) -> int:
        return self._mid

    @property
    def mid_as_bytes(self) -> bytes:
        return self.mid.to_bytes(1, _LITTLE_ENDIAN)

    @property
    def parameters(self) -> List[Parameter]:
        return self._parameters

    def to_bytes(self) -> bytes:
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

        1) ``parameters`` is nonempty
        2) All or no members of ``parameters`` are extended
        3) If any parameter is a data link escape, it is the final one in the
           list

        Raises ValueError if any of these conditions are not met.
        Otherwise returns whether all or no parameters are extended."""

        if not parameters:
            raise ValueError

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
        return -sum(memoryview(s)) % 256

    @classmethod
    def append_checksum(cls, s: bytes) -> bytes:
        l = len(s)
        if l > 20:
            raise ValueError(f'"{s}" (length {l}) exceeds max length 20')
        return s + cls.calc_checksum(s).to_bytes(1, _LITTLE_ENDIAN)

    @classmethod
    def strip_checksum(cls, s: bytes) -> bytes:
        head = s[:-1]
        expected_checksum = cls.calc_checksum(head)
        provided_checksum = s[-1]
        if expected_checksum != provided_checksum:
            raise ValueError(f'Error parsing "{s}": '
                             f'provided checksum {provided_checksum} differs'
                             f'from expected value {expected_checksum}')
        return head
