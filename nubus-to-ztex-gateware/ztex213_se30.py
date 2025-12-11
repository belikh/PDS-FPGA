#
# Copyright (c) 2015 Yann Sionneau <yann.sionneau@gmail.com>
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2020-2021 Romain Dolbeau <romain@dolbeau.org>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from litex.build.generic_platform import *
from litex.build.xilinx import XilinxPlatform

try:
    from VintageBusFPGA_Common.ztex_21x_common import ZTexPlatform
except ImportError:
    # Fallback if path not set up
    from ztex_21x_common import ZTexPlatform

# IOs ----------------------------------------------------------------------------------------------

# I/O for SE/30 PDS (Redesigned Board Pinout)
# This mapping assumes a custom adapter board for ZTex 2.13.
# It utilizes most available pins for PDS signals and Buffer Controls.

_se30_pds_io = [
    # SE/30 PDS Signals
    # CPUCLK (15.6672 MHz)
    ("clk_3v3_n",          0, Pins("H16"), IOStandard("lvttl")),

    # Address Bus (A0-A31) - Reusing 'ad' pins
    ("pds_a_3v3_n",        0, Pins("A13 A14 C12 B12 B13 B14 A15 A16 "
                                   "D12 D13 D14 C14 B16 B17 D15 C15 "
                                   "B18 A18 C16 C17 E15 E16 F14 F13 "
                                   "D17 D18 E17 E18 F15 F18 F16 G18 "), IOStandard("lvttl")),

    # Data Bus (D0-D31)
    # Reusing Control + P1 pins + Extras
    ("pds_d_3v3_n",        0, Pins(
        "U7 V6 V7 " +             # ID (3)
        "U2 V2 K6 " +             # TM0, TM1, TM2 (3)
        "T8 V4 V5 " +             # ARB (3)
        "J17 K15 J18 " +          # ACK, START, RQST (3)
        "K16 " +                  # NMRQ (1)
        "M1 L1 N2 N1 R2 P2 T1 R1 P4 P3 P5 N5 " + # P1 (12)
        "V9 U9 " +                # LED/Serial (2)
        "T5 " +                   # CLK2X (1)
        "T6 " +                   # EXTRA (1)
        "G17 " +                  # EXTRA (1)
        "H17 " +                  # EXTRA (1)
        "L3"                      # EXTRA (1) - Using spare HDMI pin
    ), IOStandard("lvttl")),

    # Control Signals
    # /AS
    ("as_3v3_n",           0, Pins("J13"), IOStandard("lvttl")),
    # /DS
    ("ds_3v3_n",           0, Pins("G13"), IOStandard("lvttl")), # Bidirectional
    # R/W
    ("rw_3v3_n",           0, Pins("G16"), IOStandard("lvttl")),
    # /DSACK0
    ("dsack0_3v3_n",       0, Pins("H15"), IOStandard("lvttl")),
    # /DSACK1
    ("dsack1_3v3_n",       0, Pins("H14"), IOStandard("lvttl")),
    # SIZ0
    ("siz0_3v3_n",         0, Pins("U6"),  IOStandard("lvttl")),
    # SIZ1
    ("siz1_3v3_n",         0, Pins("J14"), IOStandard("lvttl")),

    # FC0-2
    ("fc_3v3_n",           0, Pins("G14 R3 R5"), IOStandard("lvttl")),

    # Interrupts /IRQ1-3
    ("irq_3v3_n",          0, Pins("U8 K13 J15"), IOStandard("lvttl")),

    # Bus Arbitration
    ("br_3v3_n",           0, Pins("R6"), IOStandard("lvttl")),
    ("bg_3v3_n",           0, Pins("R7"), IOStandard("lvttl")),
    ("bgack_3v3_n",        0, Pins("R8"), IOStandard("lvttl")),

    # Extended PDS Signals (Using HDMI pins)
    # /STERM
    ("sterm_3v3_n",        0, Pins("M2"), IOStandard("lvttl")),
    # /CBREQ
    ("cbreq_3v3_n",        0, Pins("K5"), IOStandard("lvttl")),
    # /CBACK
    ("cback_3v3_n",        0, Pins("L4"), IOStandard("lvttl")),
    # /CIOUT
    ("ciout_3v3_n",        0, Pins("K3"), IOStandard("lvttl")),

    # External Buffer Controls (For New Board)
    # Data Direction (1 = Output/Write, 0 = Input/Read)
    ("pds_dir_data",       0, Pins("M4"), IOStandard("lvttl")),
    # Address Direction (1 = Output/Master, 0 = Input/Slave)
    ("pds_dir_addr",       0, Pins("N4"), IOStandard("lvttl")),
    # Output Enable (Active Low)
    ("pds_oe_n",           0, Pins("M3"), IOStandard("lvttl")),
]

_se30_peripherals = [
    ## USB
    ("usb", 0,
     Subsignal("dp", Pins("B11")),
     Subsignal("dm", Pins("A11")),
     IOStandard("LVCMOS33")
    ),
    ## HDMI (Disabled to use pins for PDS extension)
    # ("hdmi", 0,
    #     Subsignal("clk_p",   Pins("M4"), IOStandard("TMDS_33")),
    #     Subsignal("clk_n",   Pins("N4"), IOStandard("TMDS_33")),
    #     Subsignal("data0_p", Pins("M3"), IOStandard("TMDS_33")),
    #     Subsignal("data0_n", Pins("M2"), IOStandard("TMDS_33")),
    #     Subsignal("data1_p", Pins("K5"), IOStandard("TMDS_33")),
    #     Subsignal("data1_n", Pins("L4"), IOStandard("TMDS_33")),
    #     Subsignal("data2_p", Pins("K3"), IOStandard("TMDS_33")),
    #     Subsignal("data2_n", Pins("L3"), IOStandard("TMDS_33")),
    #     Subsignal("hpd",     Pins("N6"), IOStandard("LVCMOS33")),
    #     Subsignal("sda",     Pins("M6"), IOStandard("LVCMOS33")),
    #     Subsignal("scl",     Pins("L6"), IOStandard("LVCMOS33")),
    #     Subsignal("cec",     Pins("L5"), IOStandard("LVCMOS33")),
    # ),
    ## micro-sd
    ("sdcard", 0,
        Subsignal("data", Pins("U1 T3 T4 U4"), Misc("PULLUP True")),
        Subsignal("cmd",  Pins("U3"), Misc("PULLUP True")),
        Subsignal("clk",  Pins("V1")),
        Misc("SLEW=FAST"),
        IOStandard("LVCMOS33"),
    ),
]

class SE30Platform(ZTexPlatform):
    def __init__(self, variant="ztex2.13a"):
        # The base ZTexPlatform expects 'connectors'.
        # We pass empty as we define pins explicitly.
        ZTexPlatform.__init__(self, variant=variant, version="V1.2", connectors=[])
        self.add_extension(_se30_pds_io)
        self.add_extension(_se30_peripherals)
