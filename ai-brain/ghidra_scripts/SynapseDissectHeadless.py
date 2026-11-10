# SynapseDissectHeadless.py
# @category SynapseBrain
# @description Headless Ghidra 12.3 binary dissector exporting functions, decompiled C, memory blocks, and strings to JSON for the Portable Living AI Brain.

import json
import math
from collections import Counter

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor


def shannon_entropy(byte_values):
    n = len(byte_values)
    if n == 0:
        return 0.0
    counts = Counter(byte_values)
    ent = 0.0
    for c in counts.values():
        p = float(c) / float(n)
        ent -= p * math.log(p, 2)
    return round(ent, 3)


def run():
    args = getScriptArgs()
    out_path = args[0] if len(args) > 0 else "ghidra_dissect_out.json"
    monitor = ConsoleTaskMonitor()
    prog = currentProgram

    # 1. Memory blocks & Shannon entropy
    sections = []
    mem = prog.getMemory()
    for blk in mem.getBlocks():
        size = int(blk.getSize())
        sample_len = min(size, 4096)
        ent = 0.0
        if blk.isInitialized() and sample_len > 0:
            buf = bytearray(sample_len)
            try:
                blk.getBytes(blk.getStart(), buf)
                ent = shannon_entropy([b & 0xFF for b in buf])
            except Exception:
                ent = 0.0
        sections.append(
            {
                "name": blk.getName(),
                "addr": str(blk.getStart()),
                "size": size,
                "entropy": ent,
                "rwx": "{}{}{}".format(
                    "R" if blk.isRead() else "-",
                    "W" if blk.isWrite() else "-",
                    "X" if blk.isExecute() else "-",
                ),
            }
        )

    # 2. Decompile top non-external functions
    decomp = DecompInterface()
    decomp.openProgram(prog)
    fm = prog.getFunctionManager()
    funcs = []
    for idx, fn in enumerate(fm.getFunctions(True)):
        if fn.isExternal() or idx >= 20:
            continue
        c_code = ""
        res = decomp.decompileFunction(fn, 15, monitor)
        if res and res.decompileCompleted():
            c_code = res.getDecompiledFunction().getC()
        funcs.append(
            {
                "name": fn.getName(),
                "entry": str(fn.getEntryPoint()),
                "size": int(fn.getBody().getNumAddresses()),
                "signature": str(fn.getSignature()),
                "decompiled_c": c_code[:2400],
            }
        )
    decomp.dispose()

    # 3. Defined strings
    strings_out = []
    listing = prog.getListing()
    data_iter = listing.getDefinedData(True)
    while data_iter.hasNext() and len(strings_out) < 40:
        d = data_iter.next()
        if d.hasStringValue():
            val = str(d.getValue())
            if len(val) >= 4:
                strings_out.append({"addr": str(d.getAddress()), "value": val[:160]})

    report = {
        "engine": "Ghidra 12.3 Headless Decompiler",
        "program_name": prog.getName(),
        "language": str(prog.getLanguageID()),
        "compiler": str(prog.getCompilerSpec().getCompilerSpecID()),
        "image_base": str(prog.getImageBase()),
        "sections": sections,
        "functions": funcs,
        "strings": strings_out,
    }
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    run()
