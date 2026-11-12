#!/bin/sh
# Builds rando_give.dll on Linux without the Windows SDK or a CRT (clang + lld-link from LLVM).
set -e
cd "$(dirname "$0")"
mkdir -p out
llvm-dlltool -m i386:x86-64 -d kernel32.def -l out/kernel32.lib
llvm-dlltool -m i386:x86-64 -d ntdll.def -l out/ntdll.lib
clang --target=x86_64-pc-windows-msvc -O2 -ffreestanding -fno-stack-protector -fms-extensions \
      -fno-builtin -funwind-tables -fasynchronous-unwind-tables -Wall -Wextra -Werror -c rando_give.c -o out/rando_give.obj
lld-link /dll /nodefaultlib /entry:DllMain /machine:x64 /subsystem:windows /opt:ref \
      /out:out/rando_give.dll out/rando_give.obj out/kernel32.lib out/ntdll.lib
echo built out/rando_give.dll
