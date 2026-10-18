# RenameWithLLM.py — GhidraWritePlugin 없이도 쓰기 테스트용 스크립트
# @category ClaudeBrain
# @menupath Tools.ClaudeBrain.Rename Function
# Ghidra CodeBrowser > Script Manager 에서 실행
# 팝업에서 old_name, new_name 입력하면 rename_function과 동일 효과

from ghidra.program.model.listing import CodeUnit

askString = askString
askChoice = askChoice

old_name = askString("ClaudeBrain — Rename", "Old function name (e.g. FUN_00401000):")
if not old_name:
    popup("Cancelled")
    exit()

new_name = askString("ClaudeBrain — Rename", "New function name (e.g. decrypt_config):")
if not new_name:
    popup("Cancelled")
    exit()

fm = currentProgram.getFunctionManager()
target = None
for f in fm.getFunctions(True):
    if f.getName() == old_name:
        target = f
        break

if target is None:
    # try address
    try:
        addr = currentProgram.getAddressFactory().getAddress(old_name)
        target = fm.getFunctionAt(addr)
    except:
        pass

if target is None:
    popup("Function not found: " + old_name)
    exit()

tx = currentProgram.startTransaction("ClaudeBrain rename %s -> %s" % (old_name, new_name))
commit = False
try:
    target.setName(new_name, getMonitor().getClass().getName() and target.getSymbol().getSource() or target.getSymbol().getSource())
    # simpler:
    # target.setName(new_name, ghidra.program.model.symbol.SourceType.USER_DEFINED)
    from ghidra.program.model.symbol import SourceType
    target.setName(new_name, SourceType.USER_DEFINED)
    commit = True
    popup("OK: %s -> %s at %s" % (old_name, new_name, target.getEntryPoint()))
    print("Renamed %s -> %s at %s" % (old_name, new_name, target.getEntryPoint()))
finally:
    currentProgram.endTransaction(tx, commit)

# Optional: also set a comment to prove write
comment = askString("ClaudeBrain — Comment (optional)", "Enter comment for %s (leave empty to skip):" % new_name)
if comment:
    tx2 = currentProgram.startTransaction("ClaudeBrain comment " + new_name)
    try:
        currentProgram.getListing().setComment(target.getEntryPoint(), CodeUnit.PRE_COMMENT, comment)
        print("Comment set: " + comment)
    finally:
        currentProgram.endTransaction(tx2, True)
