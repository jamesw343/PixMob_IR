# Nyquest NY8A054E MCU Firmware Dumper
Arduino program designed to extract the firmware from a Nyquest NY8A054E 8-bit MCU.

This program has been tested on the following PixMob boards:
* PixMob PALM v2.6r1 (c) 20230629 with 24C02 EEPROM chip
* PixMob VIC v2.3r1 (c) 20211206 with 24C02 EEPROM chip

> [!NOTE]
> This dumper does not work with PixMob VIC v2.3r1 (c) 20211206 boards using an EEPROM marked AKI**. Based on EEPROM data, these boards are likely running an older firmware version and may have the "protect" bit enabled during factory programming.

The NY8 family of 8-bit MCUs use a proprietary programming protocol and can only be written to using Nyquest's custom NY8 OTP Writer programming tool, which is expensive and only available from overseas vendors. Luckily, someone had posted [logic analyzer captures of the NY8 programming process](https://www.eevblog.com/forum/blog/eevblog-1144-padauk-programmer-reverse-engineering/msg4434847/#msg4434847) online, which this program is based upon.

## Usage
The MCU is connected directly to the Arduino using a SOIC 8-pin test clip:
* MCU SDI to Arduino Pin 2
* MCU SDO to Arduino Pin 3
* MCU SCK to Arduino Pin 4
* MCU VDD to Arduino Pin 5
* MCU VSS to Arduino GND

<img src="hardware_setup.jpg" width="600">

The programming sequence requires that a special handshake be sent within a certain time frame after MCU power-on, so the Arduino must control power to the MCU.

The PixMob board design has a diode between the battery Vin and the MCU VDD, while the LEDs are connected directly to the battery Vin. This allows us to operate the MCU directly from the Arduino without exceeding any digital output pins' current limits.

Once wired, connect to the Arduino serial monitor and press "\<Enter>" to begin the EPROM extraction process. If successful, 2K x 14-bit EPROM words will be dumped.

```
Ready. Press enter to run.
Begin EPROM extraction ...

389F 0000 0000 0000 0000 0000 0000 0000
00C7 15C7 0103 00C8 0104 00C9 0101 080F
...
0000 0000 0000 0000 0000 0000 0000 0000
0000 0000 0000 0000 0000 0000 3FE9 16B0
```

> [!NOTE]
> To avoid copyright issues, the dumped firmware will not be included in this repository.

If you have trouble copying the output from the Arduino IDE's serial console, try using another serial console like PuTTY instead.

Now, the output can be converted into binary and analyzed in [Ghidra](https://github.com/NationalSecurityAgency/ghidra) with the [Ghidra NY8A054E Processor](https://github.com/Lyphiard/Ghidra_NY8A054E).

```bash
$ xxd -r -p pixmob_firmware.hex > pixmob_firmware.bin
```