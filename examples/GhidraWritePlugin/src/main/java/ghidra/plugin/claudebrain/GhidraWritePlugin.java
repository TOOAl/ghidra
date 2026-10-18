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
package ghidra.plugin.claudebrain;

import ghidra.app.plugin.PluginCategoryNames;
import ghidra.app.plugin.ProgramPlugin;
import ghidra.framework.plugintool.PluginInfo;
import ghidra.framework.plugintool.PluginTool;
import ghidra.framework.plugintool.util.PluginStatus;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Program;
import ghidra.util.Msg;

/**
 * GhidraWritePlugin — GhidraClaudeCode-Brain의 쓰기 손
 *
 * 외부 LLM(무료 OpenRouter 등) + 로컬 Brain이 HTTP로 호출하는 쓰기 API를 제공:
 *   POST /rename_function  {"old_name": "FUN_00401000", "new_name": "decrypt_config"}
 *   POST /set_comment       {"name": "FUN_00401000", "comment": "C2 통신 함수"}
 *
 * REA가 읽기만 되는 것을 보완하여, "읽기+쓰기+여러 포맷" 완성을 담당.
 * 서버는 127.0.0.1에만 바인딩 (로컬 전용, 외부 노출 없음).
 */
@PluginInfo(
    status = PluginStatus.RELEASED,
    packageName = "ClaudeBrain",
    category = PluginCategoryNames.MISC,
    shortDescription = "ClaudeBrain Writer — rename/comment via local HTTP",
    description = "Exposes rename_function, set_comment etc. over http://127.0.0.1:8089 for GhidraClaudeCode-Brain (external free LLM + local brain). REA provides reading, this plugin provides writing."
)
public class GhidraWritePlugin extends ProgramPlugin {

    private WriteHttpServer httpServer;
    private int port = 8089; // default, configurable via Tool Options

    public GhidraWritePlugin(PluginTool tool) {
        super(tool);
    }

    @Override
    protected void init() {
        super.init();
        // Tool Options에서 포트 읽기 (없으면 기본값)
        try {
            String portStr = System.getProperty("ghidra.claudebrain.port");
            if (portStr != null) {
                port = Integer.parseInt(portStr);
            }
        } catch (Exception e) {
            // ignore
        }
        startServer();
        Msg.info(this, "GhidraWritePlugin initialized on 127.0.0.1:" + port);
        Msg.info(this, "Endpoints: GET /health, POST /rename_function, POST /set_comment, POST /set_plate_comment, POST /create_label, GET /list_functions");
    }

    private void startServer() {
        try {
            httpServer = new WriteHttpServer(port, this);
            httpServer.start();
            Msg.info(this, "WriteHttpServer started on 127.0.0.1:" + port);
        } catch (Exception e) {
            Msg.error(this, "Failed to start WriteHttpServer on port " + port, e);
        }
    }

    @Override
    protected void dispose() {
        if (httpServer != null) {
            httpServer.stop();
            Msg.info(this, "WriteHttpServer stopped");
        }
        super.dispose();
    }

    // Called by HTTP handlers via SwingUtilities.invokeAndWait to ensure EDT safety
    // All program modifications must run in a transaction

    public Program getCurrentProgramSafe() {
        return currentProgram;
    }

    /**
     * Rename function by old name. Supports exact name match.
     * Runs in a transaction.
     */
    public String renameFunction(String oldName, String newName) {
        Program program = currentProgram;
        if (program == null) {
            return "No program open";
        }
        Function target = findFunctionByName(program, oldName);
        if (target == null) {
            // Try by address if oldName looks like 0x...
            target = findFunctionByAddress(program, oldName);
            if (target == null) {
                return "Function not found: " + oldName;
            }
        }
        int txId = program.startTransaction("ClaudeBrain rename " + oldName + " -> " + newName);
        boolean commit = false;
        try {
            target.setName(newName, ghidra.program.model.symbol.SourceType.USER_DEFINED);
            commit = true;
            Msg.info(this, "Renamed " + oldName + " -> " + newName + " at " + target.getEntryPoint());
            return "OK: " + oldName + " -> " + newName + " at " + target.getEntryPoint();
        } catch (Exception e) {
            Msg.error(this, "Rename failed", e);
            return "Error: " + e.getMessage();
        } finally {
            program.endTransaction(txId, commit);
        }
    }

    public String setComment(String funcNameOrAddress, String comment) {
        Program program = currentProgram;
        if (program == null) return "No program open";
        Function f = findFunctionByName(program, funcNameOrAddress);
        if (f == null) f = findFunctionByAddress(program, funcNameOrAddress);
        if (f == null) return "Function not found: " + funcNameOrAddress;

        int txId = program.startTransaction("ClaudeBrain comment " + funcNameOrAddress);
        boolean commit = false;
        try {
            // PRE_COMMENT on function entry point
            program.getListing().setComment(f.getEntryPoint(),
                ghidra.program.model.listing.CodeUnit.PRE_COMMENT, comment);
            commit = true;
            Msg.info(this, "Set comment on " + funcNameOrAddress + ": " + comment);
            return "OK: comment set on " + funcNameOrAddress;
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        } finally {
            program.endTransaction(txId, commit);
        }
    }

    public String setPlateComment(String funcNameOrAddress, String comment) {
        Program program = currentProgram;
        if (program == null) return "No program open";
        Function f = findFunctionByName(program, funcNameOrAddress);
        if (f == null) f = findFunctionByAddress(program, funcNameOrAddress);
        if (f == null) return "Function not found: " + funcNameOrAddress;

        int txId = program.startTransaction("ClaudeBrain plate " + funcNameOrAddress);
        boolean commit = false;
        try {
            program.getListing().setComment(f.getEntryPoint(),
                ghidra.program.model.listing.CodeUnit.PLATE_COMMENT, comment);
            commit = true;
            return "OK: plate comment set on " + funcNameOrAddress;
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        } finally {
            program.endTransaction(txId, commit);
        }
    }

    public String createLabel(String addressStr, String label) {
        Program program = currentProgram;
        if (program == null) return "No program open";
        try {
            ghidra.program.model.address.Address addr =
                program.getAddressFactory().getAddress(addressStr);
            if (addr == null) return "Invalid address: " + addressStr;
            int txId = program.startTransaction("ClaudeBrain label " + label);
            boolean commit = false;
            try {
                program.getSymbolTable().createLabel(addr, label,
                    ghidra.program.model.symbol.SourceType.USER_DEFINED);
                commit = true;
                return "OK: label " + label + " at " + addressStr;
            } finally {
                program.endTransaction(txId, commit);
            }
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    public String patchBytes(String addressStr, String hexBytes, String comment) {
        Program program = currentProgram;
        if (program == null) return "No program open";
        try {
            ghidra.program.model.address.Address addr =
                program.getAddressFactory().getAddress(addressStr);
            if (addr == null) return "Invalid address: " + addressStr;
            // hex string -> bytes
            String clean = hexBytes.replaceAll("\\s+", "");
            if (clean.length() % 2 != 0) return "Invalid hex (odd length): " + hexBytes;
            byte[] bytes = new byte[clean.length() / 2];
            for (int i = 0; i < bytes.length; i++) {
                bytes[i] = (byte) Integer.parseInt(clean.substring(i * 2, i * 2 + 2), 16);
            }
            // read original bytes for backup/undo
            byte[] orig = new byte[bytes.length];
            int read = program.getMemory().getBytes(addr, orig, 0, bytes.length);
            String origHex = bytesToHex(orig, read);

            int txId = program.startTransaction("ClaudeBrain patch " + addressStr);
            boolean commit = false;
            try {
                program.getMemory().setBytes(addr, bytes, 0, bytes.length);
                if (comment != null && !comment.isEmpty()) {
                    program.getListing().setComment(addr,
                        ghidra.program.model.listing.CodeUnit.EOL_COMMENT, "PATCH: " + comment + " (orig: " + origHex + ")");
                }
                // also try to disassemble new bytes
                try {
                    ghidra.app.util.PseudoDisassembler pd = new ghidra.app.util.PseudoDisassembler(program);
                    pd.disassemble(addr, null);
                } catch (Exception ignored) {}
                commit = true;
                Msg.info(this, "Patched " + addressStr + " " + origHex + " -> " + hexBytes + " (" + comment + ")");
                return "OK: patched " + addressStr + " " + origHex + " -> " + hexBytes + " (undo: Edit > Undo)";
            } catch (Exception e) {
                Msg.error(this, "Patch failed", e);
                return "Error: " + e.getMessage();
            } finally {
                program.endTransaction(txId, commit);
            }
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    public String getBytes(String addressStr, int length) {
        Program program = currentProgram;
        if (program == null) return "No program open";
        try {
            ghidra.program.model.address.Address addr =
                program.getAddressFactory().getAddress(addressStr);
            if (addr == null) return "Invalid address: " + addressStr;
            byte[] buf = new byte[length];
            int read = program.getMemory().getBytes(addr, buf, 0, length);
            return bytesToHex(buf, read);
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    public String searchBytes(String pattern) {
        Program program = currentProgram;
        if (program == null) return "No program open";
        try {
            // Use Ghidra Memory.search with simple hex pattern (supports ?? wildcards via masking)
            // Simplified: split pattern, build byte[] + mask
            String[] parts = pattern.trim().split("\\s+");
            byte[] bytes = new byte[parts.length];
            byte[] mask = new byte[parts.length];
            for (int i = 0; i < parts.length; i++) {
                if (parts[i].equals("??") || parts[i].equals("?")) {
                    bytes[i] = 0; mask[i] = 0;
                } else {
                    bytes[i] = (byte) Integer.parseInt(parts[i], 16);
                    mask[i] = (byte) 0xFF;
                }
            }
            int count = 0;
            StringBuilder sb = new StringBuilder("[");
            ghidra.program.model.address.AddressSetView set = program.getMemory();
            // Iterate memory blocks
            for (ghidra.program.model.mem.MemoryBlock block : program.getMemory().getBlocks()) {
                if (!block.isInitialized()) continue;
                long size = block.getSize();
                // naive scan (good enough for demo, ≤10MB)
                if (size > 20_000_000) continue;
                byte[] blockBytes = new byte[(int) size];
                int got = program.getMemory().getBytes(block.getStart(), blockBytes, 0, (int) size);
                for (int off = 0; off <= got - bytes.length; off++) {
                    boolean match = true;
                    for (int j = 0; j < bytes.length; j++) {
                        if (mask[j] != 0 && blockBytes[off + j] != bytes[j]) { match = false; break; }
                    }
                    if (match) {
                        if (count > 0) sb.append(",");
                        sb.append("\"").append(block.getStart().add(off)).append("\"");
                        count++;
                        if (count >= 100) break;
                        off += bytes.length - 1;
                    }
                }
                if (count >= 100) break;
            }
            sb.append("]");
            return sb.toString();
        } catch (Exception e) {
            Msg.error(this, "searchBytes failed", e);
            return "Error: " + e.getMessage();
        }
    }

    public String listImports(String filter) {
        Program program = currentProgram;
        if (program == null) return "No program open";
        try {
            StringBuilder sb = new StringBuilder("[");
            int count = 0;
            ghidra.program.model.symbol.SymbolTable st = program.getSymbolTable();
            for (ghidra.program.model.symbol.Symbol s : st.getExternalSymbols()) {
                String name = s.getName(true);
                if (filter != null && !filter.isEmpty() && !name.toLowerCase().contains(filter.toLowerCase())) continue;
                if (count > 0) sb.append(",");
                sb.append("\"").append(name.replace("\"", "\\\"")).append("\"");
                count++;
                if (count >= 200) break;
            }
            sb.append("]");
            return sb.toString();
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    private String bytesToHex(byte[] b, int len) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < len && i < b.length; i++) {
            if (i > 0) sb.append(" ");
            sb.append(String.format("%02X", b[i] & 0xFF));
        }
        return sb.toString();
    }

    private Function findFunctionByName(Program program, String name) {
        if (name == null) return null;
        ghidra.program.model.listing.FunctionManager fm = program.getFunctionManager();
        // Exact match first
        for (Function f : fm.getFunctions(true)) {
            if (name.equals(f.getName())) return f;
        }
        // Case-insensitive fallback
        for (Function f : fm.getFunctions(true)) {
            if (name.equalsIgnoreCase(f.getName())) return f;
        }
        return null;
    }

    private Function findFunctionByAddress(Program program, String addrStr) {
        try {
            ghidra.program.model.address.Address addr =
                program.getAddressFactory().getAddress(addrStr);
            if (addr == null) return null;
            return program.getFunctionManager().getFunctionAt(addr);
        } catch (Exception e) {
            return null;
        }
    }

    public int getPort() {
        return port;
    }
}
