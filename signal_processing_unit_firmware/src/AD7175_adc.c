// Copyright (c) 2026    Claes Astrabeck, Julius Berg, David Björkman, Nils Palm, Daniel Rising, Hugo Sahlin
// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "AD7175_adc.h"

#include "config.h"
#include "current_control.h"

#include "pico/stdlib.h"
#include "hardware/spi.h"

// =====================================================================================================================
// Static (Private)
// =====================================================================================================================

static void ad7175_write_reg16(uint8_t reg, uint16_t value) {
    uint8_t buf[3];
    buf[0] = 0x00 | (reg & 0x3F); // 0x00 (WEN=0, R/W=0) + Register Address
    buf[1] = (value >> 8) & 0xFF; // MSB
    buf[2] = value & 0xFF;        // LSB

    spi_write_blocking(SPI_ADC0, buf, 3);
}

// =====================================================================================================================
// API (Public)
// =====================================================================================================================

int32_t volatile zeroed_offset_binary = 0x800000;

void init_ad7175() {

    spi_init(SPI_ADC0, 1000 * 1000 * 16);
    spi_set_format(SPI_ADC0, 8, SPI_CPOL_1, SPI_CPHA_1, SPI_MSB_FIRST);
    
    gpio_set_function(ADC0_MISO, GPIO_FUNC_SPI);
    gpio_set_function(ADC0_SCLK,  GPIO_FUNC_SPI);
    gpio_set_function(ADC0_MOSI, GPIO_FUNC_SPI);

    // SYNC/ERR pin is default high for the ADC to be active
    gpio_init(ADC0_SYNC_ERR);
    gpio_set_dir(ADC0_SYNC_ERR, GPIO_OUT);
    gpio_put(ADC0_SYNC_ERR, 1);
}

void configure_ad7175(void){

    // Force reset the ADC
    uint8_t reset_cmd[8] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    spi_write_blocking(SPI_ADC0, reset_cmd, 8);
    sleep_ms(10);  

    // 1. Configure Channel 0 (REG_CH0: 0x10)
    // Bit 15 = 1: CH_EN0 (Enable Channel)
    // Bits 11:10 = 00: SETUP_SEL (Use Setup 0)
    // Bits 9:5 = 00000: AINPOS0 (AIN0)
    // Bits 4:0 = 00001: AINNEG0 (AIN1) -> Connect AIN1 to Ground
    // Hex Calculation: 0x8000 | 0x0001 = 0x8001
    ad7175_write_reg16(AD7175_REG_CH0, 0x8001); 

    // 2. Configure Setup 0 (REG_SETUPCON0: 0x20)
    // Bit 12 = 1: BI_UNIPOLAR (Bipolar coding)
    // Bits 11:10 = 11: REF_BUF+ and REF_BUF- enabled
    // Bits 9:8 = 11: AIN_BUF+ and AIN_BUF- enabled
    // Bit 7 = 0: BURNOUT_EN0 not enabled
    // Bit 6 = reserved
    // Bits 5:4 = 10: REF_SEL, Internal 2.5V reference
    // Hex Calculation: 0x1000 | 0x0C00 | 0x0300 | 0x0020 = 0x1F20
    ad7175_write_reg16(AD7175_REG_SETUPCON0, 0x1F20);
    
    // 3. Setup Filter (REG_FILTCON0: 0x28)
    // Bit 15: SINC3_MAP0 = 0 (some filter mapping I don't really understand. We don't want it)
    // Bit 11: ENHFILTEN0 = 0: Disable digital filters
    // Bits 10:8 = 000: These bits configure digital filters. We don't use those filters, so these bits are irrelevant
    // Bits 6:5 = 00: Sets the digital filter to Sinc5 + Sinc1. We don't use the digital filters
    // Bits 4:0 = 00000: Sets output data rate to 250 kSps
    ad7175_write_reg16(AD7175_REG_FILTCON0, 0x0000); 

    // 4. ADC Mode (REG_ADCMODE: 0x01)
    // Bit 15: 1: Enables internal reference
    // Bits 10:8 = 000: Sets the measurement delay to 0 µs
    // Bits 6:4 = 000: Sets conversion mode to continous 
    // Bits 3:2 = 00: Sets internal oscillator
    ad7175_write_reg16(AD7175_REG_ADCMODE, 0x8000); 

    // 5. Interface Mode (REG_IFMODE: 0x02)
    // Bit 12 = 0: Disables the use of the Sync/Error pin as a chip-select pin
    // Bit 11 = 0: IOSTRENGTH, In use with a low IOVDD supply
    // Bit 8 = 0: DOUT reset bit
    // Bit 7: CONT_READ = 1 (Continuous Read mode - eliminates command overhead)
    // Disable all other functions
    ad7175_write_reg16(AD7175_REG_IFMODE, 0x0080);
}

uint32_t ad7175_fast_read() {
    uint8_t rx[3];
    // Read 3 bytes directly without sending a register address first, assumes continous conversion on the ADC
    spi_read_blocking(SPI_ADC0, 0x00, rx, 3);
    return ((uint32_t)rx[0] << 16) | ((uint32_t)rx[1] << 8) | rx[2];
}

void ad7175_set_zero() {
    int64_t sum = 0;
    int32_t count = 0;

    for (int i = 0; i < 56000; i++) {
        while (gpio_get(ADC0_MISO));

        int32_t sample = ad7175_fast_read() - 0x800000;
        // Avoid transients when zeroing against the modulated signal.
        if (modulation_state_stable && axis_state_stable) {
            sum += sample;
            count++;
        }
    }

    int32_t average = 0;
    if (count != 0) {
        average = sum / count;
    }
    zeroed_offset_binary = 0x800000 + average;
}
