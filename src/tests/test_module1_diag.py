import pytest
from unittest.mock import patch, MagicMock

# Exemple de fonction à tester
def run_db():
    # simulation de la connexion à la base de données en local
    import mariadb
    conn = mariadb.connect(
        user="admin",
        password="admin",
        host="localhost",
        port=3306,
        database="testdb"
    )

    # On lance la commande SELECT 1 si les paramètres sont correctes, elle doit nous renvoyer 1
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# Test avec mock
def test_run_db():
    # Simulation d'une connexion à une fausse base de données (mock)
    with patch("mariadb.connect") as mock_connect:
        mock_cursor = MagicMock()
        # simulation du résultat
        mock_cursor.fetchall.return_value = [(1,)]  
        mock_cursor.close.return_value = None

        # Connexion factice
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.close.return_value = None

        mock_connect.return_value = mock_conn

        # Appel de la fonction
        result = run_db()

        # Vérifications
        mock_connect.assert_called_once_with(
            user="admin",
            password="admin",
            host="localhost",
            port=3306,
            database="testdb"
        )
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.fetchall.assert_called_once()
        assert result == [(1,)]