#define PIN_SDI         2
#define PIN_SDO         3
#define PIN_SCK         4
#define PIN_VDD         5
#define PIN_VPP_SENSE   6

// If dumping the MCU is unsuccessful without Vpp, try re-running
// with this set to 1. Follow README.md for hardware setup details.
#define MCU_REQUIRES_VPP 0

static_assert(PIN_SCK < 8);
static_assert(PIN_SDI < 8);
static_assert(PIN_SDO < 8);
static_assert(PIN_VDD < 8);
static_assert(PIN_VPP_SENSE < 8);

#define SET_PIN_HIGH(pin)   (PORTD |= 1 << (pin))
#define SET_PIN_LOW(pin)    (PORTD &= ~(1 << (pin)))
#define SET_PIN(pin, val)   (val) ? SET_PIN_HIGH(pin) : SET_PIN_LOW(pin)
#define GET_PIN(pin)        (PIND & (1 << (pin)))

#define DELAY_NANO(delay)   __builtin_avr_delay_cycles(((double) (delay)) * F_CPU / 1e9)
#define DELAY_MICRO(delay)  DELAY_NANO(1000.0 * (delay))
#define DELAY_MILLI(delay)  DELAY_MICRO(1000.0 * (delay))

uint8_t send_receive_byte(uint8_t data_out)
{
    uint8_t mask = 1 << 7; // MSB first
    SET_PIN(PIN_SDI, data_out & mask);
    DELAY_MICRO(1); // Ensure sufficient setup time

    uint8_t data_in = 0;
    do {
        if (GET_PIN(PIN_SDO)) {
            data_in |= mask;
        }

        // Toggle clock
        SET_PIN_HIGH(PIN_SCK);

        // Update SDI for next cycle
        // Slow Arduino should be sufficient to satisfy hold times
        mask >>= 1;
        SET_PIN(PIN_SDI, data_out & mask);

        DELAY_NANO(500);

        SET_PIN_LOW(PIN_SCK);

        DELAY_NANO(500);
    } while (mask);

    return data_in;
}

inline void ny8_send_command_separator()
{
    // SDO must be high here, or the reset won't happen properly
    SET_PIN_HIGH(PIN_SDI);
    DELAY_MICRO(1); // Setup time

    // Toggle clock
    SET_PIN_HIGH(PIN_SCK);
    DELAY_NANO(500);
    SET_PIN_LOW(PIN_SCK);

    SET_PIN_LOW(PIN_SDI);

    DELAY_MICRO(50);
}

void ny8_send_handshake()
{
    send_receive_byte(0x53);
    DELAY_MICRO(1.5);
    send_receive_byte(0xAD);
}

void ny8_dump_eprom()
{
    // Send 0x20 0x00 0x00 0x00 for (EPROM read command)
    // In the programming timings for the NY8A051H, only 3 bytes
    // are sent and received here. However, the NY8A054E used by
    // the PixMob appears to send and receive 4 bytes, maybe due
    // to a 2K EPROM instead of 1K?
    send_receive_byte(0x20);
    send_receive_byte(0x00);
    send_receive_byte(0x00);
    send_receive_byte(0x00);

    // Read 2048 words
    for (int i = 0; i < 2048; i++) {
        // EPROM words are 14 bits and split across two reads
        uint8_t b1 = send_receive_byte(0x00);
        uint8_t b2 = send_receive_byte(0x00);

        // Combine lower 7 bits of each byte
        uint16_t word = ((b1 & 0x7F) << 7) | (b2 & 0x7F);

        // Invert the bits to get actual instruction/data
        word = (~word) & 0x3FFF;

        char buf[16];
        snprintf(buf, sizeof(buf), "%04X%s",
            word, i % 8 == 7 ? "\r\n" : " ");
        Serial.print(buf);
    }

    Serial.print("\r\n\r\n");
}

void setup()
{
    pinMode(PIN_SDI, OUTPUT);
    pinMode(PIN_SDO, INPUT);
    pinMode(PIN_SCK, OUTPUT);
    pinMode(PIN_VDD, OUTPUT);

#if MCU_REQUIRES_VPP
    pinMode(PIN_VPP_SENSE, INPUT);
#endif

    SET_PIN_LOW(PIN_VDD);

    Serial.begin(115200);
}

void loop()
{
#if MCU_REQUIRES_VPP
    Serial.println("Ready. Waiting for VPP sense...");
    // Wait in loop (debounce) until VPP_SENSE pin goes high
    for (int i = 0; i < 10; i++) {
        while (GET_PIN(PIN_VPP_SENSE) == 0);
    }
#else
    Serial.println("Ready. Press enter to run.");
    // Wait for trigger from serial console
    while (true) {
        if (Serial.available() > 0) {
            int c = Serial.read();

            // Look for <enter> to start program
            if (c == '\n' || c == '\r') {
                // Drain remaining characters
                while (Serial.available() > 0) {
                    Serial.read();
                }

                break;
            }
        }
    }
#endif

    Serial.println("Begin EPROM extraction ...\r\n");

    noInterrupts();
    
    // Power on
    SET_PIN_HIGH(PIN_VDD);
    SET_PIN_LOW(PIN_SCK);
    SET_PIN_LOW(PIN_SDI);

    DELAY_MICRO(500);

    // Handshake
    ny8_send_handshake();

    // Wait 100 milliseconds to determine whether the handshake succeeded.
    // Under normal operation, the MCU starts running the program about
    // 62 milliseconds after power-on. If programming handshake is successful,
    // the MCU enters a special mode and the user program is not started.
    DELAY_MILLI(100);

    if (GET_PIN(PIN_SDO)) {
        // Handshake unsuccessful
        // SDO (shared with a PWM output) has become PWM active high
        Serial.println("EPROM dump failed: handshake unsuccessful.\r\n\r\n");
    } else {
        // EPROM extraction
        ny8_dump_eprom();

        // If running multiple commands, send a command separator
        // between each command
        ny8_send_command_separator();

        Serial.println("Done!\r\n\r\n");
    }

    // Power off
    SET_PIN_LOW(PIN_VDD);

    interrupts();

#if MCU_REQUIRES_VPP
    // Wait in loop (debounce) until VPP_SENSE pin goes low
    for (int i = 0; i < 10; i++) {
        while (GET_PIN(PIN_VPP_SENSE) != 0);
    }
#endif
}
