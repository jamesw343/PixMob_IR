import enum
import sys


class Chance(enum.Enum):
    CHANCE_100_PCT  = 0b000
    CHANCE_88_PCT   = 0b001
    CHANCE_67_PCT   = 0b010
    CHANCE_50_PCT   = 0b011
    CHANCE_32_PCT   = 0b100
    CHANCE_16_PCT   = 0b101
    CHANCE_10_PCT   = 0b110
    CHANCE_4_PCT    = 0b111

    def __int__(self):
        return self.value


class Time(enum.Enum):
    TIME_0_MS       = 0b000
    TIME_32_MS      = 0b001
    TIME_96_MS      = 0b010
    TIME_192_MS     = 0b011
    TIME_480_MS     = 0b100
    TIME_960_MS     = 0b101
    TIME_2400_MS    = 0b110
    TIME_3840_MS    = 0b111

    def __int__(self):
        return self.value


class GlobalSustainTime(enum.Enum):
    TIME_64_MS      = 0b000
    TIME_112_MS     = 0b001
    TIME_160_MS     = 0b010
    TIME_208_MS     = 0b011
    TIME_480_MS     = 0b100
    TIME_960_MS     = 0b101
    TIME_2400_MS    = 0b110
    TIME_3840_MS    = 0b111

    def __int__(self):
        return self.value


class _FieldFragment:
    """
    Fragment for part of a _Field into one or more command bytes.
    """
    def __init__(self, byte, offset, width, src_offset=0):
        self.byte = byte
        self.offset = offset
        self.width = width
        self.src_offset = src_offset
        # Only lower 6 bits of each command byte is valid
        assert self.offset + self.width <= 6

class _Field:
    """
    Logical command field.
    """
    def __init__(self, fragments, value_type, default=None, read_only=False):
        self.fragments = fragments
        self.value_type = value_type
        self.default = default
        self.read_only = read_only
        if self.read_only:
            assert self.default is not None, "Read-only field must specify default value"

    def min_fragment_offset(self):
        """
        Return the minimum flattened bit offset of all fragments. Useful for sorting fields.
        """
        fragment_offsets = [fragment.byte * 8 + fragment.offset for fragment in self.fragments]
        return min(fragment_offsets)


class FieldTypeException(Exception):
    pass

class FieldKeyException(Exception):
    pass

class FieldReadOnlyException(Exception):
    pass

class CommandDecodeException(Exception):
    pass


class GenericCommand:
    """
    A generic command class containing only bytes and no fields.

    Used when a decoded command does not match any of our defined command classes.
    """
    def __init__(self, buffer):
        self._buffer = buffer

    def __repr__(self):
        buffer_str = ' '.join(f"{b:02X}" for b in self._buffer)
        return f"{type(self).__name__}(bytes={buffer_str})"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, type(self)) and \
            other._buffer == self._buffer


class Command:
    _commands = []
    _encoding_map = [
        0x21, 0x32, 0x54, 0x65, 0xa9, 0x9a, 0x6d, 0x29,
        0x56, 0x92, 0xa1, 0xb4, 0xb2, 0x84, 0x66, 0x2a,
        0x4c, 0x6a, 0xa6, 0x95, 0x62, 0x51, 0x42, 0x24,
        0x35, 0x46, 0x8a, 0xac, 0x8c, 0x6c, 0x2c, 0x4a,
        0x59, 0x86, 0xa4, 0xa2, 0x91, 0x64, 0x55, 0x44,
        0x22, 0x31, 0xb1, 0x52, 0x85, 0x96, 0xa5, 0x69,
        0x5a, 0x2d, 0x4d, 0x89, 0x45, 0x34, 0x61, 0x25,
        0x36, 0xad, 0x94, 0xaa, 0x8d, 0x49, 0x99, 0x26,
    ]
    _decoding_map = { k: v for v, k in enumerate(_encoding_map) }

    def __init__(self, **field_values):
        self._populate_fields(field_values)
        self._validate_fields()
        self._populate_buffer()

    def encode(self) -> list[int]:
        """
        Encode the command into IR string representation.
        """
        encoded_bytes = list(self._buffer)

        # Perform encoding and keep track of intermediate checksum
        checksum = 0
        for i in range(2, len(encoded_bytes)):
            encoded_bytes[i] = Command._encoding_map[encoded_bytes[i]]
            checksum += encoded_bytes[i]

        # Calculate final checksum, place into buffer
        checksum = (checksum >> 2) & 0x3F
        checksum = Command._encoding_map[checksum]
        encoded_bytes[1] = checksum

        # Separate bits into IR sequence
        encoded_bits = []
        for b in encoded_bytes:
            for i in range(8):
                # Don't insert leading 0's
                if encoded_bits or b & 0b1:
                    encoded_bits.append(b & 0b1)
                b >>= 1

        # Delete trailing 0's
        while encoded_bits[-1] == 0:
            encoded_bits.pop()

        return encoded_bits

    @staticmethod
    def decode(encoded_bits: list[int], verify_checksum=True):
        """
        Decode an IR string and return the matching Command class.

        verify_checksum: Validate the checksum with the expected checksum. Fails if
                         there is a checksum mismatch.
        """
        encoded_bytes = [0]
        num_leading_zeroes = 0
        for i, b in enumerate(encoded_bits):
            # Skip leading 0's
            if b == 0 and len(encoded_bytes) == 1 and encoded_bytes[0] == 0:
                num_leading_zeroes += 1
                continue

            # Commands are stored starting at bit 7 of byte 0
            bit_pos = i + 7 - num_leading_zeroes
            byte_index = bit_pos // 8
            while len(encoded_bytes) - 1 < byte_index:
                encoded_bytes.append(0)
            if b:
                encoded_bytes[byte_index] |= 1 << (bit_pos % 8)

        if len(encoded_bytes) not in [6, 9]:
            raise CommandDecodeException(f"Invalid command size: {len(encoded_bytes)} ")

        # Perform decoding and keep track of intermediate checksum starting from 3rd byte
        checksum = 0
        decoded_bytes = [0] * len(encoded_bytes)
        decoded_bytes[0] = encoded_bytes[0]
        for i, byte in enumerate(encoded_bytes[2:]):
            checksum += byte
            if byte not in Command._decoding_map:
                raise CommandDecodeException(f"Invalid byte at offset {i + 2}: {byte:#04x}")
            decoded_bytes[i + 2] = Command._decoding_map[byte]

        # Verify the checksum is correct
        expected_checksum = (checksum >> 2) & 0x3F
        expected_checksum = Command._encoding_map[expected_checksum]
        if verify_checksum and encoded_bytes[1] != expected_checksum:
            raise CommandDecodeException(f"Checksum mismatch: " +
                f"expected {expected_checksum:#04x}, " +
                f"received {encoded_bytes[1]:#04x}")

        # Try finding the matching command class
        match_classes = []
        for cls in Command._commands:
            if cls._num_bytes != len(decoded_bytes) or \
                    cls._flags_type != ((decoded_bytes[2] >> 1) & 0b111) or \
                    (hasattr(cls, '_action_id') and cls._action_id != (decoded_bytes[7] & 0x1F)):
                continue
            match_classes.append(cls)

        if len(match_classes) == 0:
            return GenericCommand(decoded_bytes)
        elif len(match_classes) > 1:
            raise CommandDecodeException(f"Multiple matching commands found: {match_classes}")
        else:
            cls = match_classes[0]

        # Extract fields from decoded bytes based on command field definitions
        field_values = {}
        for field_name, field in cls._fields.items():
            raw_field_value = 0
            for fragment in field.fragments:
                # Extract and mask the fragment from the decoded bytes
                fragment_value = decoded_bytes[fragment.byte] >> fragment.offset
                fragment_value &= (1 << fragment.width) - 1
                # Add it to the field at the correct offset
                raw_field_value |= fragment_value << fragment.src_offset
            field_value = field.value_type(raw_field_value)
            field_values[field_name] = field_value

        return cls(**field_values)


    def _populate_fields(self, field_values):
        self._field_values = field_values
        fields = type(self)._fields

        # Check for unexpected fields, field types, and modification of read-only fields
        for field_name, field_value in self._field_values.items():
            if field_name not in fields:
                raise FieldKeyException(f"Unexpected field: {field_name} = {field_value}")
            field = fields[field_name]
            if not isinstance(field_value, field.value_type):
                raise FieldTypeException(f"Field {field_name} type mismatch: " +
                    f"expected {field.value_type.__name__}, " +
                    f"received {type(field_value).__name__} (value: {field_value})")
            if field.read_only and field_value != field.default:
                raise FieldReadOnlyException(f"Field {field_name} may not be modified " +
                    f"from the default value of {field.default}")

        # Check for missing required fields
        # For missing fields with a default value defined, apply the default value
        missing_fields = set(fields.keys()).difference(self._field_values.keys())
        for field_name in list(missing_fields):
            field = fields[field_name]
            if field.default is not None:
                self._field_values[field_name] = field.default
                missing_fields.remove(field_name)
        if missing_fields:
            missing_fields = ", ".join(sorted(list(missing_fields)))
            raise FieldKeyException(f"Missing fields: {missing_fields}")

    def _validate_fields(self):
        """
        Allow commands to define additional field validations.
        """
        pass

    def _populate_buffer(self):
        cls = type(self)
        self._buffer = [0] * cls._num_bytes

        # Populate command type flags and magic values
        self._buffer[0] = 0b10000000 # Magic value
        self._buffer[2] = cls._flags_type << 1
        if len(self._buffer) == 9 and hasattr(cls, '_action_id'):
            self._buffer[7] = cls._action_id

        # Add user-defined fields
        for field_name, field in cls._fields.items():
            field_value = int(self._field_values[field_name])
            for fragment in field.fragments:
                # Extract and mask a portion of the field value
                fragment_value = field_value >> fragment.src_offset
                fragment_value &= (1 << fragment.width) - 1
                # Now shift to proper place; to be ORed with command byte
                fragment_value <<= fragment.offset
                self._buffer[fragment.byte] |= fragment_value

    def __init_subclass__(cls):
        Command._commands.append(cls)

    def __repr__(self):
        cls = type(self)
        buffer_str = ' '.join(f"{b:02X}" for b in self._buffer)
        fields_str = ', '.join(f"{k}={v}" for k, v in sorted(self._field_values.items(),
            key=lambda x: cls._fields[x[0]].min_fragment_offset()))
        return f"{cls.__name__}(bytes={buffer_str}, {fields_str})"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, type(self)) and \
            other._field_values == self._field_values


class CommandSingleColor(Command):
    _num_bytes  = 6
    _flags_type = 0b000
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=False),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'green':            _Field([_FieldFragment(byte=3, offset=0, width=6, src_offset=2)], int),
        'red':              _Field([_FieldFragment(byte=4, offset=0, width=6, src_offset=2)], int),
        'blue':             _Field([_FieldFragment(byte=5, offset=0, width=6, src_offset=2)], int),
    }

    def _validate_fields(self):
        if self._field_values['on_start']: assert self._field_values['gst_enable']


class CommandSingleColorExt(Command):
    _num_bytes  = 9
    _flags_type = 0b000
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=False),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'green':            _Field([_FieldFragment(byte=3, offset=0, width=6, src_offset=2)], int),
        'red':              _Field([_FieldFragment(byte=4, offset=0, width=6, src_offset=2)], int),
        'blue':             _Field([_FieldFragment(byte=5, offset=0, width=6, src_offset=2)], int),
        'chance':           _Field([_FieldFragment(byte=6, offset=0, width=3)], Chance, default=Chance.CHANCE_100_PCT),
        'attack':           _Field([_FieldFragment(byte=6, offset=3, width=3)], Time, default=Time.TIME_480_MS),
        'sustain':          _Field([_FieldFragment(byte=7, offset=0, width=3)], Time, default=Time.TIME_480_MS),
        'release':          _Field([_FieldFragment(byte=7, offset=3, width=3)], Time, default=Time.TIME_480_MS),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
        'enable_repeat':    _Field([_FieldFragment(byte=8, offset=5, width=1)], bool, default=False),
    }

    def _validate_fields(self):
        if self._field_values['on_start']: assert self._field_values['gst_enable']


class CommandTwoColors(Command):
    _num_bytes  = 9
    _flags_type = 0b010
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=False, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'green1':           _Field([_FieldFragment(byte=3, offset=0, width=6, src_offset=2)], int),
        'red1':             _Field([_FieldFragment(byte=4, offset=0, width=6, src_offset=2)], int),
        'blue1':            _Field([_FieldFragment(byte=5, offset=0, width=6, src_offset=2)], int),
        'green2':           _Field([_FieldFragment(byte=6, offset=0, width=6, src_offset=2)], int),
        'red2':             _Field([_FieldFragment(byte=7, offset=0, width=6, src_offset=2)], int),
        'blue2':            _Field([_FieldFragment(byte=8, offset=0, width=6, src_offset=2)], int),
    }


class CommandSetConfig(Command):
    _num_bytes  = 6
    _flags_type = 0b001
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=False),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'profile_id_lo':    _Field([_FieldFragment(byte=3, offset=0, width=4)], int),
        'profile_id_hi':    _Field([_FieldFragment(byte=3, offset=4, width=2),
                                    _FieldFragment(byte=4, offset=0, width=2, src_offset=2)], int),
        'is_random':        _Field([_FieldFragment(byte=4, offset=2, width=1)], bool),
        'attack':           _Field([_FieldFragment(byte=4, offset=3, width=3)], Time, default=Time.TIME_480_MS),
        'sustain':          _Field([_FieldFragment(byte=5, offset=0, width=3)], Time, default=Time.TIME_480_MS),
        'release':          _Field([_FieldFragment(byte=5, offset=3, width=3)], Time, default=Time.TIME_480_MS),
    }

    def _validate_fields(self):
        if self._field_values['on_start']: assert self._field_values['gst_enable']


class CommandSetColor(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 0
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'green':            _Field([_FieldFragment(byte=3, offset=0, width=6, src_offset=2)], int),
        'red':              _Field([_FieldFragment(byte=4, offset=0, width=6, src_offset=2)], int),
        'blue':             _Field([_FieldFragment(byte=5, offset=0, width=6, src_offset=2)], int),
        'profile_id':       _Field([_FieldFragment(byte=6, offset=0, width=4)], int, default=0),
        'is_background':    _Field([_FieldFragment(byte=6, offset=4, width=1)], bool, default=False),
        'skip_display':     _Field([_FieldFragment(byte=6, offset=5, width=1)], bool, default=False),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }


class CommandSetGroupSel(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 1
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'green':            _Field([_FieldFragment(byte=3, offset=0, width=4, src_offset=4)], int, default=0),
        'red':              _Field([_FieldFragment(byte=3, offset=4, width=2, src_offset=4),
                                    _FieldFragment(byte=4, offset=0, width=2, src_offset=6)], int, default=0),
        'blue':             _Field([_FieldFragment(byte=4, offset=2, width=4, src_offset=4)], int, default=0),
        'group_sel':        _Field([_FieldFragment(byte=5, offset=0, width=3)], int),
        'skip_display':     _Field([_FieldFragment(byte=6, offset=5, width=1)], bool, default=False),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }


class CommandSetGroupId(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 2
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'green':            _Field([_FieldFragment(byte=3, offset=0, width=4, src_offset=4)], int, default=0),
        'red':              _Field([_FieldFragment(byte=3, offset=4, width=2, src_offset=4),
                                    _FieldFragment(byte=4, offset=0, width=2, src_offset=6)], int, default=0),
        'blue':             _Field([_FieldFragment(byte=4, offset=2, width=4, src_offset=4)], int, default=0),
        'group_sel':        _Field([_FieldFragment(byte=5, offset=0, width=3)], int),
        'new_group_id':     _Field([_FieldFragment(byte=6, offset=0, width=5)], int),
        'skip_display':     _Field([_FieldFragment(byte=6, offset=5, width=1)], bool, default=False),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }

    def _validate_fields(self):
        # Group ID needs to be 1 or higher
        assert self._field_values['new_group_id'] > 0


class CommandSetRepeatDelayTime(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 7
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'repeat_delay':     _Field([_FieldFragment(byte=6, offset=0, width=3)], Time),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }


class CommandSetRepeatCount(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 8
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'repeat_count':     _Field([_FieldFragment(byte=5, offset=0, width=6),
                                    _FieldFragment(byte=6, offset=0, width=2, src_offset=6)], int),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }

    def _validate_fields(self):
        assert self._field_values['repeat_count'] <= 255 # Max value that fits into 1 byte


class CommandSetGlobalSustainTime(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 9
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'global_sustain':   _Field([_FieldFragment(byte=4, offset=0, width=3)], GlobalSustainTime),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }


class CommandSingleColor12Bit(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 12
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'green':            _Field([_FieldFragment(byte=3, offset=0, width=4, src_offset=4)], int, default=0),
        'red':              _Field([_FieldFragment(byte=3, offset=4, width=2, src_offset=4),
                                    _FieldFragment(byte=4, offset=0, width=2, src_offset=6)], int, default=0),
        'blue':             _Field([_FieldFragment(byte=4, offset=2, width=4, src_offset=4)], int, default=0),
        '_byte_5':          _Field([_FieldFragment(byte=5, offset=0, width=6)], int, default=0b000001, read_only=True),
        '_byte_6':          _Field([_FieldFragment(byte=6, offset=0, width=6)], int, default=0b001000, read_only=True),
    }

class CommandSetOffReset(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 15
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'nreset':           _Field([_FieldFragment(byte=6, offset=5, width=1)], bool),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }
