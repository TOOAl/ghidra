/* ###
 * IP: GHIDRA
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
// Export the facts the portable brain is taught from: per-function instruction
// counts, mnemonics, resolved call targets, references, and (when the
// decompiler is present) the first lines of decompiled C.
// Usage:  -postScript ExportBrainFacts.java /tmp/brain_facts.json
//@category AI Brain

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.FlowType;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;

import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class ExportBrainFacts extends GhidraScript {

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        String outPath = (args != null && args.length > 0) ? args[0] : "/tmp/brain_facts.json";

        DecompInterface decomp = null;
        try {
            decomp = new DecompInterface();
            if (!decomp.openProgram(currentProgram)) {
                decomp = null; // no decompiler for this platform: facts still flow
            }
        } catch (Throwable t) {
            decomp = null;
        }

        ReferenceManager refs = currentProgram.getReferenceManager();
        StringBuilder sb = new StringBuilder();
        sb.append("{\"binary\":\"").append(esc(currentProgram.getDomainFile().getName()))
          .append("\",\"functions\":[");

        int count = 0;
        Iterator<Function> it = currentProgram.getFunctionManager().getFunctions(true);
        while (it.hasNext() && count < 400) {
            Function f = it.next();
            if (f.isThunk() || f.isExternal()) {
                continue;
            }
            List<String> insns = new ArrayList<>();
            Set<String> mnem = new LinkedHashSet<>();
            Set<String> calls = new LinkedHashSet<>();
            Set<String> refNames = new LinkedHashSet<>();
            Instruction instr = currentProgram.getListing().getInstructionAt(f.getEntryPoint());
            int guard = 0;
            while (instr != null && f.getBody().contains(instr.getMinAddress()) && guard < 16) {
                insns.add(instr.getMinAddress().toString() + ":\t"
                          + instr.getMnemonicString() + " " + instr.getDefaultOperandRepresentation(0));
                mnem.add(instr.getMnemonicString());
                Reference[] rs = refs.getReferencesFrom(instr.getMinAddress());
                for (Reference r : rs) {
                    Address to = r.getToAddress();
                    Function tgt = currentProgram.getFunctionManager().getFunctionContaining(to);
                    String nm = (tgt != null) ? tgt.getName() : null;
                    if (nm == null) {
                        nm = currentProgram.getSymbolTable().getPrimarySymbol(to) != null
                             ? currentProgram.getSymbolTable().getPrimarySymbol(to).getName() : null;
                    }
                    if (nm != null) {
                        refNames.add(nm);
                        FlowType ft = r.getFlowType();
                        if (ft != null && ft.isCall() && nm != null && !nm.equals(f.getName())) {
                            calls.add(nm);
                        }
                    }
                }
                instr = instr.getNext();
                guard++;
            }
            if (insns.size() < 3) {
                continue;
            }

            String dec = "";
            if (decomp != null) {
                try {
                    DecompileResults dr = decomp.decompileFunction(f, 20, monitor);
                    if (dr != null && dr.decompileCompleted() && dr.getDecompiledFunction() != null) {
                        String c = dr.getDecompiledFunction().getC();
                        if (c != null) {
                            String[] lines = c.split("\n");
                            StringBuilder keep = new StringBuilder();
                            for (int i = 0; i < Math.min(24, lines.length); i++) {
                                keep.append(lines[i]).append("\n");
                            }
                            dec = keep.toString();
                        }
                    }
                } catch (Throwable t) {
                    dec = "";
                }
            }

            if (count > 0) {
                sb.append(",");
            }
            sb.append("{\"name\":\"").append(esc(f.getName())).append("\",")
              .append("\"addr\":\"").append(f.getEntryPoint().toString()).append("\",")
              .append("\"insns\":[").append(join(insns)).append("],")
              .append("\"mnemonics\":[").append(join(new ArrayList<>(mnem))).append("],")
              .append("\"calls\":[").append(join(new ArrayList<>(calls))).append("],")
              .append("\"refs\":[").append(join(new ArrayList<>(refNames))).append("],")
              .append("\"decompile\":\"").append(esc(dec)).append("\"}");
            count++;
        }
        sb.append("]}");

        try (FileWriter w = new FileWriter(outPath)) {
            w.write(sb.toString());
        }
        println("ExportBrainFacts: " + count + " functions -> " + outPath);
        if (decomp != null) {
            decomp.dispose();
        }
    }

    private static String esc(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }

    private static String join(List<String> xs) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < xs.size(); i++) {
            if (i > 0) {
                b.append(",");
            }
            b.append("\"").append(esc(xs.get(i))).append("\"");
        }
        return b.toString();
    }
}
