# Troubleshooting

## Common Issues

### Simulation

**Issue: "FAIL: DSACK not asserted within timeout"**
- **Cause**: The internal Wishbone bus did not acknowledge the request in time.
- **Fix**: Check if the requested address matches the memory map. In `se30_bus.py`, addresses `0xF9...` are decoded as valid slots.

**Issue: "FAIL: Master did not drive bus"**
- **Cause**: The arbitration logic failed.
- **Fix**: Ensure `/BG` (Bus Grant) is asserted (Low) by the testbench after `/BR` is asserted.

### Hardware

**Issue: Mac hangs at startup**
- **Cause**: FPGA might be driving `/DSACK` or `/BERR` inappropriately, or causing bus contention.
- **Fix**: Check `se30_bus.py` tristate logic. Ensure `slave_dsack_oe` is only high when the FPGA is addressed.

**Issue: DMA transfers are corrupt**
- **Cause**: Timing violations on signals crossing domains.
- **Fix**: The PDS bus is asynchronous. `se30_bus.py` uses `MultiReg` for synchronization. Ensure all critical control signals (`/AS`, `/DS`, `R/W`) are synchronized.

**Issue: Interrupts not triggering**
- **Cause**: Incorrect polarity.
- **Fix**: The 68030 interrupts are Active Low. The logic uses Open Drain simulation (`irq_3v3_n`). Ensure `irq_out` CSR bits are set to `1` to drive the pin Low.

## Logs & Diagnostics

- **Vivado Logs**: Check `build/se30_soc/vivado.log` for synthesis warnings, especially related to Timing Constraints.
- **Simulation Output**: `test_se30_bus.py` prints step-by-step status.
