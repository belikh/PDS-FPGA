# SE30 PDS Bridge Module

**File**: `se30_bus.py`

## Purpose
The `SE30PDS` module acts as a bidirectional bridge between the asynchronous Motorola 68030 PDS bus and the internal synchronous Wishbone bus. It handles signal synchronization, bus arbitration, and protocol translation.

## Interfaces

### Platform Signals
Directly mapped to FPGA pins (see `ztex213_se30.py`).
- **Address/Data**: `pds_a_3v3_n` (32-bit), `pds_d_3v3_n` (32-bit)
- **Control**: `/AS`, `/DS`, `R/W`, `/DSACK0`, `/DSACK1`, `SIZ0`, `SIZ1`, `/BERR`
- **Arbitration**: `/BR`, `/BG`, `/BGACK`
- **Interrupts**: `/IRQ1`, `/IRQ2`, `/IRQ3` (mapped via `irq_3v3_n`)

### Wishbone Interfaces
- **`wb_read` (Master)**: Initiates internal WB reads when Mac CPU reads from FPGA.
- **`wb_write` (Master)**: Initiates internal WB writes when Mac CPU writes to FPGA.
- **`wb_dma` (Slave)**: Receives WB requests from internal masters to perform DMA on the Mac bus. *Note: In code this is implemented as a Master interface driving the PDS bus, but conceptually it services internal requests.*

## Finite State Machines (FSMs)

### Slave FSM (Mac accessing FPGA)
Handles `READ` and `WRITE` cycles.
1. **IDLE**: Waits for falling edge of `/AS` and matching Slot Address (0xF9, 0xFA, 0xFB).
2. **READ/WRITE_REQ**: Initiates Wishbone cycle.
3. **DRIVE/ACK**: Drives data (on read) and asserts `/DSACK`.
4. **COMPLETE**: Waits for `/AS` negation.

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> READ_WB_REQ: /AS Low & Read
    IDLE --> WRITE_WAIT_DS: /AS Low & Write

    READ_WB_REQ --> READ_DRIVE: WB Ack
    READ_DRIVE --> IDLE: /AS High

    WRITE_WAIT_DS --> WRITE_WB_REQ: /DS Low
    WRITE_WB_REQ --> WRITE_ACK: WB Ack
    WRITE_ACK --> IDLE: /AS High
```

### Master FSM (FPGA DMA to Mac)
Handles Bus Arbitration and Transfer.
1. **Arbitration**: Asserts `/BR`, waits for `/BG`, asserts `/BGACK`.
2. **Transfer**: Drives Address/Control, asserts `/AS` & `/DS`.
3. **Wait**: Waits for `/DSACK` or `/BERR`.
4. **Release**: Releases Bus.

## Implementation Details

### Signal Synchronization
All asynchronous inputs (`/AS`, `/DS`, Address, etc.) are synchronized using `migen.genlib.cdc.MultiReg` to the system clock domain to prevent metastability.

### Open-Drain Emulation
Signals like `/IRQ`, `/BR`, `/BGACK`, and Data Bus (in some modes) use `Tristate` primitives to emulate Open-Drain/Bidirectional behavior.

### Address Decoding
The Slave logic decodes addresses starting with:
- `0xF9xxxxxx` (Slot 9)
- `0xFAxxxxxx` (Slot A)
- `0xFBxxxxxx` (Slot B)

### Byte Lane Selection
Logic converts `SIZ0`, `SIZ1`, `A0`, `A1` into Wishbone `SEL` signals to support Byte, Word, and Long Word accesses.
