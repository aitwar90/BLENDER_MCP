#!/bin/bash

# --- KONFIGURACJA ŚCIEŻEK ---
BASE_DIR="/media/aitwarcl/b6fec136-6fdf-43ec-aa0e-0c5f6a0afa37/BlenderRepo/blender_proj/BLENDER_MCP/blender-main"

echo "========================================================="
echo "[MCP] ROZPOCZYNAM CZYSTE PRZYGOTOWANIE REPOZYTORIUM BLENDERA"
echo "========================================================="

# 1. Tworzenie katalogu bazowego, jeśli nie istnieje
mkdir -p "$BASE_DIR"
cd "$BASE_DIR" || exit 1

# 2. Oficjalne klonowanie głównego kodu Blendera z pominięciem LFS na starcie
if [ ! -d "blender" ]; then
    echo "[MCP] Klonowanie kodu źródłowego z oficjalnego GitHuba (Z pominięciem LFS)..."
    # Zastosowanie oficjalnej flagi zalecanej przez Blender Foundation przy problemach z LFS
    GIT_LFS_SKIP_SMUDGE=1 git clone git@github.com:blender/blender.git
else
    echo "[MCP] Katalog 'blender' już istnieje. Pomijam klonowanie."
fi

cd blender || exit 1

# 3. Pobranie oficjalnych prekompilowanych bibliotek oraz zasobów LFS
echo "[MCP] Uruchamianie 'make update' (pobieranie bibliotek i assetów)..."
make update

echo "========================================================="
echo "[SUKCES] Czyste repozytorium oraz biblioteki pobrane pomyślnie!"
echo "Możesz teraz bezpiecznie uruchomić skrypt patch_and_compile.py"
echo "========================================================="
