#!/usr/bin/env python3

import pixmob_ir_protocol as pmir

#
# Eras Tour: Go Home Sequence
#
# This will cycle through 8 different colors at random. Each color fades in and out for
# approximately 1.5 seconds with the LEDs turning off between colors.
#
print("\nEras Tour: Go Home Sequence")
eras_tour_ir_commands = [
    # Set 8 colors in profiles 0 through 7
    # Tell the PixMob to NOT display the color at the moment the command is received, only save it
    pmir.CommandSetColor(red=0xC0, green=0x64, blue=0x64, profile_id=0, skip_display=True),
    pmir.CommandSetColor(red=0x98, green=0xC0, blue=0x30, profile_id=1, skip_display=True),
    pmir.CommandSetColor(red=0x64, green=0xC0, blue=0xC0, profile_id=2, skip_display=True),
    pmir.CommandSetColor(red=0x7C, green=0xC0, blue=0xC0, profile_id=3, skip_display=True),
    pmir.CommandSetColor(red=0x18, green=0xC0, blue=0x18, profile_id=4, skip_display=True),
    pmir.CommandSetColor(red=0xC0, green=0x64, blue=0xC0, profile_id=5, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x28, blue=0xC0, profile_id=6, skip_display=True),
    pmir.CommandSetColor(red=0x38, green=0x38, blue=0x38, profile_id=7, skip_display=True),

    # Enable the on-start effect with random colors from profiles 0 through 7
    pmir.CommandSetConfig(
        on_start=True, gst_enable=True,
        profile_id_lo=0, profile_id_hi=7, is_random=True,
        attack=pmir.Time.TIME_480_MS,
        sustain=pmir.Time.TIME_480_MS,
        release=pmir.Time.TIME_480_MS
    ),
]
for ir_command in eras_tour_ir_commands:
    print(ir_command.encode())


#
# Color Blend
#
# This will cycle through 3 different colors sequentially, with each color blending
# directly into the next one (LEDs do not turn off in between colors).
#
print("\n\nColor Blend")
color_blend_ir_commands = [
    pmir.CommandSetColor(red=0xFF, green=0x00, blue=0x00, profile_id=0, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0xFF, blue=0x00, profile_id=1, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0xFF, profile_id=2, skip_display=True),

    # Enable the on-start effect with sequential colors from profiles 0 through 2
    # Setting release timer to 0ms enables the blend mode
    pmir.CommandSetConfig(
        on_start=True, gst_enable=True,
        profile_id_lo=0, profile_id_hi=2, is_random=False,
        attack=pmir.Time.TIME_480_MS,
        sustain=pmir.Time.TIME_480_MS,
        release=pmir.Time.TIME_0_MS
    ),
]
for ir_command in color_blend_ir_commands:
    print(ir_command.encode())


#
# Same Color Indefinitely
#
# Displays the same color indefinitely. Makes use of the on-start effect and color blend
# mode so there is no noticable change in colors.
#
print("\n\nSame Color Indefinitely")
same_color_ir_commands = [
    pmir.CommandSetColor(red=0x3F, green=0x3F, blue=0x3F, profile_id=0, skip_display=True),
    pmir.CommandSetConfig(
        on_start=True, gst_enable=True,
        profile_id_lo=0, profile_id_hi=0, is_random=False,
        attack=pmir.Time.TIME_960_MS,
        sustain=pmir.Time.TIME_960_MS,
        release=pmir.Time.TIME_0_MS
    ),
]
for ir_command in same_color_ir_commands:
    print(ir_command.encode())


#
# Single Color Fade-Out
#
# Display the single color for 960 milliseconds, then fade out and wait for the next command.
#
print("\n\nSingle Color")
single_color_ir_command = pmir.CommandSingleColorExt(
    red=0x40, green=0x00, blue=0x40,
    attack=pmir.Time.TIME_32_MS, # No fade-in time
    sustain=pmir.Time.TIME_960_MS,
    release=pmir.Time.TIME_480_MS, # Fade out over ~480 milliseconds
)
print(single_color_ir_command.encode())


#
# Groups
#
# Set up the PixMob to only respond to commands with a certain group id (or group id 0).
#
print("\n\nGroup Id")
group_id_commands = [
    # Set group sel 7 to group id 22
    pmir.CommandSetGroupId(group_sel=7, new_group_id=22),

    # Set group sel to 7, this changes the PixMob's group id to 22
    pmir.CommandSetGroupSel(group_sel=7),

    # Show a color to only devices in group id 22
    # The PixMob should respond to this command
    pmir.CommandSingleColorExt(
        red=0xFF, green=0x00, blue=0x00,
        attack=pmir.Time.TIME_0_MS,
        sustain=pmir.Time.TIME_96_MS,
        release=pmir.Time.TIME_32_MS,
        group_id=22
    ),

    # Now show a different color only to devices in group id 23
    # The PixMob should ignore this command since it's in group 22
    pmir.CommandSingleColorExt(
        red=0x00, green=0xFF, blue=0x00,
        attack=pmir.Time.TIME_0_MS,
        sustain=pmir.Time.TIME_96_MS,
        release=pmir.Time.TIME_32_MS,
        group_id=23
    ),

    # Finally, show a third color to all devices, regardless of their group
    # This is done by setting group_id=0 (or omitting it)
    # The PixMob should respond to this command
    pmir.CommandSingleColorExt(
        red=0x00, green=0x00, blue=0xFF,
        attack=pmir.Time.TIME_0_MS,
        sustain=pmir.Time.TIME_96_MS,
        release=pmir.Time.TIME_32_MS,
        group_id=0
    ),
]
for ir_command in group_id_commands:
    print(ir_command.encode())


#
# Repeat Effect
#
# These commands will cause a color effect to be repeated a defined
# number of times.
#
print("\n\nRepeat Effect")
repeat_commands = [
    # Configure a delay of 480ms between each effect repetition
    pmir.CommandSetRepeatDelayTime(repeat_delay=pmir.Time.TIME_480_MS),

    # Repeat 5 times
    pmir.CommandSetRepeatCount(repeat_count=5),

    # Effect with repeat enabled
    pmir.CommandSingleColorExt(
        red=0x00, green=0x40, blue=0x80,
        enable_repeat=True
    ),
]
for ir_command in repeat_commands:
    print(ir_command.encode())


#
# Background Color
#
# This will set a background color that is displayed when no active
# effect is currently being run.
#
print("\n\nBackground Color")
background_commands = [
    # Configure the background color as purple
    pmir.CommandSetColor(
        red=0x40, green=0x00, blue=0x40,
        is_background=True,
        skip_display=True
    ),

    # Now send a green color effect
    # After the green effect finishes, it should transition to the background color
    pmir.CommandSingleColorExt(red=0x00, green=0x40, blue=0x00),
]
for ir_command in background_commands:
    print(ir_command.encode())


#
# Two Color Cycle (Combined Repeat Effect + Background Color)
#
# We can achieve a two-color cycle by switching between an effect color and
# a background color in a repeat loop.
#
print("\n\nTwo Color Cycle (Combined Repeat Effect + Background Color)")
two_color_cycle_commands = [
    # Configure a delay of 480ms between each effect repetition
    pmir.CommandSetRepeatDelayTime(repeat_delay=pmir.Time.TIME_480_MS),

    # Repeat 5 times
    pmir.CommandSetRepeatCount(repeat_count=5),

    # Configure the background color as purple
    pmir.CommandSetColor(
        red=0x40, green=0x00, blue=0x40,
        is_background=True,
        skip_display=True
    ),

    # Now send a green color effect
    # It should alternate between the green and purple 5 times total
    # After the last repetition, it will remain on purple (the background color)
    pmir.CommandSingleColorExt(
        red=0x00, green=0x40, blue=0x00,
        enable_repeat=True
    ),
]
for ir_command in two_color_cycle_commands:
    print(ir_command.encode())


#
# Factory Reset
#
# These series of commands attempts to factory reset the PixMob's EEPROM
# The values were taken from a PixMob PALM v2.6r1 (c) 20230629
#
# Potentially useful if you were messing around with different IR commands
# that may have affected settings in the EEPROM.
#
print("\n\nFactory Reset:")
factory_reset_commands = [
    # Set group sel to 0
    pmir.CommandSetGroupSel(group_sel=0),

    # Set all group sel group ids to 1
    pmir.CommandSetGroupId(group_sel=0, new_group_id=1),
    pmir.CommandSetGroupId(group_sel=1, new_group_id=1),
    pmir.CommandSetGroupId(group_sel=2, new_group_id=1),
    pmir.CommandSetGroupId(group_sel=3, new_group_id=1),
    pmir.CommandSetGroupId(group_sel=4, new_group_id=1),
    pmir.CommandSetGroupId(group_sel=5, new_group_id=1),
    pmir.CommandSetGroupId(group_sel=6, new_group_id=1),
    pmir.CommandSetGroupId(group_sel=7, new_group_id=1),

    # Set the default color profiles
    pmir.CommandSetColor(red=0xBF, green=0x00, blue=0x00, profile_id=0, skip_display=True),
    pmir.CommandSetColor(red=0xBF, green=0x00, blue=0x60, profile_id=1, skip_display=True),
    pmir.CommandSetColor(red=0x60, green=0x00, blue=0xBF, profile_id=2, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0xBF, profile_id=3, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0xBF, blue=0xBF, profile_id=4, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0xBF, blue=0x00, profile_id=5, skip_display=True),
    pmir.CommandSetColor(red=0xBF, green=0xBF, blue=0x00, profile_id=6, skip_display=True),
    pmir.CommandSetColor(red=0xBF, green=0x60, blue=0x00, profile_id=7, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0x00, profile_id=8, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0x00, profile_id=9, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0x00, profile_id=10, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0x00, profile_id=11, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0x00, profile_id=12, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0x00, profile_id=13, skip_display=True),
    pmir.CommandSetColor(red=0x00, green=0x00, blue=0x00, profile_id=14, skip_display=True),
    pmir.CommandSetColor(red=0xBF, green=0xBF, blue=0xBF, profile_id=15, skip_display=True),

    # Do Reset
    pmir.CommandDoReset(nreset=True),
]
for ir_command in factory_reset_commands:
    print(ir_command.encode())


#
# Decode Commands
#
# The decode feature allows you to input an IR string and figure out which command it maps to
#
print("\n\nDecode Commands")
encoded_bits = [1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1]
print(f"Encoded Bits:    {encoded_bits}")
print(f"Decoded Command: {pmir.Command.decode(encoded_bits)}")
