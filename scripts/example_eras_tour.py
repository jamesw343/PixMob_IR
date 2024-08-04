import pixmob_ir_protocol as pmir

"""
Generate the IR commands to enable continuous cycling of eras tour colors.
"""

ir_commands = [
    pmir.command_set_rgb_profile_eeprom(0xC0, 0x64, 0x64, 0),
    pmir.command_set_rgb_profile_eeprom(0x98, 0xC0, 0x30, 1),
    pmir.command_set_rgb_profile_eeprom(0x64, 0xC0, 0xC0, 2),
    pmir.command_set_rgb_profile_eeprom(0x7C, 0xC0, 0xC0, 3),
    pmir.command_set_rgb_profile_eeprom(0x18, 0xC0, 0x18, 4),
    pmir.command_set_rgb_profile_eeprom(0xC0, 0x64, 0xC0, 5),
    pmir.command_set_rgb_profile_eeprom(0x00, 0x28, 0xC0, 6),
    pmir.command_set_rgb_profile_eeprom(0x38, 0x38, 0x38, 7),
    pmir.command_set_on_start_effect(
        attack=pmir.TIME_480MS, sustain=pmir.TIME_480MS, release=pmir.TIME_480MS,
        is_random=True,
        profile_range_low=0, profile_range_high=7
    ),
]

for ir_cmd in ir_commands:
    print(ir_cmd)