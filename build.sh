#!/bin/bash

echo "Compilando para Linux..."
cd backend-zig
zig build -Dtarget=native -Doptimize=ReleaseFast
mkdir -p ../dist
cp zig-out/lib/liblogparser.so ../dist/
echo "✓ Compilação Linux concluída"

echo ""
echo "Cross-compilando para Windows..."
zig build -Dtarget=x86_64-windows -Doptimize=ReleaseFast
# DLL pode estar em bin/ ou lib/ dependendo da versão do Zig
if [ -f zig-out/bin/logparser.dll ]; then
    cp zig-out/bin/logparser.dll ../dist/
elif [ -f zig-out/lib/logparser.dll ]; then
    cp zig-out/lib/logparser.dll ../dist/
else
    echo "⚠ Aviso: DLL não encontrado em zig-out/bin/ nem zig-out/lib/"
fi
echo "✓ Cross-compilação Windows concluída"

echo ""
echo "Binários disponíveis em:"
ls -lh ../dist/

