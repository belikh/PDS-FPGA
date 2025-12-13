# SE30 SoC Module

**File**: `se30_soc.py`

## Purpose
The `SE30SoC` class defines the top-level System-on-Chip. It configures the platform, clocking, and connects the `SE30PDS` bridge to the internal bus.

## Components

### Clock Recovery Generator (`_CRG`)
- **Input**: 48 MHz (from ZTex onboard oscillator).
- **PLL**: Xilinx MMCM.
- **Outputs**:
    - `sys_clk`: 100 MHz (System Clock)
    - `sys4x`, `sys4x_dqs`: For SDRAM (if used)
    - `idelay`: 200 MHz (For IDELAYCTRL)

### Bus Architecture
- **Type**: Wishbone.
- **Masters**:
    - `se30_read`: Driven by PDS Slave Read logic.
    - `se30_write`: Driven by PDS Slave Write logic.
    - `se30_dma`: Internal master for DMA (Placeholder).
- **Slaves**:
    - `sram`: Internal Block RAM (8KB).
    - `control`: Control CSRs.

### Control CSRs (`SE30Control`)
Allows software (via the Mac) to interact with the FPGA configuration.

| Register | Address Offset | Access | Description |
| :--- | :--- | :--- | :--- |
| `scratch` | 0x00 | RW | Scratchpad register for testing. |
| `irq_out` | 0x04 | RW | Interrupt Request Output. Bit 0->/IRQ1, Bit 1->/IRQ2, Bit 2->/IRQ3. |

## Build System
The script uses `litex.soc.integration.builder` to generate the synthesis files and run Vivado.

```bash
# Build command
python3 nubus-to-ztex-gateware/se30_soc.py --build --sys-clk-freq 100000000
```
