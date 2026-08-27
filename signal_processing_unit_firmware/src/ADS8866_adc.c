// Copyright (c) 2026    ScalinQ AB
//
// This software is released under the MIT License. 
// <https://opensource.org/licenses/MIT>

#include "ADS8866_adc.h"

#include "config.h"

#include "pico/stdlib.h"
#include "hardware/spi.h"
 
// Global variable that checks time since pico bootup
static uint64_t conversion_start_time;

void init_ads8866(void) {

    // Initilize the spi1 port
    spi_init(SPI_ADC1, 2000000);
    spi_set_format(SPI_ADC1, 16, SPI_CPOL_0, SPI_CPHA_1, SPI_MSB_FIRST);

    // Configure SCLK and MISO pins
    gpio_set_function(ADC1_SCLK, GPIO_FUNC_SPI);
    gpio_set_function(ADC1_MISO, GPIO_FUNC_SPI);

    // Configure the CONVST (conversion stage) pin as a GPIO-pin
    // This pin will act as a Chip - Select pin in this SPI configuration
    // Data conversion will start on a CONVST rising edge, so default should be low
    gpio_init(ADC1_CONVST);
    gpio_set_dir(ADC1_CONVST, GPIO_OUT);
    gpio_put(ADC1_CONVST, 0); 

    // The ADC works in 3-wire configuration, and MOSI will set high during the entire conversion 
    gpio_init(ADC1_MOSI);
    gpio_set_dir(ADC1_MOSI, GPIO_OUT);
    gpio_put(ADC1_MOSI, 1); 
}

void ads8866_start_conversion(void) {
    // Make sure MOSI is pulled high
    gpio_put(ADC1_MOSI, 1);
    
    // Pull CONVST high to start conversion
    gpio_put(ADC1_CONVST, 1);

    // Record a timestamp to ensure sufficient time has passed before reading the adc value
    conversion_start_time = time_us_64();
}

float ads8866_get_voltage(void) {
    uint16_t adc_data = 0;
    float voltage = 0.0f;
    
    // Calculate how much time has passed since conversion started
    uint64_t current_time = time_us_64();
    uint64_t elapsed_time = current_time - conversion_start_time;
    
    // Wait for the remainder of the 10us minimum conversion time if we arrived too early
    if (elapsed_time < 10) {
        sleep_us(10 - elapsed_time);
    }

    // Pull CONVST low to act as Chip Select and bring DOUT out of 3-state
    gpio_put(ADC1_CONVST, 0);
    
    // Read the 16-bit conversion result from the SPI bus
    spi_read16_blocking(SPI_ADC1, 0x0000, &adc_data, 1);

    // Convert the 16-bit digital code to a physical voltage
    // The ADS8866 is a 16-bit ADC, thus a resolution of 65536 bits.
    voltage = (float)adc_data * (ADC_VOLTAGE_REFERENCE / 65536.0f);
    
    // Return the calculated voltage
    return voltage; 
}