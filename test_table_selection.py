# -*- coding: utf-8 -*-
"""
Script de test pour la boîte de dialogue de sélection de tables.

Exécutez ce script depuis la console Python de QGIS pour tester le dialogue.
"""

def test_table_selection_dialog():
    """Test avec un grand nombre de tables."""
    from table_selection_dialog import show_table_selection_dialog
    from qgis.utils import iface

    # Créer un grand nombre de tables de test
    test_tables = {}

    # Catégories de tables
    categories = ['parcelles', 'forets', 'villages', 'routes', 'rivieres']

    for i in range(50):  # 50 tables pour tester le scroll
        category = categories[i % len(categories)]
        table_name = f"{category}_{i+1:03d}"
        test_tables[table_name] = {
            'endpoint': f"api/v1/{table_name}",
            'pk_field': 'id',
            'layer_name': table_name
        }

    print(f"\n=== Test de sélection avec {len(test_tables)} tables ===\n")

    # Afficher le dialogue
    selected, mappings, is_all = show_table_selection_dialog(
        test_tables,
        iface.mainWindow(),
        "Test: Sélection de tables (50 tables)"
    )

    if selected is not None:
        print(f"\n✓ Sélection confirmée:")
        print(f"  - Nombre de tables sélectionnées: {len(selected)}")
        print(f"  - Toutes sélectionnées: {is_all}")
        print(f"  - Tables sélectionnées: {', '.join(selected[:10])}")
        if len(selected) > 10:
            print(f"    ... et {len(selected) - 10} autres")
    else:
        print("\n✗ Sélection annulée")


def test_small_selection():
    """Test avec peu de tables."""
    from table_selection_dialog import show_table_selection_dialog
    from qgis.utils import iface

    # Petite liste de tables
    test_tables = {
        'parcelles': {'endpoint': 'api/parcelles', 'pk_field': 'id'},
        'forets': {'endpoint': 'api/forets', 'pk_field': 'gid'},
        'villages': {'endpoint': 'api/villages', 'pk_field': 'village_id'}
    }

    print(f"\n=== Test de sélection avec {len(test_tables)} tables ===\n")

    selected, mappings, is_all = show_table_selection_dialog(
        test_tables,
        iface.mainWindow(),
        "Test: Sélection de tables (3 tables)"
    )

    if selected is not None:
        print(f"\n✓ Sélection confirmée:")
        print(f"  - Tables sélectionnées: {', '.join(selected)}")
        print(f"  - Toutes sélectionnées: {is_all}")
        print(f"\n  Mappings:")
        for name, mapping in mappings.items():
            print(f"    - {name}: {mapping.get('endpoint')}")
    else:
        print("\n✗ Sélection annulée")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("TESTS DE LA BOÎTE DE DIALOGUE DE SÉLECTION")
    print("="*60)

    # Test 1: Petite sélection
    print("\nTest 1: Petite sélection (3 tables)")
    print("-" * 60)
    test_small_selection()

    # Test 2: Grande sélection
    print("\n\nTest 2: Grande sélection (50 tables)")
    print("-" * 60)
    test_table_selection_dialog()

    print("\n" + "="*60)
    print("FIN DES TESTS")
    print("="*60 + "\n")
