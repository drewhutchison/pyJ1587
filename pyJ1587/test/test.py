import unittest.mock

import pyJ1587 as dut


class TestPID(unittest.TestCase):

    SINGLE_LENGTH_PIDS = [0, 1, 12, 127, 256, 383]
    DOUBLE_LENGTH_PIDS = [128, 191, 384, 447]
    VARIABLE_LENGTH_PIDS = [192, 253, 448, 509]
    DLESCAPE_PIDS = [254, 510]
    UNEXTENDED_PIDS = [0, 1, 12, 254]
    EXTENDED_PIDS = [256, 257, 510]

    def test_i_works(self):
        for i in [0, 1, 12, 254, 256, 257, 510]:
            pid = dut.PID(i)
            self.assertEqual(pid.i, i)

    def test_exception_i_out_of_range(self):
        for i in [-1, 512, 39847]:
            with self.assertRaises(ValueError):
                dut.PID(i)

    def test_exception_i_forbidden(self):
        for i in [255, 511]:
            with self.assertRaises(ValueError):
                dut.PID(i)

    def test_is_extended(self):
        for i in self.UNEXTENDED_PIDS:
            pid = dut.PID(i)
            self.assertFalse(pid.is_extended)
        for i in self.EXTENDED_PIDS:
            pid = dut.PID(i)
            self.assertTrue(pid.is_extended)

    def test_to_bytes(self):
        for i, b in [
            (0, b'\x00'),
            (1, b'\x01'),
            (0xfe, b'\xfe'),
            (0x0100, b'\x00'),
            (0x0101, b'\x01'),
            (0x01fe, b'\xfe'),
        ]:
            pid = dut.PID(i)
            self.assertEqual(pid.to_bytes(), b)

    def test_length(self):
        for i in self.SINGLE_LENGTH_PIDS:
            pid = dut.PID(i)
            self.assertIs(pid.length, dut.PidLength.SINGLE)
        for i in self.DOUBLE_LENGTH_PIDS:
            pid = dut.PID(i)
            self.assertIs(pid.length, dut.PidLength.DOUBLE)
        for i in self.VARIABLE_LENGTH_PIDS:
            pid = dut.PID(i)
            self.assertIs(pid.length, dut.PidLength.VARIABLE)
        for i in self.DLESCAPE_PIDS:
            pid = dut.PID(i)
            self.assertIs(pid.length, dut.PidLength.DLESCAPE)

    def test_unreachable(self):
        pid = dut.PID(0)
        pid._i = 1234
        with self.assertRaises(RuntimeError):
            _ = pid.length


class TestParameter(unittest.TestCase):

    def test_is_abstract(self):
        # should not be able to instantiate class directly
        with self.assertRaises(TypeError):
            pid = dut.PID(23)
            dut.Parameter(pid, b'', 0)

    # decorator to mock abstract methods to allow direct instantiation
    unabstract = unittest.mock.patch.multiple(
        dut.Parameter, __abstractmethods__=set())

    @unabstract
    def test_properties(self):
        pid = dut.PID(23)
        value = b'j'
        parameter = dut.Parameter(pid, value, 1)
        self.assertIs(parameter.pid, pid)
        self.assertIs(parameter.value, value)

    @unabstract
    def test_length_check(self):
        with self.assertRaises(ValueError):
            dut.Parameter(dut.PID(0), b'abc', 1)


class TestFixedLengthParameter(unittest.TestCase):

    def test_lengths(self):
        for i in TestPID.SINGLE_LENGTH_PIDS:
            parameter = dut.FixedLengthParameter(dut.PID(i), b'8')
            self.assertEqual(parameter._varlength, 1)
        for i in TestPID.DOUBLE_LENGTH_PIDS:
            parameter = dut.FixedLengthParameter(dut.PID(i), b'88')
            self.assertEqual(parameter._varlength, 2)

    def test_bad_pids(self):
        for i in [*TestPID.VARIABLE_LENGTH_PIDS,
                  *TestPID.DLESCAPE_PIDS]:
            with self.assertRaises(ValueError):
                dut.FixedLengthParameter(dut.PID(i), b'')

    @unittest.mock.patch('pyJ1587.PID', length=None)
    def test_unreachable(self, PID):
        pid = PID(0)
        with self.assertRaises(RuntimeError):
            dut.FixedLengthParameter(pid, b'')

    def test_to_bytes(self):
        for i, v, b in [
            (0x00, b'3', b'\x003'),
            (0x69, b'3', b'\x693'),
            (0x0100, b'h', b'\x00h'),
            (0x80, b'yi', b'\x80yi'),
            (0x0182, b'39', b'\x8239'),
        ]:
            self.assertEqual(dut.FixedLengthParameter(
                dut.PID(i), v).to_bytes(),
                             b)


class TestVariableLengthParameter(unittest.TestCase):

    def test_bad_pids(self):
        for i in [*TestPID.DLESCAPE_PIDS,
                  *TestPID.DOUBLE_LENGTH_PIDS,
                  *TestPID.SINGLE_LENGTH_PIDS]:
            with self.assertRaises(ValueError):
                dut.VariableLengthParameter(dut.PID(i), b'', None)

    def test_length_specified_and_overruns(self):
        pid = dut.PID(TestPID.VARIABLE_LENGTH_PIDS[0])
        with self.assertRaises(ValueError):
            dut.VariableLengthParameter(pid, b'1234', 3)

    def test_length_specified_and_equal(self):
        pid = dut.PID(TestPID.VARIABLE_LENGTH_PIDS[0])
        m = dut.VariableLengthParameter(pid, b'1234', 4)
        self.assertEqual(m._varlength, 4)

    def test_length_specified_and_underruns(self):
        pid = dut.PID(TestPID.VARIABLE_LENGTH_PIDS[0])
        m = dut.VariableLengthParameter(pid, b'1234', 5)
        self.assertEqual(m._varlength, 5)

    def test_to_bytes(self):
        for i, v, b in [
            (0xc0, b'3', b'\xc0\x013'),
            (0xc1, b'34', b'\xc1\x0234'),
        ]:
            self.assertEqual(dut.VariableLengthParameter(
                dut.PID(i), v).to_bytes(),
                             b)


class TestDataLinkEscapeParameter(unittest.TestCase):

    def test_bad_pids(self):
        for i in [*TestPID.SINGLE_LENGTH_PIDS,
                  *TestPID.DOUBLE_LENGTH_PIDS,
                  *TestPID.VARIABLE_LENGTH_PIDS]:
            with self.assertRaises(ValueError):
                dut.DataLinkEscapeParameter(dut.PID(i), 127, b'')

    def test_bad_addressee(self):
        for pid in TestPID.DLESCAPE_PIDS:
            for addressee in [-1, 256, 999]:
                with self.assertRaises(ValueError):
                    dut.DataLinkEscapeParameter(dut.PID(pid), addressee, b'')

    def test_addressee(self):
        for pid in TestPID.DLESCAPE_PIDS:
            for addressee in [0, 1, 69, 254, 255]:
                parameter = dut.DataLinkEscapeParameter(
                    dut.PID(pid), addressee, b'')
                self.assertEqual(parameter.addressee, addressee)

    def test_to_bytes(self):
        for i, addressee, payload, value in [
            (254, 123, b'', b'\xfe\x7b'),
            (254, 123, b'payload', b'\xfe\x7bpayload'),
        ]:
            self.assertEqual(dut.DataLinkEscapeParameter(
                dut.PID(i), addressee, payload).to_bytes(), value)


class TestMessage(unittest.TestCase):

    def test_mid(self):

        # bad mids should ValueError out of range
        for i in [-1, 256, 999]:
            with self.assertRaises(ValueError):
                dut.Message(i, [])

        # good mids should expose the property
        for i in [0, 1, 127, 128, 255]:
            m = dut.Message(i, [])
            self.assertEqual(m.mid, i)

    def test_mid_as_bytes(self):
        # good mids should expose the property as_bytes
        for i, bytes_i in [(0, b'\x00'),
                           (1, b'\x01'),
                           (0x7f, b'\x7f'),
                           (0x80, b'\x80'),
                           (0xff, b'\xff')]:
            m = dut.Message(i, [])
            self.assertEqual(m.mid_as_bytes,
                             i.to_bytes(1, dut._LITTLE_ENDIAN))

    def test_parameters(self):
        # TODO test getter
        pass

    def test_to_bytes(self):
        # TODO impl
        pass

    @staticmethod
    def _parameter_from_pid(pid: dut.PID) -> dut.Parameter:

        if pid.length == dut.PidLength.SINGLE:
            return dut.FixedLengthParameter(pid, b'9')
        elif pid.length == dut.PidLength.DOUBLE:
            return dut.FixedLengthParameter(pid, b'99')
        elif pid.length == dut.PidLength.VARIABLE:
            return dut.VariableLengthParameter(pid, b'')
        elif pid.length == dut.PidLength.DLESCAPE:
            return dut.DataLinkEscapeParameter(pid, 123, b'')
        else:
            raise RuntimeError('should be unreachable')

    def test_check_parameters(self):

        # empty list should ValueError
        with self.assertRaises(ValueError):
            dut.Message.check_parameters([])

        # list of only extended params should return True
        self.assertTrue(dut.Message.check_parameters([
            self._parameter_from_pid(dut.PID(i))
            for i in TestPID.EXTENDED_PIDS
        ]))

        # list of only unextended params should return False
        self.assertFalse(dut.Message.check_parameters([
            self._parameter_from_pid(dut.PID(i))
            for i in TestPID.UNEXTENDED_PIDS
        ]))

        # list of mixed extended and unextended params should ValueError
        with self.assertRaises(ValueError):
            dut.Message.check_parameters([
                self._parameter_from_pid(dut.PID(i))
                for i in [*TestPID.UNEXTENDED_PIDS,
                          *TestPID.EXTENDED_PIDS]
            ])

        # list of one DataLinkEscapeParameter should pass
        dut.Message.check_parameters([
            self._parameter_from_pid(dut.PID(TestPID.DLESCAPE_PIDS[0]))
        ])

        # list with DataLinkEscapeParameter at end should pass
        dut.Message.check_parameters([
            self._parameter_from_pid(dut.PID(TestPID.SINGLE_LENGTH_PIDS[0])),
            self._parameter_from_pid(dut.PID(TestPID.DLESCAPE_PIDS[0])),
        ])

        # list with DataLinkEscapeParameter not at end should fail
        with self.assertRaises(ValueError):
            dut.Message.check_parameters([
                self._parameter_from_pid(
                    dut.PID(TestPID.SINGLE_LENGTH_PIDS[0])),
                self._parameter_from_pid(dut.PID(TestPID.DLESCAPE_PIDS[0])),
                self._parameter_from_pid(
                    dut.PID(TestPID.SINGLE_LENGTH_PIDS[0])),
            ])

        # list with two DataLinkEscapeParameters should fail
        with self.assertRaises(ValueError):
            dut.Message.check_parameters([
                self._parameter_from_pid(dut.PID(TestPID.DLESCAPE_PIDS[0])),
                self._parameter_from_pid(dut.PID(TestPID.DLESCAPE_PIDS[0])),
            ])

    def test_calc_checksum(self):
        for s, checksum in [
            (b'\x00', 0x00),
            (b'\x01', 0xff),
            (b'\xff', 0x01),
            (b'\x00\x01', 0xff),
            (b'\x01\x00', 0xff),
            (b'\x01\x01', 0xfe),
            (b'\xfe\x01\x01', 0x00),
        ]:
            self.assertEqual(dut.Message.calc_checksum(s), checksum)

    def test_append_checksum(self):
        # normal cases should work
        for s, sc in [
            (b'\x00', b'\x00\x00'),
            (b'\x01', b'\x01\xff'),
            (b'\xff', b'\xff\x01'),
            (b'\x00\x01', b'\x00\x01\xff'),
            (b'\x01\x00', b'\x01\x00\xff'),
            (b'\x01\x01', b'\x01\x01\xfe'),
            (b'\xfe\x01\x01', b'\xfe\x01\x01\x00'),
        ]:
            self.assertEqual(dut.Message.append_checksum(s), sc)

        # and overlength cases should throw
        with self.assertRaises(ValueError):
            dut.Message.append_checksum(b'123456789012345678901')

    def test_strip_checksum(self):
        # strings s with correct checksum should return s[:-1]
        for s in [
            b'\x00\x00',
            b'\x01\xff',
            b'\xff\x01',
            b'\x00\x01\xff',
            b'\x01\x00\xff',
            b'\x01\x01\xfe',
            b'\xfe\x01\x01\x00',
        ]:
            self.assertEqual(dut.Message.strip_checksum(s), s[:-1])

        # and strings with incorrect checksum should throw

        for s in [
            b'\x00\x01',
            b'\x00\xff',
            b'\x01\xfe',
            b'\xff\x11',
            b'\x00\x01\x69',
            b'\x01\x00\xfe',
            b'\x01\x01\xff',
            b'\xfe\x01\x01\x01',
        ]:
            with self.assertRaises(ValueError):
                dut.Message.strip_checksum(s)
