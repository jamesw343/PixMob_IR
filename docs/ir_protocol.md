# PixMob IR Protocol
PixMob IR commands are either 6 or 9 bytes in length, comprised of a 3-byte header and a 3 or 6-byte body.

## IR Command Header
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
* `gsten`: At least one of its functions is to override the effect's sustain time with the global sustain time (stored in `MCU:gst`). Exact details still under investigation.
* `type`: In conjunction with the total length of the command, determines the format of the command body.
* `onstrt`: Set to 1 to enable (or keep enabled) the "on-start" effect. If the "on-start" effect is currently enabled and a command is received with `onstrt` is 0, the "on-start" effect will be disabled.


### IR Command: Display Single Color
Briefly display a single color.

The RGB values are stored in `MCU:cfg0.rgb`. `MCU:cfg0.attack_time` and `MCU:cfg0.release_time` are always set at 0ms and 32ms, respectively. If `gsten` is 1, `MCU:cfg0.release_time` is set to `MCU:gst`, otherwise it is set at 384ms.

Flags: `type=3'b000`, (`onstrt=1` and `gsten=1`) or (`onstrt=0` and `gsten=X`)

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

The RGB values along with the attack, sustain, and release timers will be stored in `MCU:cfg0`.

Flags: `type=3'b000`, (`onstrt=1` and `gsten=1`) or (`onstrt=0` and `gsten=X`)

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
* `rpen`: If equal to 1, enables LED repeat mode in CFG0. The color will be repeated `EEPROM:repeat_count` times with a delay of `EEPROM:repeat_delay` between each repeat.


### IR Command: Display Two Colors
Color 1 is briefly displayed for approximately 25ms with no attack or release timers (these intervals are not user-configurable), followed by Color 2 for a slightly longer period. The RGB values of Color 2 are saved to `MCU:cfg0`.

The attack and release timers on Color 2 are always set at 32ms. If `gsten` is 1, then the sustain time for Color 2 is set from `MCU:gst`. Otherwise, sustain time for Color 2 is set at 384ms.

Flags: `type=3'b010`, `onstrt=0`, `gsten=X`

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
Set configuration options into `MCU:cfg0`. Will also set `MCU:cfg0.dynamic` to 1. If flags `onstrt` is 1, the updated `MCU:cfg0` is also copied to the `EEPROM:cfg`.

Flags: `type=3'b001`, (`onstrt=1` and `gsten=1`) or (`onstrt=0` and `gsten=X`)

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
* `random`: Enables random cycling mode when set to 1, otherwise cycling is sequential.
* `attack`, `sustain`, and `release`: See [IR Command Fields: Attack, Sustain, and Release](#ir-command-fields-attack-sustain-and-release)


### IR Command: Set Color
Set RGB color to either a color profile in EEPROM or set the background color in memory.

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

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
* `setbg`: When set to 0, the color profile is saved to the EEPROM at the specified profile id. Otherwise, when set to 1, the RGB values are saved as the background color.
* `profile id`: The index of the profile within EEPROM to save to. Valid values are 0 to 15. Ignored when `setbg=1`.
* `restrict group id`: See [IR Command Fields: Restrict Group ID](#ir-command-fields-restrict-group-id)


### IR Command: Set Group Sel / Change Group
Change the PixMob device's group by setting `EEPROM:group_sel`.

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

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

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

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
Set the value `EEPROM:repeat_delay` to the specified delay.

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

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
Set the value `EEPROM:repeat_count` to the specified count.

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

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
Set the value `MCU:gst` to the specified time.

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

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


### IR Command: Identify Firmware Version
Conditionally display the specified RGB color if and only if the PixMob is running the specified firmware version.

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |     red[5:4]      |               green[7:4]              |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |               blue[7:4]               |     red[7:6]      |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |    0    |    0    |    1    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |                     firmware version                      |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    1    |    1    |    0    |    0    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `green`, `red`, and `blue` is a compacted 12-bit RGB that is copied into `MCU:cfg0`.
* `firmware version`: Check [Device Models](../README.md#devices-models) for PCB and firmware version combinations.


### IR Command: Do Reset
Interrupt the current operation; turn off LEDs; clear `MCU:cfg0`, `MCU:cfg1`, and `MCU:cfg2`; and optionally, reset certain global settings.

Flags: `type=3'b111`, `onstrt=1`, `gsten=X`

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |    0    |    0    |    X    |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |    0    |    0    |  ngrst  |    X    |    X    |    X    |    X    |    X    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |    0    |    0    |    0    |    0    |    1    |    1    |    1    |    1    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x08 |    0    |    0    |    X    |                restrict group id                |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

Fields:
* `ngrst`: When set to 0, in addition to turning off LEDs and clearing `MCU:cfg0`, `MCU:cfg1`, and `MCU:cfg2`, `MCU:bg_rgb` is also cleared, `EEPROM:repeat_delay` and `EEPROM:repeat_count` are set to 0, and `MCU:gst` is reset back to 480ms.


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
* If `sustain=3'b111` and `release!=3'b000`, then the sustain timer is set from `MCU:gst`.
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
