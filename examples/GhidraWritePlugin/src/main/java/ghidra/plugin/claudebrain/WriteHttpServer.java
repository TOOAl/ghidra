/* ###
 * IP: GHIDRA
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 */
package ghidra.plugin.claudebrain;

import java.io.*;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.stream.Collectors;

import javax.swing.SwingUtilities;

import com.sun.net.httpserver.*;

import ghidra.util.Msg;

/**
 * Tiny HTTP server for GhidraWritePlugin.
 * Uses JDK built-in com.sun.net.httpserver (no extra deps).
 * Bound to 127.0.0.1 only — local brain only.
 */
public class WriteHttpServer {

    private final int port;
    private final GhidraWritePlugin plugin;
    private HttpServer server;

    public WriteHttpServer(int port, GhidraWritePlugin plugin) {
        this.port = port;
        this.plugin = plugin;
    }

    public void start() throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/health", this::handleHealth);
        server.createContext("/rename_function", this::handleRename);
        server.createContext("/set_comment", this::handleComment);
        server.createContext("/set_plate_comment", this::handlePlate);
        server.createContext("/create_label", this::handleLabel);
        server.createContext("/list_functions", this::handleListFunctions);
        server.setExecutor(java.util.concurrent.Executors.newCachedThreadPool());
        server.start();
    }

    public void stop() {
        if (server != null) server.stop(0);
    }

    private void handleHealth(HttpExchange ex) throws IOException {
        String body = "{\"status\":\"ok\",\"plugin\":\"GhidraWritePlugin\",\"port\":" + port + "}";
        sendJson(ex, 200, body);
    }

    private void handleRename(HttpExchange ex) throws IOException {
        if (!checkMethod(ex, "POST")) return;
        String req = readBody(ex);
        String oldName = extractJsonField(req, "old_name");
        String newName = extractJsonField(req, "new_name");
        if (oldName == null || newName == null) {
            // also try camelCase fallback
            if (oldName == null) oldName = extractJsonField(req, "oldName");
            if (newName == null) newName = extractJsonField(req, "newName");
        }
        if (oldName == null || newName == null) {
            sendJson(ex, 400, "{\"error\":\"need old_name and new_name\"}");
            return;
        }
        final String o = oldName, n = newName;
        String result = invokeOnSwing(() -> plugin.renameFunction(o, n));
        boolean ok = result.startsWith("OK");
        sendJson(ex, ok ? 200 : 404, jsonMsg(result, ok));
    }

    private void handleComment(HttpExchange ex) throws IOException {
        if (!checkMethod(ex, "POST")) return;
        String req = readBody(ex);
        String name = extractJsonField(req, "name");
        String comment = extractJsonField(req, "comment");
        if (name == null || comment == null) {
            sendJson(ex, 400, "{\"error\":\"need name and comment\"}");
            return;
        }
        String result = invokeOnSwing(() -> plugin.setComment(name, comment));
        boolean ok = result.startsWith("OK");
        sendJson(ex, ok ? 200 : 404, jsonMsg(result, ok));
    }

    private void handlePlate(HttpExchange ex) throws IOException {
        if (!checkMethod(ex, "POST")) return;
        String req = readBody(ex);
        String name = extractJsonField(req, "name");
        String comment = extractJsonField(req, "comment");
        if (name == null || comment == null) {
            sendJson(ex, 400, "{\"error\":\"need name and comment\"}");
            return;
        }
        String result = invokeOnSwing(() -> plugin.setPlateComment(name, comment));
        boolean ok = result.startsWith("OK");
        sendJson(ex, ok ? 200 : 404, jsonMsg(result, ok));
    }

    private void handleLabel(HttpExchange ex) throws IOException {
        if (!checkMethod(ex, "POST")) return;
        String req = readBody(ex);
        String addr = extractJsonField(req, "address");
        String label = extractJsonField(req, "label");
        if (addr == null || label == null) {
            sendJson(ex, 400, "{\"error\":\"need address and label\"}");
            return;
        }
        String result = invokeOnSwing(() -> plugin.createLabel(addr, label));
        boolean ok = result.startsWith("OK");
        sendJson(ex, ok ? 200 : 404, jsonMsg(result, ok));
    }

    private void handleListFunctions(HttpExchange ex) throws IOException {
        if (!checkMethod(ex, "GET")) return;
        String query = ex.getRequestURI().getQuery();
        // Simple impl: if program open, list functions (read-only check)
        String result = invokeOnSwing(() -> {
            if (plugin.getCurrentProgramSafe() == null) return "No program open";
            StringBuilder sb = new StringBuilder("[");
            int count = 0;
            int limit = 50;
            if (query != null && query.contains("limit=")) {
                try {
                    String v = query.replaceAll(".*limit=([^&]+).*", "$1");
                    limit = Integer.parseInt(v);
                } catch (Exception ignored) {}
            }
            for (ghidra.program.model.listing.Function f : plugin.getCurrentProgramSafe().getFunctionManager().getFunctions(true)) {
                if (count >= limit) break;
                if (count > 0) sb.append(",");
                sb.append("{\"name\":\"").append(f.getName()).append("\",\"addr\":\"").append(f.getEntryPoint()).append("\"}");
                count++;
            }
            sb.append("]");
            return sb.toString();
        });
        if (result.startsWith("No program")) {
            sendJson(ex, 404, jsonMsg(result, false));
        } else {
            sendJson(ex, 200, "{\"functions\":" + result + "}");
        }
    }

    // --- helpers ---

    private String invokeOnSwing(java.util.concurrent.Callable<String> c) {
        final String[] out = new String[1];
        try {
            if (SwingUtilities.isEventDispatchThread()) {
                out[0] = c.call();
            } else {
                SwingUtilities.invokeAndWait(() -> {
                    try { out[0] = c.call(); } catch (Exception e) { out[0] = "Error: " + e.getMessage(); }
                });
            }
        } catch (Exception e) {
            out[0] = "Error: " + e.getMessage();
            Msg.error(this, "invokeOnSwing failed", e);
        }
        return out[0];
    }

    private boolean checkMethod(HttpExchange ex, String expected) throws IOException {
        if (!expected.equals(ex.getRequestMethod())) {
            ex.getResponseHeaders().set("Allow", expected);
            sendJson(ex, 405, "{\"error\":\"Method not allowed, use " + expected + "\"}");
            return false;
        }
        return true;
    }

    private String readBody(HttpExchange ex) throws IOException {
        try (BufferedReader br = new BufferedReader(new InputStreamReader(ex.getRequestBody(), StandardCharsets.UTF_8))) {
            return br.lines().collect(Collectors.joining("\n"));
        }
    }

    private void sendJson(HttpExchange ex, int code, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        ex.sendResponseHeaders(code, bytes.length);
        try (OutputStream os = ex.getResponseBody()) { os.write(bytes); }
    }

    private String jsonMsg(String msg, boolean ok) {
        // minimal escaping
        String esc = msg.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n");
        return "{\"ok\":" + ok + ",\"message\":\"" + esc + "\"}";
    }

    private String extractJsonField(String json, String key) {
        if (json == null) return null;
        // very simple parser: "key": "value"
        String pat = "\"" + key + "\"";
        int idx = json.indexOf(pat);
        if (idx < 0) return null;
        int colon = json.indexOf(":", idx + pat.length());
        if (colon < 0) return null;
        int q1 = json.indexOf("\"", colon + 1);
        if (q1 < 0) return null;
        int q2 = json.indexOf("\"", q1 + 1);
        if (q2 < 0) return null;
        // handle escaped quotes naively
        return json.substring(q1 + 1, q2);
    }
}
