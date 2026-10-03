# 🚗 Tomobil

Application Streamlit pour conducteurs, techniciens et experts automobiles.

## Fonctionnalités
- Création de compte avec choix du métier (Conducteur, Technicien / Mécanicien, Expert automobile)
- Mes voitures et kilométrage
- Rappels de dates (visite technique, vidange, assurance...) avec code couleur
- Conseils par partie de la voiture, avec photos
- Demandes de service avec offres de prix des techniciens (façon inDrive)
- Discussions : communauté, experts & techniciens, salon privé par mission
- Vidéos pour réparer soi-même

## Fichiers
| Fichier | Rôle |
|---|---|
| `app.py` | Application complète |
| `dataset.csv` | Conseils et vidéos (colonnes : type, categorie, titre, contenu, lien, image) |
| `requirements.txt` | Dépendances |
| `README.md` | Ce fichier |

La base `mycar.db` est créée automatiquement au premier lancement.

## Test en local (Windows, invite de commandes)
Aucun compte GitHub ni Streamlit Cloud n'est nécessaire.
```bat
cd chemin\vers\mycar
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
```
Le navigateur s'ouvre sur http://localhost:8501. Arrêt : `Ctrl + C` dans la fenêtre cmd.

Pour tester : créez un compte « Conducteur », ajoutez une voiture, un rappel et une demande de service ; puis ouvrez une fenêtre de navigation privée, créez un compte « Technicien » et envoyez une offre.

## Images
Les photos viennent d'Unsplash et Pexels (libres de droits) et nécessitent internet. Si une image ne charge pas, une photo de secours s'affiche.
Pour utiliser vos propres photos : placez-les à côté de `app.py` et écrivez leur nom (ex. `freins.jpg`) dans la colonne `image` de `dataset.csv`.

## Vidéos
Colonne `lien` : une URL `https://www.youtube.com/watch?v=...` se lit directement dans l'application.

## Comptes et hébergement
- Les comptes sont stockés dans `mycar.db` (SQLite), créée automatiquement.
- Sur **Streamlit Cloud**, le disque est temporaire : la base est effacée à chaque redémarrage ou mise à jour de l'application. Les comptes créés disparaissent alors.
- Pour garder des comptes de test, 3 comptes de démonstration sont recréés automatiquement (`SEED_DEMO = True` dans `app.py`) : `conducteur@demo.com`, `technicien@demo.com`, `expert@demo.com`, mot de passe `demo1234`. Mettez `SEED_DEMO = False` pour les supprimer.
- Pour un stockage permanent en ligne, il faut une base externe (par exemple Supabase).
