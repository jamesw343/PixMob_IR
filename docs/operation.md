# PixMob Operational Documentation
This document briefly describes some of PixMob's modes of operations, namely, the format of internal representations and states it goes through to receive IR commands and drive LED outputs.


## Configuration Structures (cfg)
The PixMob defines an 8-byte configuration structure that exists in both EEPROM (one instance) and the MCU's register-based RAM (three instances). The configuration structure stores settings such as the current operational mode, RGB colors, and timer values and its format is shown below:

```
          7         6         5         4         3         2         1         0     
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x00 |                                   rgb.green                                   |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x01 |                                    rgb.red                                    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x02 |                                   rgb.blue                                    |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x03 |                                  attack_time                                  |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x04 |                                 sustain_time                                  |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x05 |                                 release_time                                  |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x06 |           profile_range_hi            |           profile_range_lo            |
     +---------+---------+---------+---------+---------+---------+---------+---------+
0x07 |   ???   |   ???   |   ???   |  nbgen  |   ???   | random  | dynamic |  rpen   |
     +---------+---------+---------+---------+---------+---------+---------+---------+
```

The three instances of cfg in the MCU's register-based RAM will be labeled as `MCU:cfg0`, `MCU:cfg1`, and `MCU:cfg2`. The instance of CFG in EEPROM will be labeled as `EEPROM:cfg`.

| Identifier | Usage | Description |
| :--------: | :---: | :--------- |
| `MCU:cfg0` | Staging | As the PixMob receives data from an incoming IR command, fields are extracted from the command bytes, transformed if necessary, and stored into `MCU:cfg0` for staging.<br /><br />For example, 6-bit RGB values from a command are zero-padded at the LSBs to be converted into 8-bit RGB values, or 3-bit keys for the attack, sustain, and release time are applied to a lookup table to produce an 8-bit time value representing 16ms increments.<br /><br />However, not all fields from a command will necessary be staged into `MCU:cfg0`. Some fields may change other areas in the MCU's register-based memory, or cause bytes to be written directly into the EEPROM.<br /><br />When an incoming command is done being processed and the PixMob is ready to display the effect, the contents of `MCU:cfg0` are copied into `MCU:cfg1`. |
| `MCU:cfg1` | Active | Through a periodic loop, the LED FSM will read configuration values from `MCU:cfg1`, apply adjustments (e.g., for fade-in, fade-out, or transition between two colors), and use the results to drive the PWM outputs to the RGB LEDs. |
| `MCU:cfg2`<br /> and<br /> `EEPROM:cfg` | Storage | Stores configuration used in conjunction with the on-start effect.<br /><br />When the PixMob is first powered on and the on-start effect is enabled by a different setting in EEPROM, the device will copy data from `EEPROM:cfg` to `MCU:cfg2`. Thus, `MCU:cfg2` acts as a cache for `EEPROM:cfg` such that it is readily accessible by the program without a round trip to the EEPROM.<br /><br />When the PixMob is ready to display the next color profile effect in the on-start effect cycle, it copies the contents of `MCU:cfg2` into `MCU:cfg1` for the LED FSM to read from.<br /><br />For commands that update the on-start effect's configurations, the contents of `MCU:cfg0` will be copied into both `MCU:cfg2` and `EEPROM:cfg` after the command is done processing. |

Field Descriptions:
| Field | Name | Description |
| :-------: | :--: | :--------- |
| `cfg.rgb.green`<br /> `cfg.rgb.red`<br />`cfg.rgb.blue` | RGB Color Values | Stores an 8-bit RGB value for the color to be displayed.<br /><br />In the context of `EEPROM:cfg`, this value is generally not applicable since `cfg.dynamic` will always be 1 for configurations stored in the EEPROM. It is possible to manually write to the EEPROM with an I2C programmer to set `cfg.dynamic` to 0, in which case the PixMob will display a static color each cycle instead of iterating through profiles. However, this is not achievable using only IR commands. |
| `cfg.attack_time`<br /> `cfg.sustain_time`<br /> `cfg.release_time` | LED Phase Timer Values | The attack, sustain, and release times define the amount of time it takes for the PixMob to transition from the background color to the color being displayed, the amount of time to display the color, and the amount of time it takes for the PixMob to transition from the displayed color back to the background color, respectively.<br /><br />Times are stored as 8-bit values with each increment representing 16ms. For example, a time value of 0x1E (30d) would be equivalent to 480ms. |
| `cfg.profile_range_lo`<br /> `cfg.profile_range_hi` | Profile Range ID Bounds | When `cfg.dynamic` is 1, defines the lower and upper bounds of the profile id to dynamically select from. Otherwise has no effect. |
| `cfg.rpen` | Repeat Enable | When set to 1, enables effect repetition (the effect is replayed multiple times, with the number of times being defined by EEPROM:repeat_count). |
| `cfg.dynamic` | Dynamic RGB Colors Enable | When set to 1, the `cfg.rgb` fields are replaced with values loaded dynamically from a color profile stored in EEPROM based on the next profile id. |
| `cfg.random` | Random Color Profile ID Enable | When set to 1, the next profile id is selected randomly. Otherwise, the next profile id is the incremented last profile id with wraparound rules applied. |
| `cfg.nbgen` | Background Color Disable | When set to 1, instead of displaying the background color between effects, the LEDs will be turned off. Note that this same off-effect can be achieved visually by setting `cfg.nbgen` to 1, setting the background color to rgb(0, 0, 0), or both.


## Other MCU Registers/RAM
| Field | Name | Value at Power-On | Description |
| :---: | :--: | :---------------------------: | :--------- |
| `MCU:gst` | Global Sustain Time | 0x1E | This is a single 8-bit value that is occasionally used to override the sustain timer. Like other timers, each step represents a 16ms time increment. |
| `MCU:bg_rgb.green`<br /> `MCU:bg_rgb.red`<br />`MCU:bg_rgb.blue` | RGB Background Color Values | rgb(0, 0, 0) | When `MCU:cfg1.nbgen` is zero, defines the background color to transition into between effects. |
| `MCU:last_rgb.green`<br /> `MCU:last_rgb.red`<br />`MCU:last_rgb.blue` | RGB Last Displayed Color Values | rgb(0, 0, 0) | Used internally to keep track of the last-displayed color to aid in calculating transitions between one color and the next. |


## LED Phase FSM
Displaying a color on the PixMob goes through several states in a LED phase FSM:

| Phase | Next Phase(s) | Description |
| :---: | :------------ | :---------- |
| Init | Attack | The PixMob LED FSM remains in the init phase until it is ready to display the next color (either the on-start effect is enabled, a new command is received, or if repeat is enabled and the current repeat count is less than `EEPROM:repeat_count`).<br /><br />If `MCU:cfg1.dynamic` is 1, read the RGB values of the next profile (either random or sequential profile ids) from `EEPROM:profile_*` and store them into `MCU:cfg1.rgb`. Otherwise, the current values in `MCU:cfg1.rgb` are used.<br /><br />If a background color was previously set, it will continue to display until the end of the init phase.<br /><br />If the PixMob remains in this phase for approximately 60 seconds with no new commands being received, there is a timeout where the LEDs are turned off and the MCU goes into sleep / power saving mode. |
| Attack | Sustain | Over the period defined by `MCU:cfg1.attack_time`, transition from the color in `MCU:last_rgb` to `MCU:cfg1.rgb`.<br /><br />If `MCU:last_rgb` is rgb(0, 0, 0), this creates a fade-in effect. Otherwise, for non-zero rgb values, this creates a smooth transition from one color to the next. |
| Sustain | Release | Over the period defined by `MCU:cfg1.sustain_time`, display the color stored in `MCU:cfg1.rgb`. |
| Release | Repeat Delay<br /> (`MCU:cfg1.rpen` is 1)<br /><br /> -or-<br /><br /> Init<br /> (`MCU:cfg1.rpen` is 0) | Over the period defined by `MCU:cfg1.release_time`, transition from the color in `MCU:cfg1.rgb` to either `MCU:bg_rgb`, when `MCU:cfg1.nbgen` is 0, or rgb(0, 0, 0), when `MCU:cfg1.nbgen` is 1.<br /><br />A fade-out effect is created when `MCU:cfg1.nbgen` is 1 or the color is rgb(0, 0, 0). Otherwise, there will be a smooth transition between the two colors.<br /><br />If `MCU:cfg1.release_time` is zero, there is special behavior where `MCU:bg_rgb` is set to the values of `MCU:cfg1.rgb` (this essentially leaves the color effect turned on).<br /><br />If a background color was set, it will continue to display after the release phase ends. |
| Repeat Delay | Init | Over the period defined by `EEPROM:repeat_delay`, do nothing. This phase serves as a brief delay between repeat cycles of the same color.<br /><br />If a background color was previously set by the release phase, this color will continue to display both during and after this phase. |
