# MSPR_DEV_GRP1

installer les modules :

py -m pip install -e .

pour lancer l'appli :

py -m ntl_systoolbox.main

## CI/CD

Le projet utilise GitHub Actions pour automatiser les tests et le déploiement. Les workflows sont définis dans le dossier `.github/workflows`.

On utilise la pipeline `python application` pour exécuter les tests unitaires et vérifier la qualité du code à chaque push ou pull request. Si les tests passent, le workflow `python package` est déclenché pour construire et publier le package sur PyPI.

## tests

Les tests unitaires sont situés dans le dossier `src/tests`. Ils couvrent les différentes fonctionnalités de l'application pour assurer la fiabilité du code.
