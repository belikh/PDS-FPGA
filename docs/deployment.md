# Deployment

## Build Process

The project uses the Migen/LiteX build flow which generates Verilog and a Tcl script for Xilinx Vivado.

### 1. Synthesis

Run the build command:
```bash
python3 nubus-to-ztex-gateware/se30_soc.py --build
```

This performs the following steps:
1. **Elaboration**: Migen generates the Verilog (`.v`) files.
2. **Synthesis**: Vivado synthesizes the design for the Artix-7 FPGA.
3. **Place & Route**: Vivado maps the design to the physical resources.
4. **Bitstream Generation**: Produces the `.bit` file.

### 2. Output Artifacts

The build artifacts are stored in `build/se30_soc/`:
- `gateware/se30_soc.bit`: The FPGA bitstream.
- `gateware/se30_soc.v`: The generated Verilog.
- `software/include/generated/`: C headers for CSR definitions.

### 3. Programming the FPGA

You can use the ZTex tools (fwloader) to load the bitstream.

```bash
# Example (adjust path to fwloader)
fwloader -v -uu build/se30_soc/gateware/se30_soc.bit
```

## Deployment Targets

- **Target Hardware**: ZTex USB-FPGA Module 2.13 mounted on a custom SE/30 PDS adapter board.
- **Host Machine**: Macintosh SE/30 running System 7 or MacOS 8 (for testing driver interactions).

## Publishing Documentation

This documentation site is designed to be hosted on GitHub Pages.

### How to Enable

1. Go to the repository **Settings**.
2. Navigate to the **Pages** section (sidebar).
3. Under **Build and deployment** > **Source**, select **Deploy from a branch**.
4. Under **Branch**, select your main branch (e.g., `main` or `master`) and select the `/docs` folder.
5. Click **Save**.

Once enabled, the site will be available at:
`https://<username>.github.io/<repository-name>/`
