# Ghidra headless dist - chunked for sandbox delivery

Reassemble with:

    cat ghidra_headless.tgz.part* > ghidra_headless.tgz
    sha256sum -c <(echo 75fda3970400b5f394af87d600ca0ae9d02d12f4d19e8dbc8e3d95989f2aa72b ghidra_headless.tgz)
    tar xzf ghidra_headless.tgz

Disposable branch. Delete once consumed:

    git push origin --delete ghidra-dist
