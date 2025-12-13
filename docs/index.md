# SE/30 PDS FPGA Gateware

## Overview

This project implements an FPGA gateware for the Macintosh SE/30 Processor Direct Slot (PDS), utilizing a ZTex USB-FPGA Module 2.13 (Artix-7). It enables the Macintosh SE/30 to interface with modern peripherals and memory resources provided by the FPGA.

The core of the project is a bridge between the Motorola 68030 PDS bus and an internal Wishbone bus, allowing for:
- **Slave Operation**: The Macintosh CPU can access FPGA resources (CSRs, SRAM).
- **Master Operation (DMA)**: The FPGA can initiate Direct Memory Access (DMA) transfers to/from Macintosh system memory.
- **Interrupts**: The FPGA can trigger hardware interrupts on the SE/30.

## Key Features

- **PDS to Wishbone Bridge**: Bidirectional bridge handling 68030 bus cycles.
- **DMA Support**: Full bus arbitration (BR/BG/BGACK) for mastering the bus.
- **SoC Integration**: Built on LiteX/Migen for easy integration of standard cores.
- **Simulation**: Comprehensive testbench for verifying bus logic.

## Documentation

- [Getting Started](getting-started.md): Installation and setup.
- [Architecture](architecture.md): High-level system design.
- [Modules](modules/index.md): Detailed module documentation.
- [Data Models](data-models.md): Memory maps and signal definitions.
- [Development Guide](development-guide.md): Testing and contributing.
