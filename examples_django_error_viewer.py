# -*- coding: utf-8 -*-
"""
Exemples pratiques - Django Error Viewer

Montre comment utiliser le Django Error Viewer dans différents contextes
du plugin MrvTeraka
"""

# ============================================================================
# EXEMPLE 1: Utilisation Simple dans PostgREST Client
# ============================================================================

def example_1_simple_usage():
    """Utilisation simple avec affichage automatique des erreurs"""
    from postgrest_client import PostgREST, PostgRESTMode

    # Initialiser le client
    postgrest = PostgREST(
        "http://localhost:8000",
        mode=PostgRESTMode.DJANGO
    )
    postgrest.set_auth_token("your_jwt_token")

    try:
        # Cette méthode affiche automatiquement les erreurs Django avec rendu HTML
        communes = postgrest.select_with_ui('communes')
        print(f"✅ {len(communes)} communes chargées")

    except RuntimeError as e:
        # L'erreur Django est déjà affichée dans l'interface
        # Ici on peut juste logger l'erreur
        print(f"❌ Erreur: {e}")


# ============================================================================
# EXEMPLE 2: Intégration dans DataValidationDialog
# ============================================================================

def example_2_validation_dialog():
    """Intégration dans le dialog de validation"""
    from postgrest_client import PostgREST, PostgRESTMode
    from validation_dialog import DataValidationDialog

    postgrest = PostgREST("http://localhost:8000", mode=PostgRESTMode.DJANGO)
    postgrest.set_auth_token("token")

    try:
        # Charger les données collectées
        collected_data = postgrest.select_with_ui('communes')

        # Charger les données originales
        original_data = postgrest.select_with_ui('communes_original')

        # Créer et afficher le dialog de validation
        dialog = DataValidationDialog(
            collected_data=collected_data,
            original_data=original_data
        )

        if dialog.exec_():
            print(f"✅ {len(dialog.validated_data)} enregistrements validés")
        else:
            print("❌ Validation annulée")

    except RuntimeError:
        # Erreur Django déjà affichée
        pass


# ============================================================================
# EXEMPLE 3: Gestion d'Erreurs avec Retry Logic
# ============================================================================

def example_3_with_retry():
    """Gestion d'erreurs avec logique de réessai"""
    from postgrest_client import PostgREST, PostgRESTMode
    import time

    postgrest = PostgREST("http://localhost:8000", mode=PostgRESTMode.DJANGO)
    postgrest.set_auth_token("token")

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            data = postgrest.select_with_ui('communes')
            print(f"✅ Données chargées au essai #{retry_count + 1}")
            return data

        except RuntimeError as e:
            retry_count += 1
            print(f"❌ Essai #{retry_count} échoué")

            if retry_count < max_retries:
                print(f"⏳ Réessai dans 3 secondes...")
                time.sleep(3)
            else:
                print(f"❌ Échec après {max_retries} essais")
                raise


# ============================================================================
# EXEMPLE 4: Affichage Personnalisé d'Erreur
# ============================================================================

def example_4_custom_error_display():
    """Afficher une erreur Django personnalisée"""
    from django_error_viewer import show_django_error

    # Simuler une réponse d'erreur Django
    html_error_page = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>404 Not Found</title>
    </head>
    <body>
        <h1>Page Not Found</h1>
        <p>The requested resource /api/communes/invalid/ was not found.</p>
    </body>
    </html>
    """

    # Afficher avec rendu HTML
    show_django_error(
        parent=None,
        error_code=404,
        error_reason="Not Found",
        html_content=html_error_page,
        url="http://localhost:8000/api/communes/invalid",
        method="GET",
        headers={
            'Content-Type': 'text/html; charset=utf-8',
            'Server': 'Django/3.2'
        },
        error_message="La ressource demandée n'existe pas sur le serveur"
    )


# ============================================================================
# EXEMPLE 5: Fusion avec Gestion d'Erreurs Django
# ============================================================================

def example_5_merge_with_error_handling():
    """Fusionner les données avec affichage UI des erreurs"""
    from postgrest_client import PostgREST, PostgRESTMode
    from mergin_workflow_manager import MerginWorkflowManager

    postgrest = PostgREST("http://localhost:8000", mode=PostgRESTMode.DJANGO)
    postgrest.set_auth_token("token")
    mgr = MerginWorkflowManager("plugin_dir")

    project_id = "communes_project"

    try:
        # Charger les données collectées
        collected_data = postgrest.select_with_ui('communes')

        # Valider les données
        validation_results = mgr.validate_data(project_id, collected_data)

        # Fusionner avec affichage UI des erreurs
        merge_results = mgr.merge_data(project_id, collected_data)

        # Synchroniser avec l'API - affiche erreur Django si elle survient
        try:
            result = postgrest.insert_with_ui('communes', merge_results)
            print(f"✅ {len(result)} enregistrements synchronisés")
        except RuntimeError:
            print("❌ Impossible de synchroniser - erreur Django affichée")
            # Sauvegarder les résultats localement
            mgr.save_error_backup(project_id, merge_results)

    except RuntimeError:
        pass


# ============================================================================
# EXEMPLE 6: Mappage Personnalisé d'Erreur
# ============================================================================

def example_6_error_mapping():
    """Mapper les erreurs Django à des actions spécifiques"""
    from postgrest_client import PostgREST, PostgRESTMode
    from django_error_viewer import DjangoErrorViewer

    postgrest = PostgREST("http://localhost:8000", mode=PostgRESTMode.DJANGO)

    # Codes d'erreur et actions correspondantes
    error_handlers = {
        401: lambda: print("🔐 Ré-authentification requise"),
        403: lambda: print("🚫 Permissions insuffisantes"),
        404: lambda: print("❓ Ressource non trouvée"),
        500: lambda: print("⚠️ Erreur serveur - Contacter support"),
        503: lambda: print("🛠️ Serveur en maintenance")
    }

    try:
        data = postgrest.select_with_ui('communes')
    except RuntimeError as e:
        # Extraire le code d'erreur depuis le message d'erreur
        import re
        match = re.search(r'HTTP (\d+)', str(e))
        if match:
            error_code = int(match.group(1))
            handler = error_handlers.get(error_code)
            if handler:
                handler()


# ============================================================================
# EXEMPLE 7: Classe Wrapper avec Gestion d'Erreurs
# ============================================================================

class PostgRESTWithErrorUI:
    """Wrapper de PostgREST avec gestion d'erreurs UI"""

    def __init__(self, api_url, token):
        from postgrest_client import PostgREST, PostgRESTMode
        self.postgrest = PostgREST(api_url, mode=PostgRESTMode.DJANGO)
        self.postgrest.set_auth_token(token)
        self.last_error = None

    def select(self, table, **kwargs):
        """Sélectionner avec gestion d'erreur"""
        try:
            return self.postgrest.select_with_ui(table, **kwargs)
        except RuntimeError as e:
            self.last_error = e
            raise

    def insert(self, table, data):
        """Insérer avec gestion d'erreur"""
        try:
            return self.postgrest.insert_with_ui(table, data)
        except RuntimeError as e:
            self.last_error = e
            raise

    def has_error(self):
        """Vérifier s'il y a une erreur"""
        return self.last_error is not None

    def get_last_error(self):
        """Récupérer la dernière erreur"""
        return self.last_error


def example_7_wrapper_usage():
    """Utiliser la classe wrapper"""
    api = PostgRESTWithErrorUI("http://localhost:8000", "token")

    try:
        communes = api.select('communes')
        print(f"✅ Chargé: {len(communes)} communes")
    except RuntimeError:
        if api.has_error():
            print(f"❌ Erreur: {api.get_last_error()}")


# ============================================================================
# EXEMPLE 8: Batch Operations avec Gestion d'Erreurs
# ============================================================================

def example_8_batch_operations():
    """Opérations en batch avec gestion centralisée d'erreurs"""
    from postgrest_client import PostgREST, PostgRESTMode

    postgrest = PostgREST("http://localhost:8000", mode=PostgRESTMode.DJANGO)
    postgrest.set_auth_token("token")

    operations = [
        ('select', 'communes'),
        ('select', 'districts'),
        ('select', 'regions'),
    ]

    results = {}
    failed = []

    for op_type, table in operations:
        try:
            if op_type == 'select':
                data = postgrest.select_with_ui(table)
                results[table] = data
                print(f"✅ {table}: {len(data)} enregistrements")
        except RuntimeError as e:
            failed.append((table, str(e)))
            print(f"❌ {table}: Erreur")

    if failed:
        print(f"\n⚠️ {len(failed)} table(s) échouée(s):")
        for table, error in failed:
            print(f"  - {table}")


# ============================================================================
# Tests d'Intégration
# ============================================================================

def run_all_examples():
    """Exécuter tous les exemples"""
    print("🚀 Démarrage des exemples Django Error Viewer\n")

    examples = [
        ("Simple Usage", example_1_simple_usage),
        ("Validation Dialog", example_2_validation_dialog),
        ("Retry Logic", example_3_with_retry),
        ("Custom Error Display", example_4_custom_error_display),
        ("Merge with Error Handling", example_5_merge_with_error_handling),
        ("Error Mapping", example_6_error_mapping),
        ("Wrapper Usage", example_7_wrapper_usage),
        ("Batch Operations", example_8_batch_operations),
    ]

    for name, func in examples:
        print(f"\n{'='*60}")
        print(f"EXEMPLE: {name}")
        print('='*60)
        try:
            func()
        except Exception as e:
            print(f"❌ Erreur dans l'exemple: {e}")


if __name__ == "__main__":
    # Exécuter les exemples
    run_all_examples()

