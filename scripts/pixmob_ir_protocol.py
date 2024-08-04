# Probabilities
CHANCE_100_PCT      = 0b000
CHANCE_88_PCT       = 0b001
CHANCE_67_PCT       = 0b010
CHANCE_50_PCT       = 0b011
CHANCE_32_PCT       = 0b100
CHANCE_16_PCT       = 0b101
CHANCE_10_PCT       = 0b110
CHANCE_4_PCT        = 0b111

# Attack/Sustain/Release times
TIME_0MS            = 0b000
TIME_32MS           = 0b001
TIME_96MS           = 0b010
TIME_192MS          = 0b011
TIME_480MS          = 0b100
TIME_960MS          = 0b101
TIME_2400MS         = 0b110
TIME_3840MS         = 0b111

# Command stuff
COMMAND_HEADER      = 0b10000000
COMMAND_SIZE_6B     = 6
COMMAND_SIZE_9B     = 9

COMMAND_GSTEN       = 0b00010000
COMMAND_TYPE_00     = 0b00000000
COMMAND_TYPE_01     = 0b00000100
COMMAND_TYPE_11     = 0b00001100
COMMAND_NRGB        = 0b00000010
COMMAND_ONSTRT      = 0b00000001

# IR encoding map
IR_ENCODING_MAP = [
    0x21, 0x32, 0x54, 0x65, 0xa9, 0x9a, 0x6d, 0x29,
    0x56, 0x92, 0xa1, 0xb4, 0xb2, 0x84, 0x66, 0x2a,
    0x4c, 0x6a, 0xa6, 0x95, 0x62, 0x51, 0x42, 0x24,
    0x35, 0x46, 0x8a, 0xac, 0x8c, 0x6c, 0x2c, 0x4a,
    0x59, 0x86, 0xa4, 0xa2, 0x91, 0x64, 0x55, 0x44,
    0x22, 0x31, 0xb1, 0x52, 0x85, 0x96, 0xa5, 0x69,
    0x5a, 0x2d, 0x4d, 0x89, 0x45, 0x34, 0x61, 0x25,
    0x36, 0xad, 0x94, 0xaa, 0x8d, 0x49, 0x99, 0x26,
]


def _do_ir_encoding(buf):
    assert len(buf) == COMMAND_SIZE_6B or len(buf) == COMMAND_SIZE_9B

    checksum = 0
    encoded_bytes = [COMMAND_HEADER, 0] # second value is placeholder for checksum
    for i in range(2, len(buf)):
        b = buf[i]
        assert b < len(IR_ENCODING_MAP), f"Invalid command byte {hex(b)} at offset {i}"
        encoded_byte = IR_ENCODING_MAP[b]
        encoded_bytes.append(encoded_byte)
        checksum += encoded_byte
    
    checksum = (checksum >> 2) & 0b111111
    encoded_bytes[1] = IR_ENCODING_MAP[checksum]

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


def command_rgb_single(red, green, blue,
                       attack=None, sustain=None, release=None,
                       chance=None):
    """
    Display a single RGB color.

    Optionally, specify all of attack, sustain, release, and chance.
    """
    if (attack is not None or
            sustain is not None or
            release is not None or
            chance is not None):
        buf = [0] * COMMAND_SIZE_9B

        # All four options must be set for the extended RGB command
        assert attack is not None, "Attack time must be set"
        assert sustain is not None, "Sustain time must be set"
        assert release is not None, "Release time must be set"
        assert chance is not None, "Chance must be set"

        buf[6] = ((attack & 0x07) << 3) | (chance & 0x07)
        buf[7] = ((release & 0x07) << 3) | (sustain & 0x07)
    else:
        buf = [0] * COMMAND_SIZE_6B
    
    buf[3] = (green >> 2) & 0x3F
    buf[4] = (red   >> 2) & 0x3F
    buf[5] = (blue  >> 2) & 0x3F

    return _do_ir_encoding(buf)


def command_rgb_doubleflash(red1, green1, blue1,
                            red2, green2, blue2):
    """
    Display two RGB colors back-to-back.

    The first color is shown for only approximately 25ms (this is not configurable).
    The second color is shown for slightly longer.
    """
    buf = [0] * COMMAND_SIZE_9B
    buf[2] = COMMAND_TYPE_01
    buf[3] = (green1 >> 2) & 0x3F
    buf[4] = (red1   >> 2) & 0x3F
    buf[5] = (blue1  >> 2) & 0x3F
    buf[6] = (green2 >> 2) & 0x3F
    buf[7] = (red2   >> 2) & 0x3F
    buf[8] = (blue2  >> 2) & 0x3F

    return _do_ir_encoding(buf)


def command_set_rgb_profile_eeprom(red, green, blue, profile_id):
    """
    Save a RGB profile to EEPROM.
    """
    # SKIP_DISPLAY prevents the color from showing when saving the profile to EEPROM
    SKIP_DISPLAY = 0b00100000
    buf = [0] * COMMAND_SIZE_9B
    buf[2] = COMMAND_TYPE_11 | COMMAND_NRGB | COMMAND_ONSTRT
    buf[3] = (green >> 2) & 0x3F
    buf[4] = (red   >> 2) & 0x3F
    buf[5] = (blue  >> 2) & 0x3F
    buf[6] = SKIP_DISPLAY | (profile_id & 0xF)

    return _do_ir_encoding(buf)


def command_set_on_start_effect(attack, sustain, release,
                                is_random,
                                profile_range_low, profile_range_high):
    """
    Enable "on-start" effect to cycle through profiles stored in EEPROM.

    profile_range_low:  starting profile_id
    profile_range_high: ending profile_id
    is_random:          True to select a random profile_id within the defined range,
                        False to cycle through the range sequentially
    """
    profile_range = ((profile_range_high & 0xF) << 4) | (profile_range_low & 0xF)
    buf = [0] * COMMAND_SIZE_6B
    buf[2] = COMMAND_GSTEN | COMMAND_NRGB | COMMAND_ONSTRT
    buf[3] = profile_range & 0x3F
    buf[4] = ((attack & 0x07) << 3) | ((int(is_random) & 0x01) << 2) | ((profile_range >> 6) & 0x03)
    buf[5] = ((release & 0x07) << 3) | (sustain & 0x07)

    return _do_ir_encoding(buf)
