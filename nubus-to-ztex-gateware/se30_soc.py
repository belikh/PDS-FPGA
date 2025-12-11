#!/usr/bin/env python3

import os
import argparse
import sys

from migen import *
from litex.build.generic_platform import *
from litex.build.xilinx.vivado import vivado_build_args, vivado_build_argdict
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import AutoCSR, CSRStorage
from litex.soc.integration.builder import *
from litex.soc.interconnect import wishbone
from litex.soc.cores.clock import *
from litex.soc.cores.led import LedChaser

from ztex213_se30 import SE30Platform
from se30_bus import SE30PDS

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module, AutoCSR):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys = ClockDomain("sys")
        self.clock_domains.cd_sys4x = ClockDomain("sys4x", reset_less=True)
        self.clock_domains.cd_sys4x_dqs = ClockDomain("sys4x_dqs", reset_less=True)
        self.clock_domains.cd_idelay = ClockDomain("idelay")

        # # #

        clk48 = platform.request("clk48")
        platform.add_platform_command("create_clock -name clk48 -period 20.8333 [get_nets clk48]")

        self.submodules.pll = pll = S7MMCM(speedgrade=platform.speedgrade)
        pll.register_clkin(clk48, 48e6)
        pll.create_clkout(self.cd_sys,       sys_clk_freq)
        pll.create_clkout(self.cd_sys4x,     4*sys_clk_freq)
        pll.create_clkout(self.cd_sys4x_dqs, 4*sys_clk_freq, phase=90)
        pll.create_clkout(self.cd_idelay,    200e6)

        self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_idelay)

# SE30 SoC -----------------------------------------------------------------------------------------

class SE30SoC(SoCCore):
    def __init__(self, sys_clk_freq=int(100e6), **kwargs):
        platform = SE30Platform()

        # SoCCore init
        SoCCore.__init__(self, platform, clk_freq=sys_clk_freq,
                         cpu_type=None,
                         integrated_rom_size=0,
                         integrated_sram_size=0x2000, # 8KB internal SRAM
                         integrated_main_ram_size=0,
                         **kwargs)

        # CRG
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # Leds
        # platform.request("user_led", 0) might fail if not defined in ztex213_se30 or common
        # ZTex common usually defines user_led.
        # Check ztex_21x_common.py? It doesn't seem to have "user_led".
        # It has "ddram" and "clk48".
        # ztex213_nubus.py has extensions for leds?
        # Let's check if we can add LEDs.
        # For now, I'll skip LedChaser if pins aren't there, or I can define them.
        # The ztex board usually has LEDs.
        # But if not defined in platform, we skip.

        # Wishbone Masters/Slaves for SE30 Bus

        # 1. PDS Bus Master (DMA) -> Wishbone Slave
        # The Mac can perform DMA reads/writes to the FPGA resources (like the SRAM).
        # We need to expose a Wishbone Slave port from the SE30PDS module and connect it to the SoC bus.
        # Wait, SE30PDS defines `wb_dma` as a Master Interface (from PDS perspective, it masters the WB bus).
        # Yes: `wb_dma` in SE30PDS is used when the Mac requests the bus (DMA).
        # So `wb_dma` is a Wishbone Master.

        self.wb_dma = wishbone.Interface()
        self.bus.add_master(name="se30_dma", master=self.wb_dma)

        # 2. PDS Bus Slave (Mac accesses FPGA as a Slave) -> Wishbone Master
        # The Mac CPU accesses the FPGA. The FPGA acts as a Slave on the PDS bus.
        # The SE30PDS module converts these accesses to Wishbone cycles.
        # `wb_read` and `wb_write` are Wishbone Masters (from SE30PDS perspective).
        # We can connect them to the SoC bus so the Mac can read/write SoC resources (like SRAM, CSRs).

        self.wb_read = wishbone.Interface()
        self.wb_write = wishbone.Interface()

        # We need to arbiter these two into one master port on the SoC bus, or add two masters.
        # Adding two masters is fine.
        self.bus.add_master(name="se30_read", master=self.wb_read)
        self.bus.add_master(name="se30_write", master=self.wb_write)

        # Instantiate SE30 Bus Bridge
        self.submodules.se30_bridge = SE30PDS(self, platform, self.wb_read, self.wb_write, self.wb_dma)

        # Dummy CSR to ensure CSR bus is not empty (fix for reduce() error)
        class DummyCSR(Module, AutoCSR):
            def __init__(self):
                self.scratch = CSRStorage(32, name="scratch", reset=0xCAFEFEED)

        self.submodules.dummy_csr = DummyCSR()

# Build Script -------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="SE/30 PDS FPGA SoC")
    parser.add_argument("--build", action="store_true", help="Build bitstream")
    parser.add_argument("--sys-clk-freq", default=100e6, help="System clock frequency (default: 100MHz)")

    builder_args(parser)
    vivado_build_args(parser)
    args = parser.parse_args()

    soc = SE30SoC(sys_clk_freq=int(float(args.sys_clk_freq)), **soc_core_argdict(args))

    builder = Builder(soc, **builder_argdict(args))

    # Do not run build by default unless requested
    builder.build(**vivado_build_argdict(args), run=args.build)

if __name__ == "__main__":
    main()
