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
            self.assertIs(pid.length, dut.PID.PidLength.SINGLE)
        for i in self.DOUBLE_LENGTH_PIDS:
            pid = dut.PID(i)
            self.assertIs(pid.length, dut.PID.PidLength.DOUBLE)
        for i in self.VARIABLE_LENGTH_PIDS:
            pid = dut.PID(i)
            self.assertIs(pid.length, dut.PID.PidLength.VARIABLE)
        for i in self.DLESCAPE_PIDS:
            pid = dut.PID(i)
            self.assertIs(pid.length, dut.PID.PidLength.DLESCAPE)

    def test_unreachable(self):
        pid = dut.PID(0)
        pid._i = 1234
        with self.assertRaises(ValueError):
            _ = pid.length

    def test___eq__(self):
        one = dut.PID(0)
        same = dut.PID(0)
        other = dut.PID(1)
        self.assertEqual(one, same)
        self.assertNotEqual(one, other)

    def test___str__(self):
        one = dut.PID(0)
        self.assertEqual('PID(0)', str(one))


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

    @unabstract
    def test___eq__(self):
        cases = [
            dut.Parameter(dut.PID(i), v, l)
            for i, v, l in [
                (0, b'8', 1),
                (0, b'9', 1),
                (1, b'8', 1),
                (128, b'88', 2),
                (191, b'88', 2),
                (0xc1, b'34', 2),
            ]]
        for i in range(len(cases)):
            for j in range(len(cases)):
                if i == j:
                    self.assertEqual(cases[i], cases[j])
                else:
                    self.assertNotEqual(cases[i], cases[j])


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

    def test_formatted_lengths(self):
        for i in TestPID.SINGLE_LENGTH_PIDS:
            parameter = dut.FixedLengthParameter(dut.PID(i), b'8')
            self.assertEqual(len(parameter.to_bytes()), 2)
        # when given a single byte, double-length parameters should still
        # return 3
        for i in TestPID.DOUBLE_LENGTH_PIDS:
            parameter = dut.FixedLengthParameter(dut.PID(i), b'8')
            self.assertEqual(len(parameter.to_bytes()), 3)
        for i in TestPID.DOUBLE_LENGTH_PIDS:
            parameter = dut.FixedLengthParameter(dut.PID(i), b'88')
            self.assertEqual(len(parameter.to_bytes()), 3)

    def test___str__(self):
        cases = [
            (
                "Length-1 parameter (PID(12), b'8')",
                str(dut.FixedLengthParameter(dut.PID(12), b'8'))
            ),
            (
                "Length-2 parameter (PID(191), b'8')",
                str(dut.FixedLengthParameter(dut.PID(191), b'8'))
            ),
            (
                "Length-2 parameter (PID(191), b'89')",
                str(dut.FixedLengthParameter(dut.PID(191), b'89'))
            ),
        ]
        for expected, param in cases:
            self.assertEqual(expected, str(param))


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

    def test___str__(self):
        cases = [
            (
                "Length-2 parameter (PID(192), b'89')",
                str(dut.VariableLengthParameter(dut.PID(192), b'89'))
            ),
            (
                "Length-4 parameter (PID(192), b'8912')",
                str(dut.VariableLengthParameter(dut.PID(192), b'8912'))
            ),
        ]
        for expected, param in cases:
            self.assertEqual(expected, str(param))


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

    def test___str__(self):
        cases = [
            (
                "Length-1 data link escape parameter (PID(254), MID=123, b'8')",
                str(dut.DataLinkEscapeParameter(dut.PID(254), 123, b'8'))
            ),
        ]
        for expected, param in cases:
            self.assertEqual(expected, str(param))


class TestMessage(unittest.TestCase):
    test_cases = [
        # single P1 single-length
        (0,
         [
             dut.FixedLengthParameter(dut.PID(1), b'\x88')
         ],
         b'\x00\x01\x88\x77'),
        (1,
         [
             dut.FixedLengthParameter(dut.PID(1), b'\x08')
         ],
         b'\x01\x01\x08\xf6'),
        (0x0c,
         [
             dut.FixedLengthParameter(dut.PID(1), b'\x88')
         ],
         b'\x0c\x01\x88\x6b'),
        # double P1 single-length
        (0,
         [
             dut.FixedLengthParameter(dut.PID(1), b'\x88'),
             dut.FixedLengthParameter(dut.PID(1), b'\x88')
         ],
         b'\x00\x01\x88\x01\x88\xee'),
        # single P2 single-length
        (0x17,
         [
             dut.FixedLengthParameter(dut.PID(0x0105), b'\x99')
         ],
         b'\x17\xff\x05\x99\x4c'),
        # double P2 single-length
        (0x25,
         [
             dut.FixedLengthParameter(dut.PID(0x0105), b'\x99'),
             dut.FixedLengthParameter(dut.PID(0x0105), b'\x99')
         ],
         b'\x25\xff\x05\x99\x05\x99\xa0'),
        # TODO lots more cases
    ]

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
                             i.to_bytes(1, 'little'))

    def test_unrepresentable(self):
        # per the documentation, we should be able to instantiate cases without
        # error but for which to_bytes() will fail.

        # we should be able to successfully instantiate with empty parameters
        msg = dut.Message(1, [])
        # but to_bytes should then fail
        with self.assertRaises(ValueError):
            msg.to_bytes()

        # we should be able to successfully instantiate with too many params
        msg = dut.Message(1, [dut.FixedLengthParameter(dut.PID(1), b'a')] * 10)
        # but to_bytes should then fail
        with self.assertRaises(ValueError):
            msg.to_bytes()

    def test_parameters(self):
        # "parameters" argument to constructor should be exposed as property,
        # for now, `is` will suffice for comparison.
        l = [dut.FixedLengthParameter(dut.PID(23), b'')]
        msg = dut.Message(123, l)
        self.assertIs(msg.parameters, l)

    def test_to_bytes(self):
        # if we're going to catch regressions, here's where we're going to do it
        # special cases ahoy!
        for pid, params, expected in self.test_cases:
            msg = dut.Message(pid, params)
            self.assertEqual(msg.to_bytes(), expected)

    @staticmethod
    def _parameter_from_pid(pid: dut.PID) -> dut.Parameter:
        if pid.length == dut.PID.PidLength.SINGLE:
            return dut.FixedLengthParameter(pid, b'9')
        elif pid.length == dut.PID.PidLength.DOUBLE:
            return dut.FixedLengthParameter(pid, b'99')
        elif pid.length == dut.PID.PidLength.VARIABLE:
            return dut.VariableLengthParameter(pid, b'')
        elif pid.length == dut.PID.PidLength.DLESCAPE:
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

        # lists with non-Parameter instances should ValueError
        for parameters in [
            [*[self._parameter_from_pid(dut.PID(i))
               for i in TestPID.EXTENDED_PIDS],
             None]
        ]:
            with self.assertRaises(ValueError):
                dut.Message.check_parameters(parameters)

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

    def test___eq__(self):
        args = [
            (0, [
                dut.FixedLengthParameter(dut.PID(1), b'\x88')
            ]),
            (1, [
                dut.FixedLengthParameter(dut.PID(1), b'\x08')
            ]),
            (0x0c,
             [
                 dut.FixedLengthParameter(dut.PID(1), b'\x88')
             ]),
            (0, [
                dut.FixedLengthParameter(dut.PID(1), b'\x88'),
                dut.FixedLengthParameter(dut.PID(1), b'\x88')
            ]),
            (0x17, [
                dut.FixedLengthParameter(dut.PID(0x0105), b'\x99')
            ]),
            (0x25, [
                dut.FixedLengthParameter(dut.PID(0x0105), b'\x99'),
                dut.FixedLengthParameter(dut.PID(0x0105), b'\x99')
            ]),
        ]
        jcases = [
            dut.Message(pid, params)
            for pid, params in args]
        icases = [
            dut.Message(pid, params)
            for pid, params in args]
        for i in range(len(args)):
            for j in range(len(args)):
                if i == j:
                    self.assertEqual(icases[i], jcases[j])
                else:
                    self.assertNotEqual(icases[i], jcases[j])

    def test___str__(self):
        cases = [
            ("Message object (MID=0, params=[Length-1 parameter (PID(1), b'\\x88')])",
             (0, [
                 dut.FixedLengthParameter(dut.PID(1), b'\x88')
             ])),
            ("Message object (MID=0, params=[Length-1 parameter (PID(1), b'\\x88'), "
             "Length-1 parameter (PID(1), b'\\x88')])",
             (0, [
                 dut.FixedLengthParameter(dut.PID(1), b'\x88'),
                 dut.FixedLengthParameter(dut.PID(1), b'\x88')
             ])),
        ]
        for expected, args in cases:
            self.assertEqual(expected, str(dut.Message(*args)))

    def test_from_bytes(self):
        for pid, params, bytes_ in self.test_cases:
            msg = dut.Message(pid, params)
            self.assertEqual(msg, dut.Message.from_bytes(bytes_))
