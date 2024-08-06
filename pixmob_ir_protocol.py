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


class FieldTypeException(Exception):
    pass

class FieldKeyException(Exception):
    pass

class FieldReadOnlyException(Exception):
    pass


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

    def __init__(self, **field_values):
        self.field_values = field_values
        fields = type(self)._fields

        # Check for unexpected fields, field types, and modification of read-only fields
        for field_name, field_value in self.field_values.items():
            if field_name not in fields:
                raise FieldKeyException(f"Unexpected field: {field_name} = {field_value}")
            field = fields[field_name]
            if not isinstance(field_value, field.value_type):
                raise FieldTypeException(f"Field {field_name} type mismatch: " +
                    f"expected {field.value_type.__name__}, " +
                    f"received {type(field_value).__name__} (value: {field_value})")
            if field.read_only and field_value != field.default:
                raise FieldReadOnlyException(f"Field {field_name} may not be modified " +
                    f" from the default value of {field.default}")
        
        # Check for missing required fields
        # For missing fields with a default value defined, apply the default value
        missing_fields = set(fields.keys()).difference(self.field_values.keys())
        for field_name in list(missing_fields):
            field = fields[field_name]
            if field.default is not None:
                self.field_values[field_name] = field.default
                missing_fields.remove(field_name)
        if missing_fields:
            missing_fields = ", ".join(sorted(list(missing_fields)))
            raise FieldKeyException(f"Missing fields: {missing_fields}")
        
        # Additional command-specific validation
        self._validate_fields()

    def encode(self) -> list[int]:
        """
        Encode the command into IR string representation.
        """
        cls = type(self)
        buf = [0] * cls._num_bytes

        # Populate command type flags and magic values
        buf[0] = 0b10000000 # Magic value
        buf[2] = cls._flags_type << 1
        if len(buf) == 9 and hasattr(cls, '_action_id'):
            buf[7] = cls._action_id

        # Add user-defined fields
        for field_name, field in cls._fields.items():
            field_value = int(self.field_values[field_name])
            for fragment in field.fragments:
                # Extract and mask a portion of the field value
                fragment_value = field_value >> fragment.src_offset
                fragment_value &= (1 << fragment.width) - 1
                # Now shift to proper place; to be ORed with command byte
                fragment_value <<= fragment.offset
                buf[fragment.byte] |= fragment_value

        # Perform encoding and keep track of intermediate checksum
        checksum = 0
        for i in range(2, len(buf)):
            buf[i] = Command._encoding_map[buf[i]]
            checksum += buf[i]
        
        # Calculate final checksum, place into buffer
        checksum = (checksum >> 2) & 0x3F
        checksum = Command._encoding_map[checksum]
        buf[1] = checksum

        # Separate bits into IR sequence
        encoded_bits = []
        for b in buf:
            for i in range(8):
                # Don't insert leading 0's
                if encoded_bits or b & 0b1:
                    encoded_bits.append(b & 0b1)
                b >>= 1
        
        # Delete trailing 0's
        while encoded_bits[-1] == 0:
            encoded_bits.pop()

        return encoded_bits

    def _validate_fields(self):
        """
        Allow commands to define additional field validations.
        """
        pass
    
    def __init_subclass__(cls):
        Command._commands.append(cls)


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
        if self.field_values['on_start']: assert self.field_values['gst_enable']


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
        'set_post_release': _Field([_FieldFragment(byte=8, offset=5, width=1)], bool, default=False),
    }

    def _validate_fields(self):
        if self.field_values['on_start']: assert self.field_values['gst_enable']


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
        if self.field_values['on_start']: assert self.field_values['gst_enable']


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
        'nsave_eeprom':     _Field([_FieldFragment(byte=6, offset=4, width=1)], bool, default=False),
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
        assert self.field_values['new_group_id'] > 0


class CommandSetPostReleaseTime(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 7
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'post_release':     _Field([_FieldFragment(byte=6, offset=0, width=3)], Time),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }


class CommandSetEEPROM3(Command):
    _num_bytes  = 9
    _flags_type = 0b111
    _action_id  = 8
    _fields = {
        'on_start':         _Field([_FieldFragment(byte=2, offset=0, width=1)], bool, default=True, read_only=True),
        'gst_enable':       _Field([_FieldFragment(byte=2, offset=4, width=1)], bool, default=False),
        'eeprom_data':      _Field([_FieldFragment(byte=5, offset=0, width=6),
                                    _FieldFragment(byte=6, offset=0, width=2, src_offset=6)], int),
        'group_id':         _Field([_FieldFragment(byte=8, offset=0, width=5)], int, default=0),
    }


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
