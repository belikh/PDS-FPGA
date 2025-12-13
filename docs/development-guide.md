# Development Guide

## Repository Structure

```
nubus-to-ztex-gateware/
├── se30_bus.py        # Core PDS Bus Bridge logic
├── se30_soc.py        # Top-level SoC definition
├── ztex213_se30.py    # Platform pinout definition
├── test_se30_bus.py   # Standalone bus simulation
└── ...                # Other NuBus/Legacy files
```

## Running Tests

The primary way to verify logic changes is through simulation.

### Bus Logic Simulation

The `test_se30_bus.py` script simulates the `SE30PDS` module using Migen's simulator.

```bash
python3 nubus-to-ztex-gateware/test_se30_bus.py
```

**What it tests:**
1. **Slave Read**: Checks if the FPGA responds to a Mac read cycle with correct data and `/DSACK`.
2. **Interrupts**: Checks if writing to the `irq_out` CSR asserts the correct physical pin.
3. **Slave Write**: Checks if the FPGA accepts data from the Mac.
4. **Master DMA**: Checks if the FPGA can arbitrate for the bus and perform a write cycle.
5. **Bus Error**: Checks if the FPGA handles external `/BERR` assertions during DMA.

### Troubleshooting Simulation

- **"Data Out mismatch"**: The simulation currently emits a warning about data mismatch during Read tests. This is a known artifact of the testbench setup and not necessarily a logic bug.
- **Waveforms**: You can modify `test_se30_bus.py` to dump VCD files for viewing in GTKWave.
  ```python
  run_simulation(dut, test_bench(...), vcd_name="sim.vcd")
  ```

## Adding a New Feature

**Example: Adding a new CSR**

1. **Modify `se30_soc.py`**:
   Inside `SE30Control`:
   ```python
   self.new_reg = CSRStorage(32, name="new_reg", reset=0)
   ```
2. **Update Documentation**: Add the new register to `docs/data-models.md`.
3. **Verify**: Run `se30_soc.py --no-compile` to ensure Migen accepts the new logic.

## Contribution Workflow

1. Fork the repository.
2. Create a feature branch.
3. Make changes and verify with `test_se30_bus.py`.
4. Submit a Pull Request.
