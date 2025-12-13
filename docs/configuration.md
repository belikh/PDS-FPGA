# Configuration

## Platform Configuration (`ztex213_se30.py`)

The platform definition file controls the physical interface.

- **`_se30_pds_io`**: Defines the pin mapping for all PDS signals. Modify this list if the adapter board layout changes.
- **`_se30_peripherals`**: Defines extra peripherals like USB (not currently used) and SD Card.

## SoC Configuration (`se30_soc.py`)

- **`sys_clk_freq`**: Default is 100 MHz. Can be changed via command line argument `--sys-clk-freq`.
- **SRAM Size**: Currently set to 8KB (`integrated_sram_size=0x2000`).

## Environment Variables

The build process uses standard LiteX and Vivado environment variables.

- **`PATH`**: Must include the path to `vivado`.

## CSR Configuration

The Control Status Registers (CSRs) are defined in `SE30SoC.SE30Control`.

- **`irq_out`**:
    - 3-bit register.
    - Write `1` to a bit to assert the corresponding interrupt (Active Low on bus).
    - `Bit 0` = `/IRQ1`
    - `Bit 1` = `/IRQ2`
    - `Bit 2` = `/IRQ3`
