#!/usr/bin/env python3

from migen import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.interconnect import wishbone
# from litex.soc.cores.clock import CRG # Not in litex, in migen.genlib.io
from migen.genlib.io import CRG

from ztex213_se30 import SE30Platform
from se30_bus import SE30PDS

# ... (Import other necessary modules for Framebuffer/RAM if needed, or stick to basic SOC)
# For this task, I will create a basic SoC that exposes the SE30PDS bus to a RAM.

class SE30SoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6), **kwargs):
        platform = SE30Platform()

        # SoCCore init
        # LiteX recent versions require defining cpu_type explicitly to None if no CPU,
        # but also sometimes fails on CSR creation if arguments aren't right.
        # The error "Cannot extract CSR name from code" usually happens when instantiating CSRs
        # dynamically or inside a function without assignment to self.
        # But here it happens inside SoCCore.__init__ -> add_controller.
        # This might be an environment issue or version mismatch of LiteX.
        # I will try to pass standard args.

        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq,
                         cpu_type=None,
                         integrated_rom_size=0,
                         integrated_sram_size=0x2000,
                         integrated_main_ram_size=0,
                         **kwargs)

        # CRG
        self.submodules.crg = CRG(platform.request("clk48"))

        # Wishbone Masters from SE30 Bus
        self.wb_read = wishbone.Interface()
        self.wb_write = wishbone.Interface()
        self.wb_dma = wishbone.Interface()

        # Instantiate SE30 Bus Bridge
        self.submodules.se30_bridge = SE30PDS(self, platform, self.wb_read, self.wb_write, self.wb_dma)

        self.wb_master = wishbone.Interface()
        self.submodules.arbiter = wishbone.Arbiter([self.wb_read, self.wb_write], self.wb_master)

        self.bus.add_master(name="se30_pds", master=self.wb_master)

# Build Script
if __name__ == "__main__":
    soc = SE30SoC()
    builder = Builder(soc, output_dir="build/se30_soc")
    # Don't actually run build as we don't have Vivado
    builder.build(build_name="se30_fpga", run=False)
