#!/bin/bash

echo "Testando parser CSV..."

# Compilar backend
cd backend-zig
zig build -Dtarget=native -Doptimize=ReleaseFast
cd ..

# Criar diretório de teste
mkdir -p test_output

# Testar com CSV de exemplo usando Python
echo "Processando CSV de exemplo..."
python3 << 'PYTHON_SCRIPT'
import sys
import os
sys.path.insert(0, 'frontend-python')

try:
    from zig_bridge import ZigBackend
    
    backend = ZigBackend()
    
    # Testar processamento de CSV individual
    csv_path = "tests/sample_logs/csv/exemplo.csv"
    json_output = "test_output/exemplo_csv.json"
    
    if os.path.exists(csv_path):
        print(f"Processando: {csv_path}")
        # Recompilar se necessário
        import subprocess
        subprocess.run(["cd", "backend-zig", "&&", "zig", "build"], shell=True, check=False)
        
        sucesso = backend.processar_csv(csv_path, json_output)
        
        if sucesso:
            print(f"✓ CSV processado com sucesso!")
            print(f"  Resultado salvo em: {json_output}")
            
            # Mostrar conteúdo do JSON gerado
            if os.path.exists(json_output):
                with open(json_output, 'r') as f:
                    print("\nConteúdo do JSON:")
                    print(f.read())
        else:
            print("✗ Erro ao processar CSV")
    else:
        print(f"✗ Arquivo não encontrado: {csv_path}")
        
except Exception as e:
    print(f"✗ Erro: {e}")
    import traceback
    traceback.print_exc()
PYTHON_SCRIPT

echo ""
echo "✓ Teste concluído"
echo "Verifique o arquivo test_output/exemplo_csv.json"

