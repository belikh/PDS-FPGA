# Getting Started

## Prerequisites

To build and simulate the gateware, you need a Linux environment (Ubuntu 20.04+ recommended) with the following tools:

### Python Dependencies

The project relies on `migen` and `litex`.

```bash
pip3 install migen litex
```

### FPGA Toolchain

For synthesis, you need **Xilinx Vivado**.
- Install Vivado WebPACK (free) or Standard/Enterprise edition.
- Ensure `vivado` is in your PATH.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/nubus-to-ztex-gateware.git
   cd nubus-to-ztex-gateware
   ```

2. **Verify Environment**:
   Ensure you can run the SoC script help command:
   ```bash
   python3 nubus-to-ztex-gateware/se30_soc.py --help
   ```

## Running Simulations

The project includes a standalone testbench for the bus logic.

```bash
python3 nubus-to-ztex-gateware/test_se30_bus.py
```

You should see output indicating successful Read, Write, Interrupt, and DMA tests.

## Building the Bitstream

To build the FPGA bitstream for the ZTex 2.13 board:

```bash
python3 nubus-to-ztex-gateware/se30_soc.py --build
```

This will generate the bitstream in `build/se30_soc/gateware/se30_soc.bit`.
