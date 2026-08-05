# -*- coding: utf-8 -*-
"""
Test pour vérifier que l'UI n'excède pas les tailles standards d'écrans
"""
import sys
import io

# Configurer UTF-8 pour Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_ui_sizes():
    """Vérifie que les tailles UI respectent les standards"""
    
    # Résolutions d'écran standards minimums (en pixels)
    MIN_WIDTH_1024 = 1024
    MIN_HEIGHT_768 = 768
    MIN_WIDTH_1280 = 1280
    MIN_HEIGHT_720 = 720
    
    # Tailles UI configurées
    ui_sizes = {
        "Dock Widget": (400, 600),  # Largeur responsive avec min 350, max 500
        "Validation Dialog": (800, 500),
        "Error Viewer": (900, 600),
        "Project Action Dialog": (900, 450),
        "Refresh Layers Dialog": (800, 420),
        "Layer Mapping Dialog": (850, 380),
        "Field Mapping Dialog": (450, 300),
        "Auth Dialog": (450, 350),
    }
    
    issues = []
    
    # Vérifier les dimensions par rapport à la résolution minimum 1024x768
    for name, (width, height) in ui_sizes.items():
        # Laisser 10% d'espace pour la barre des tâches et les marges
        max_usable_width = int(MIN_WIDTH_1024 * 0.90)
        max_usable_height = int(MIN_HEIGHT_768 * 0.85)
        
        if width > max_usable_width:
            issues.append(f"[ERREUR] {name}: Largeur {width}px dépasse {max_usable_width}px (1024x768)")
        
        if height > max_usable_height:
            issues.append(f"[ERREUR] {name}: Hauteur {height}px dépasse {max_usable_height}px (1024x768)")
        else:
            issues.append(f"[OK] {name}: {width}x{height}px adapté pour 1024x768")
    
    print("\n=== Vérification de la réactivité UI ===\n")
    for msg in issues:
        print(msg)
    
    # Résumé
    print("\n=== Résumé ===")
    errors = [m for m in issues if m.startswith("[ERREUR]")]
    if errors:
        print(f"Attention: {len(errors)} problème(s) détecté(s)")
        return False
    else:
        print("Succès: Toutes les interfaces s'ajustent correctement aux écrans standards")
        return True

if __name__ == "__main__":
    success = test_ui_sizes()
    exit(0 if success else 1)
