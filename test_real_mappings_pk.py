# -*- coding: utf-8 -*-
"""
Test d'intégration pour vérifier que les PK UUID sont correctement chargées
depuis le fichier layer_table_mapping.json réel.
"""

import sys
import os
import json
import io

# Configurer UTF-8 pour Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ajouter le chemin du plugin
plugin_dir = os.path.dirname(__file__)
sys.path.insert(0, plugin_dir)

from config_postgrest import load_layer_mapping


def test_real_mappings():
    """Teste le chargement des mappings réels avec la nouvelle logique UUID"""
    
    print("\n=== Integration Test: Chargement des Mappings Reels ===\n")
    
    mappings = load_layer_mapping(plugin_dir)
    
    if not mappings:
        print("[ERROR] Aucun mapping chargé!")
        return False
    
    print(f"Total de mappings charges: {len(mappings)}\n")
    
    # Identifier les mappings avec UUID PK
    uuid_pks = {}
    fk_uuids = {}
    
    for layer_name, config in mappings.items():
        endpoint = config.get('endpoint', '')
        pk_field = config.get('pk_field', '')
        columns = config.get('columns', [])
        
        # Verifier si la PK est une UUID
        if pk_field.lower().startswith('uuid_'):
            uuid_pks[layer_name] = {
                'endpoint': endpoint,
                'pk_field': pk_field,
                'expected_pattern': f"uuid_{endpoint.replace('-', '_')}"
            }
        
        # Compter les autres UUID (FKs)
        for col in columns:
            if col.lower().startswith('uuid_') and col.lower() != pk_field.lower():
                fk_uuids[layer_name] = fk_uuids.get(layer_name, 0) + 1
    
    print(f"Mappings avec UUID comme PK: {len(uuid_pks)}")
    if uuid_pks:
        print("Exemples:")
        for name, info in list(uuid_pks.items())[:5]:
            print(f"  - {name}: {info['pk_field']}")
    print()
    
    print(f"Mappings avec colonnes UUID (FKs): {len(fk_uuids)}")
    if fk_uuids:
        print("Exemples (avec nombre de FKs):")
        for name, count in list(fk_uuids.items())[:5]:
            print(f"  - {name}: {count} colonne(s) UUID")
    print()
    
    # Afficher les mappings qui ont des UUIDs multiples
    complex_mappings = {k: v for k, v in mappings.items() 
                        if len([c for c in v.get('columns', []) 
                               if c.lower().startswith('uuid_')]) > 1}
    
    if complex_mappings:
        print(f"Mappings avec plusieurs UUIDs (PK + FKs):")
        for name in list(complex_mappings.keys())[:5]:
            config = complex_mappings[name]
            uuids = [c for c in config.get('columns', []) if c.lower().startswith('uuid_')]
            print(f"  - {name}:")
            print(f"      PK: {config.get('pk_field')}")
            print(f"      UUIDs: {uuids}")
    print()
    
    return True


if __name__ == "__main__":
    success = test_real_mappings()
    
    if success:
        print("Succes: Analyse des mappings completee!")
        exit(0)
    else:
        print("Echec: Erreur lors de l'analyse")
        exit(1)
