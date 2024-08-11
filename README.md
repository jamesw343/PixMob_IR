# PixMob Reverse Engineering

## Introduction

The reverse engineering in this repository efforts were primarily performed on a PixMob PALM v2.6r1 (c) 20230629 and PixMob VIC v2.3r1 (c) 20211206.


## EEPROM
The EEPROM on my PixMob PALM v2.6r1 (c) 20230629 was marked `24C02`, which is a 2Kbit (256 x 8 bits) I2C chip.

### EEPROM Layout
Only the first 88 bytes of the EEPROM are used to store information. The remaining 168 bytes are left blank (0xFF) and not touched by the firmware.

The high-level layout of the EEPROM is as follows (each cell in the diagram is 8 bits / 1 byte):
```
             0x00                0x01                0x02                0x03        
     +-------------------+-------------------+-------------------+-------------------+
0x00 |       magic       |     group sel     |   repeat delay    |   repeat count    |
     +-------------------+-------------------+-------------------+-------------------+
0x04 |     on start      |     NOT USED      |     NOT USED      |     NOT USED      |
     +-------------------+-------------------+-------------------+-------------------+
0x08 |  group sel 0 id   |  group sel 1 id   |  group sel 2 id   |  group sel 3 id   |
     +-------------------+-------------------+-------------------+-------------------+
0x0C |  group sel 4 id   |  group sel 5 id   |  group sel 6 id   |  group sel 7 id   |
     +-------------------+-------------------+-------------------+-------------------+
0x10 |  profle 0 green   |   profile 0 red   |  profile 0 blue   | profile 0 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x14 |  profle 1 green   |   profile 1 red   |  profile 1 blue   | profile 1 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x18 |  profle 2 green   |   profile 2 red   |  profile 2 blue   | profile 2 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x1C |  profle 3 green   |   profile 3 red   |  profile 3 blue   | profile 3 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x20 |  profle 4 green   |   profile 4 red   |  profile 4 blue   | profile 4 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x24 |  profle 5 green   |   profile 5 red   |  profile 5 blue   | profile 5 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x28 |  profle 6 green   |   profile 6 red   |  profile 6 blue   | profile 6 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x2C |  profle 7 green   |   profile 7 red   |  profile 7 blue   | profile 7 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x30 |  profle 8 green   |   profile 8 red   |  profile 8 blue   | profile 8 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x34 |  profle 9 green   |   profile 9 red   |  profile 9 blue   | profile 9 chksum  |
     +-------------------+-------------------+-------------------+-------------------+
0x38 |  profle 10 green  |  profile 10 red   |  profile 10 blue  | profile 10 chksum |
     +-------------------+-------------------+-------------------+-------------------+
0x3C |  profle 11 green  |  profile 11 red   |  profile 11 blue  | profile 11 chksum |
     +-------------------+-------------------+-------------------+-------------------+
0x40 |  profle 12 green  |  profile 12 red   |  profile 12 blue  | profile 12 chksum |
     +-------------------+-------------------+-------------------+-------------------+
0x44 |  profle 13 green  |  profile 13 red   |  profile 13 blue  | profile 13 chksum |
     +-------------------+-------------------+-------------------+-------------------+
0x48 |  profle 14 green  |  profile 14 red   |  profile 14 blue  | profile 14 chksum |
     +-------------------+-------------------+-------------------+-------------------+
0x4C |  profle 15 green  |  profile 15 red   |  profile 15 blue  | profile 15 chksum |
     +-------------------+-------------------+-------------------+-------------------+
0x50 |   static green    |    static red     |    static blue    |      attack       |
     +-------------------+-------------------+-------------------+-------------------+
0x54 |      sustain      |      release      |   profile range   |       mode        |
     +-------------------+-------------------+-------------------+-------------------+
```

Fields:
* `magic`: A constant  value that  is specific to the firmware running on the PixMob's MCU. An unexpected value here will cause the MCU to set the EEPROM back to factory defaults.
* `group sel`: Indirect [group id](#ir-command-fields-group-id) selection. The lower 3 bits selects one of eight `group sel [0-7] id` fields.
* `repeat delay`: Defines the LED repeat delay phase time with a 16ms step. For example, a value of 0x1E would be 480ms. If repeat is enabled, the PixMob will display the background color (or no color) between repeats of the command color.
* `repeat count`: Defines the number of times a color is repeated after receiving a command with repeat mode enabled.
* `group sel [0-7] id`: The lower 5 bits select the [group id](#ir-command-fields-group-id) the PixMob unit is a part of.
* `on start`: When set to 0x11, will enable the "on-start" effect. This effect will cause the PixMob to start displaying colors as soon as it receives power, without needing to receive any IR commands.
* `profile [0-15]`: Defines 16 RGB color profiles that the MCU can access without needing to receive an IR command. The green, red, and blue fields hold the RGB values 0-255. The checksum field is 8 lower bits of the sum of green+red+blue.
* `static green`, `static red`, and `static blue`: Defines a special RGB profile that is used in static mode (see below). There is no checksum for the static RGB profile.
* `attack`, `sustain`, and `release`: Defines the LED fade-in time, hold time, and fade-out time, respectively, with a 16ms step. Used by the "on-start" effect. For example, a value of 0x1E would be 480ms.
* `profile range`: Defines the lower and upper bounds on the profile id when running in sequential and random mode (see below). The lower 4 bits of this field is the lower bound profile id, while the upper 4 bits of this field is the upper bound profile id.
* `mode`: Mode for the "on-start" effect. If "on-start" effect is not enabled (via the `on start` field), this field is ignored and nothing will happen when the PixMob receives power.
  * Static (0x00): Cycle the same RGB value defined by `static green`, `static red`, and `static blue`. `attack`, `sustain`, and `release` values are honored, but `profile range` is ignored.
  * Sequential (0x02): Cycle the profiles starting at the lower bound profile id defined by `profile range` up to the upper bound profile id defined by `profile range`, then repeat starting back at the lower bound.
  * Random (0x06): Cycle the profiles, each time picking a random profile id between the lower and upper bound profile ids defined by `profile range`.
  * Further use of the remaining possible values are still under investigation.


### EEPROM Factory Defaults
An unexpected `magic` value will cause the MCU to reset the EEPROM to factory defaults.

On the newer PixMob PALM v2.6r1 and PixMob VIC v2.3r1 with 24C02 EEPROMs with `magic=0x09`:

```
0x09 0x00 0x00 0x01
0x00 0x00 0x00 0x00
0x01 0x01 0x01 0x01
0x01 0x01 0x01 0x01
0x00 0xBF 0x00 0xBF
0x00 0xBF 0x60 0x1F
0x00 0x60 0xBF 0x1F
0x00 0x00 0xBF 0xBF
0xBF 0x00 0xBF 0x7E
0xBF 0x00 0x00 0xBF
0xBF 0xBF 0x00 0x7E
0x60 0xBF 0x00 0x1F
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0xBF 0xBF 0xBF 0x3D
0x00 0x00 0x00 0x1E
0x1E 0x1E 0x70 0x06
```

On the older PixMob VIC v2.3r1 with AKI** EEPROMS with `magic=0x07`:

```
0x07 0x00 0x00 0x01
0x00 0x00 0x00 0x00
0x01 0x01 0x01 0x01
0x01 0x01 0x01 0x01
0x00 0xCC 0x00 0xCC
0x00 0xCC 0x66 0x32
0x00 0x66 0xCC 0x32
0x00 0x00 0xCC 0xCC
0xCC 0x00 0xCC 0x98
0xCC 0x00 0x00 0xCC
0xCC 0xCC 0x00 0x98
0x66 0xCC 0x00 0x32
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0x00 0x00 0x00 0x00
0xCC 0xCC 0xCC 0x64
0x00 0x00 0x00 0x1E
0x1E 0x1E 0x70 0x06
```


## MCU RAM

### RGB Config (CFG*)
The 8 bytes at EEPROM address 0x50 to 0x57 collectively form a RGB config struct. Within the MCU register memory (RAM), there exists three instances of the RGB config struct (same format as within the EEPROM table):
* CFG0: The "staging" config. Generally, data from received IR commands are first stored into CFG0.
* CFG1: The "active" config. When the PixMob is ready to display a color, data is generally copied into CFG1 either from CFG0 or CFG2. The PWM cycles are then based off CFG1.
* CFG2: The "storage" config. During initial power-on, data from the EEPROM at 0x50-0x57 are copied into CFG2.

The last byte of each RGB config struct contains the mode flags:
```
     7         6         5         4         3         2         1         0     
+---------+---------+---------+---------+---------+---------+---------+---------+
|   ???   |   ???   |   ???   |  /bgen  |   ???   | random  | dynamic |  rpen   |
+---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `rpen`: When set to 1'b1, enables LED color repeat.
* `dynamic`: When set to 1'b1, causes colors to be selected based off the `profile range` configuration. Otherwise, when set to 1'b0, the only color used is configured by the `static green`, `static red`, and `static blue` fields.
* `random`: When set to 1'b1, causes profiles to be selected at random. Otherwise, profiles are select sequentially. Has no effect when `dynamic=1'b0`.
* `/bgen`: When set to 1'b0, the configured background color will be displayed during the LED init and repeat delay phases. Otherwise, the LED is turned off during these phases.


### Global Sustain Time (GST): 
This is a single 8-bit value that is occasionally used to override the sustain timer. Like other timers, each step represents a 16ms time increment.

During initial power-on, the GST is initialized to be 0x1E (480ms). It can then be updated through the [set GST IR command](#ir-command-set-gst).


## LED Phase FSM
Displaying a color on the PixMob goes through several states in a LED phase FSM:

### LED Phase: Init
The PixMob LED FSM remains in the init phase until it is ready to display the next color (either the on-start effect is enabled, a new command is received, or if repeat is enabled and the current repeat count is less than `repeat count` from the EEPROM).

If dynamic mode is enabled, read the RGB values of the next profile (either random or sequential profile ids) from EEPROM and store them into CFG1 memory. Otherwise, the current RGB values in CFG1 memory are used.

If a background color was previously set, it will continue to display until the end of the init phase.

If the PixMob remains in this phase for approximately 60 seconds with no new commands being received, there is a timeout where the LEDs are turned off and the MCU goes into sleep / power saving mode.

Next phase: [LED Phase: Attack](#led-phase-attack)


### LED Phase: Attack
Over a period defined by the attack time in CFG1, transition the last-displayed LED color to color defined in CFG1 memory. If the last displayed color is rgb(0, 0, 0), this creates a fade-in effect. Otherwise, for non-zero rgb values, this creates a smooth transition from one color to the next.

Next phase: [LED Phase: Sustain](#led-phase-sustain)


### LED Phase: Sustain
Over a period defined by the sustain time in CFG1, display the color defined in CFG1 memory.

Next phase: [LED Phase: Release](#led-phase-release)


### LED Phase: Release
Over a period defined by the release time in CFG1, transition the LED from the color defined in CFG1 memory to either the background color (when `/bgen=1'b0`) or OFF (when `/bgen=1'b1`).

A fade-out effect is created when `/bgen=1'b1` or the background color is rgb(0, 0, 0). If the background color is non-zero and different from the CFG1 color, there is a smooth transition between the two colors. Finally, if the background color is the same as the CFG1 color, then the color is maintained with no visible effect.

If the release time is configured to be zero, then the saved background color is overridden to be the current color defined in CFG1 memory.

If a background color was set, it will continue to display after the release phase ends.

Next phase: If the LED repeat is enabled by CFG1 mode settings (`rpen=1'b1`), [LED Phase: Repeat Delay](#led-phase-repeat-delay), otherwise [LED Phase: Init](#led-phase-init).


### LED Phase: Repeat Delay
Do nothing for a period of time defined by the repeat delay time in EEPROM. This phase serves as a brief delay between repeat cycles of the same color.

If a background color was previously set by the release phase, this color will continue to display both during and after this phase.

Next phase: [LED Phase: Init](#led-phase-init)


## IR Commands

### IR Command Header
All PixMob IR commands begin with the same 3-byte header, with the first byte being a magic constant, the second byte being [a computed checksum](#ir-command-encoding--checksum-calculation), and the third byte containing a series of flags that determine the format of the command body.

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x00 |    1    |    0    |    0    |    0    |    0    |    0    |    0    |    0    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x01 |                                   checksum                                    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x02 |    0    |    0    |   ???   |  gsten  |            type             | onstrt  |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Starting from the command byte located at offset 0x02, only the lower 6 bits of each command byte are used. The upper 2 bits MUST be zero. This is because PixMob uses 6-bit values when transmitting data over DMX for their lighting controllers (likely to reduce the total number of required channels).

Fields:
* `gsten`: At least one of its functions is to override the sustain time from [GST memory](#global-sustain-time-gst). Exact details still under investigation.
* `type`: In conjunction with the total length of the command, determines the format of the command body.
* `onstrt`: Set to 1'b1 to enable (or keep enabled) the "on-start" effect. If the "on-start" effect is currently enabled and a command is received with `onstrt=0`, the "on-start" effect will be disabled.


### IR Command: Display Single Color
Briefly display a single color.

The RGB values will be stored in CFG0 memory's static profile. The attack and release timers are always 0ms and 32ms, respectively. If `gsten=1'b1`, then the sustain time is set from [GST memory](#global-sustain-time-gst). Otherwise, sustain time is set at 384ms.

Flags: `type=3'b000`, (`onstrt=1'b1` and `gsten=1'b1`) or (`onstrt=1'b0` and `gsten=1'bX`)

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |                        green[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |                         red[7:2]                          |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |                         blue[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

> [!NOTE]
> Only the upper 6 bits of each RGB value are present in the command. The lower 2 bits are implicitly zero.


### IR Command: Display Single Color (Configurable Fields)
Briefly display a single color, but with additional configurable fields such as attack, sustain, release, and chance.

The RGB values along with the attack, sustain, and release timers will be stored in CFG0 memory.

Flags: `type=3'b000`, (`onstrt=1'b1` and `gsten=1'b1`) or (`onstrt=1'b0` and `gsten=1'bX`)

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |                        green[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |                         red[7:2]                          |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |                         blue[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |           attack            |           chance            |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |           release           |           sustain           |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |  rpen   |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `attack`, `sustain`, and `release`: See [IR Command Fields: Attack, Sustain, and Release](#ir-command-fields-attack-sustain-and-release)
* `chance`: See [IR Command Fields: Chance](#ir-command-fields-chance)
* `restrict group id`: See [IR Command Fields: Restrict Group ID](#ir-command-fields-restrict-group-id)
* `rpen`: If equal to 1'b1, enables LED repeat mode in CFG0. The color will be repeated `repeat count` (taken from EEPROM, set via another command) times with a delay of `repeat delay` (also stored in EEPROM and set via another command) between each repeat.


### IR Command: Display Two Colors
Color 1 is briefly displayed for approximately 25ms with no attack or release timers (these intervals are not user-configurable), followed by Color 2 for a slightly longer period. The RGB values of Color 2 are saved in CFG0 memory.

The attack and release timers on Color 2 are always set at 32ms. If `gsten=1'b1`, then the sustain time for Color 2 is set from [GST memory](#global-sustain-time-gst). Otherwise, sustain time for Color 2 is set at 384ms.

Flags: `type=3'b010`, `onstrt=1'b0`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |                        green1[7:2]                        |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |                         red1[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |                        blue1[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |                        green2[7:2]                        |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |                         red2[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |                        blue2[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```


### IR Command: Set Config
Set configuration options into CFG0 memory. Will also enable the dynamic mode flag in CFG0 mode. If flags `onstrt=1'b1`, the updated CFG0 memory is also saved to the EEPROM.

Flags: `type=3'b001`, (`onstrt=1'b1` and `gsten=1'b1`) or (`onstrt=1'b0` and `gsten=1'bX`)

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |                    profile range[5:0]                     |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |           attack            | random  |profile range[7:6] |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |           release           |           sustain           |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `profile range`: Split between command bytes 0x03 and 0x04. Same format as `profile range` in EEPROM.
* `random`: Enables random cycling mode when set to 1'b1, otherwise cycling is sequential.
* `attack`, `sustain`, and `release`: See [IR Command Fields: Attack, Sustain, and Release](#ir-command-fields-attack-sustain-and-release)


### IR Command: Set Color
Set RGB color to either a color profile in EEPROM or set the background color in memory.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |                        green[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |                         red[7:2]                          |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |                         blue[7:2]                         |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    | skpdisp |  setbg  |              profile id               |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    0    |    0    |    0    |    0    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `skpdisp` When set to 1, the PixMob will be "silent" and not display the color when the command is received. Otherwise, when set to 0, the color will be briefly displayed at the time the command is received.
* `setbg`: When set to 1'b0, the color profile is saved to the EEPROM at the specified profile id. Otherwise, when set to 1'b1, the RGB values are saved as the background color.
* `profile id`: The index of the profile within EEPROM to save to. Valid values are 0 to 15. Ignored when `setbg=1'b1`.
* `restrict group id`: See [IR Command Fields: Restrict Group ID](#ir-command-fields-restrict-group-id)


### IR Command: Set Group Sel / Change Group
Change the PixMob device's group by setting the `group sel` field in EEPROM.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |     red[5:4]      |               green[7:4]              |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |               blue[7:4]               |     red[7:6]      |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |          group sel          |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    | skpdisp |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    0    |    0    |    0    |    1    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `green`, `red`, and `blue` is a compacted 12-bit RGB that is copied into CFG0 memory.
* `group sel`: Changes the group id selection. The new `group sel` value is written to EEPROM and the corresponding new `group id` is read from EEPROM at the selected offset.
* `skpdisp` When set to 1, the PixMob will be "silent" and not display the color when the command is received. Otherwise, when set to 0, the color will be briefly displayed at the time the command is received.
* `restrict group id`: See [IR Command Fields: Restrict Group ID](#ir-command-fields-restrict-group-id)

> [!NOTE]
> The group id matching takes place prior to command execution. In other words, the `group id` field will match against the old group id, not the new one the PixMob is being updated to.


### IR Command: Set Group ID
Set one of eight group ids in the EEPROM.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |     red[5:4]      |               green[7:4]              |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |               blue[7:4]               |     red[7:6]      |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |          group sel          |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    | skpdisp |                  new group id                   |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    0    |    0    |    1    |    0    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `green`, `red`, and `blue` is a compacted 12-bit RGB that is copied into CFG0 memory.
* `group sel`: Selects which of the eight `group sel * id`s to change in the EEPROM.
* `new group id`: The new 5-bit group ID to write into the EEPROM.
* `skpdisp` When set to 1, the PixMob will be "silent" and not display the color when the command is received. Otherwise, when set to 0, the color will be briefly displayed at the time the command is received.
* `restrict group id`: See [IR Command Fields: Restrict Group ID](#ir-command-fields-restrict-group-id)

> [!WARNING]
> The PixMob does not update the cached group id in memory when executing this command. It is only written to the EEPROM. If the `group sel` field is changing the current group id, the PixMob still retains the old group id until either it is rebooted (and data re-read from EEPROM), or it receives a [change group command](#ir-command-change-group).

Special Cases:
* If `new group id=0`, the command will be discarded and nothing changed in EEPROM.


### IR Command: Set Repeat Delay Time
Set the LED repeat delay phase time. The value is saved to the EEPROM at address 0x02.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |    X    |    X    |    X    |            delay            |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    0    |    1    |    1    |    1    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `delay`: Time to spend in the LED repeat delay phase. Has the same lookup key as [IR Command Fields: Attack, Sustain, and Release](#ir-command-fields-attack-sustain-and-release).
* `restrict group id`: See [IR Command Fields: Restrict Group ID](#ir-command-fields-restrict-group-id)


### IR Command: Set Repeat Count
Set the LED repeat count. The value is saved to the EEPROM at address 0x03.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |                     repeat count[5:0]                     |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |    X    |    X    |    X    |    X    | repeat count[7:6] |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    1    |    0    |    0    |    0    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `repeat count`: Number of times to repeat a color.
* `restrict group id`: See [IR Command Fields: Restrict Group ID](#ir-command-fields-restrict-group-id)


### IR Command: Set GST
Set the [Global Sustain Time (GST)](#global-sustain-time-gst) memory.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |    X    |    X    |    X    |           gst key           |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    1    |    0    |    0    |    1    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

`gst key` is a 3-bit field used to index into the following table:

| Value  | Time (milliseconds) |
| :----: | :-----------------: |
| 3'b000 |           64        |
| 3'b001 |          112        |
| 3'b010 |          160        |
| 3'b011 |          208        |
| 3'b100 |          480        |
| 3'b101 |          960        |
| 3'b110 |        2,400        |
| 3'b111 |        3,840        |


### IR Command: Display Single Color (12-Bit RGB)
Another command to display a single color, except uses 12-bit RGB instead of 18-bit RGB.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |     red[5:4]      |               green[7:4]              |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |               blue[7:4]               |     red[7:6]      |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |    0    |    0    |    1    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |    0    |    0    |    1    |    0    |    0    |    0    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    1    |    1    |    0    |    0    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `green`, `red`, and `blue` is a compacted 12-bit RGB that is copied into CFG0 memory.


### IR Command: Do Reset
Interrupt the current operation; turn off LEDs; clear CFG0, CFG1, and CFG2; and optionally, reset certain global settings.

Flags: `type=3'b111`, `onstrt=1'b1`, `gsten=1'bX`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |  /grst  |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    1    |    1    |    1    |    1    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `/grst`: When set to 1'b0, in addition to turning off LEDs and clearing the CFG memories, the background color is cleared, the EEPROM data at addresses 0x02 and 0x03 are reset back to zero (`repeat delay` and `repeat count`), and the [global sustain time](#global-sustain-time-gst) is reset to 480ms.


### IR Command Fields: Attack, Sustain, and Release
The terms attack, sustain, and release are used to describe the LED fade-in time, hold time, and fade-out time, respectively. With some limited exceptions, the mapping of the 3-bit values are:

| Value  | Time (milliseconds) |
| :----: | :-----------------: |
| 3'b000 |            0        |
| 3'b001 |           32        |
| 3'b010 |           96        |
| 3'b011 |          192        |
| 3'b100 |          480        |
| 3'b101 |          960        |
| 3'b110 |        2,400        |
| 3'b111 |        3,840        |

Special Cases:
* If `sustain=3'b111` and `release!=3'b000`, then the sustain timer is set from [GST memory](#global-sustain-time-gst).
* If `release=3'b000`, then some type of multiplier is applied to the sustain time and the background color is set to the color from the command. Exact details are still under investigation.


### IR Command Fields: Chance
Chance refers to the probability that the command will be executed. The mapping of the 3-bit values are:

| Value | Probability (%) |
| :---: | :-------------: |
| 3'b000 |       100       |
| 3'b001 |        88       |
| 3'b010 |        67       |
| 3'b011 |        50       |
| 3'b100 |        32       |
| 3'b101 |        16       |
| 3'b110 |        10       |
| 3'b111 |         4       |


### IR Command Fields: Restrict Group ID
IR commands with a group id will restrict execution of the command only to PixMob devices in the matching group (determined by data in the EEPROM).

Special Cases:
* If `group id=0`, then the command is executed regardless of PixMob's current group id or group sel.


### IR Command Encoding & Checksum Calculation
A lookup table is used to transform a 6-bit command byte into an 8-bit encoded command byte.

Starting from the command byte at offset 0x02, the lower 6 bits of each command byte are used to index into the following table:

```c
0x21, 0x32, 0x54, 0x65, 0xa9, 0x9a, 0x6d, 0x29, /* 0x00 - 0x07 */
0x56, 0x92, 0xa1, 0xb4, 0xb2, 0x84, 0x66, 0x2a, /* 0x08 - 0x0F */
0x4c, 0x6a, 0xa6, 0x95, 0x62, 0x51, 0x42, 0x24, /* 0x10 - 0x17 */
0x35, 0x46, 0x8a, 0xac, 0x8c, 0x6c, 0x2c, 0x4a, /* 0x18 - 0x1F */
0x59, 0x86, 0xa4, 0xa2, 0x91, 0x64, 0x55, 0x44, /* 0x20 - 0x27 */
0x22, 0x31, 0xb1, 0x52, 0x85, 0x96, 0xa5, 0x69, /* 0x28 - 0x2F */
0x5a, 0x2d, 0x4d, 0x89, 0x45, 0x34, 0x61, 0x25, /* 0x30 - 0x37 */
0x36, 0xad, 0x94, 0xaa, 0x8d, 0x49, 0x99, 0x26, /* 0x38 - 0x3F */
```

The primary purpose of this encoding is likely to minimize the number of consecutive 1's and 0's both within and across neighboring command bytes being sent by the IR transmitter. Since the IR transmission is based on ~700 microsecond time-sliced segments, too many consecutive bits of the same value may be interpreted as loss of signal or interference.

> [!NOTE]
> The magic constant at command offset 0x00 is NOT encoded!

After encoding all command bytes except the magic constant at 0x00 and checksum at 0x01, the partial checksum can be calculated by summing the encoded command bytes. The final checksum is found by taking the upper 6 bits of the partial checksum and indexing into the encoding table above.

For example, suppose we want to send a [Display Single Color](#ir-command-display-single-color) command with rgb(0, 252, 192). The pre-encoded command would be:
```c
0x00: 1000 0000  /* magic constant                  */
0x01: XXXX XXXX  /* checksum to be calculated later */
0x02: 0000 0000  /* no command flags set            */
0x03: 0011 1111  /* green value msbs                */
0x04: 0000 0000  /* red value msbs                  */
0x05: 0011 0000  /* blue value msbs                 */
```

After applying the initial encoding to command bytes 0x02 through 0x05:
```c
0x00: 1000 0000  /* magic constant                  */
0x01: XXXX XXXX  /* checksum to be calculated later */
0x02: 0010 0001  /* tbl[6'b000000] = 8'b00100001    */
0x03: 0010 0110  /* tbl[6'b111111] = 8'b00100110    */
0x04: 0010 0001  /* tbl[6'b000000] = 8'b00100001    */
0x05: 0101 1010  /* tbl[6'b110000] = 8'b01011010    */
```

Now, the partial checksum can be calculated as `8'b00100001 + 8'b00100110 + 8'b00100001 + 8'b01011010 = 8'b11000010`. Index into the encoding table using the 6 upper bits of the partial checksum to get the final checksum: `checksum = tbl[6'b110000] = 8'b01011010`.

The final encoded command with checksum then is:
```c
0x00: 1000 0000
0x01: 0101 1010
0x02: 0010 0001
0x03: 0010 0110
0x04: 0010 0001
0x05: 0101 1010
```

The IR transmission starts from the least significant bit of the command and contiues through the encoded command bytes. Leading and trailing zeroes may optionally be removed, since there is no way for the IR receiver to distinguish a zero that is not surrounded by ones.

The final IR sequence would be: `[1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 1]` (the leading `0, 0, 0, 0, 0, 0, 0` from the magic constant and trailing `0` from encoded command byte 0x05 bit 7 was removed).
