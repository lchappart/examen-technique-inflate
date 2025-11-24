# Examen Technique - Système d'Import et d'Avis Clients

Ce projet Django permet d'importer massivement des clients et des commandes depuis un fichier CSV, et gère l'envoi automatique d'emails de demande d'avis (transactionnels).

## 📋 Fonctionnalités

* **Import CSV Robuste** : Gestion des clients, commandes et produits avec support du format JSON.
* **Intégrité des Données** : Utilisation de `transaction.atomic` pour garantir qu'aucune donnée partielle n'est sauvegardée en cas d'erreur.
* **Options Avancées** : Mode `dry-run` (simulation), barre de progression (`tqdm`) et gestion de la verbosité.
* **Emails Transactionnels** : Envoi d'emails HTML via des templates Django.
* **Tests Unitaires** : Couverture des modèles et de la logique métier.

## 🛠️ Prérequis

* Python 3.8+
* Django 4.2+
* Tqdm (Barre de progression)

## 🚀 Installation

1.  **Cloner le projet et se placer dans le dossier :**
    ```bash
    cd inflate_back
    ```

2.  **Créer et activer l'environnement virtuel :**
    * Windows :
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    * Mac/Linux :
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Installer les dépendances :**
    ```bash
    pip install django tqdm
    # Ou si le fichier requirements.txt est présent :
    # pip install -r requirements.txt
    ```

4.  **Appliquer les migrations (Base de données) :**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

## ⚙️ Utilisation

### 1. Import des données (CSV)

La commande `import_csv` lit un fichier CSV et peuple la base de données.

* **Usage standard :**
    ```bash
    python manage.py import_csv
    ```
    *(Par défaut, cherche un fichier `sample_data.csv` à la racine)*

* **Fichier personnalisé :**
    ```bash
    python manage.py import_csv mon_fichier.csv
    ```

* **Mode Simulation (Dry-Run) :**
    Exécute le script, affiche les erreurs potentielles, mais **n'enregistre rien** en base de données.
    ```bash
    python manage.py import_csv --dry-run
    ```

### 2. Envoi des demandes d'avis

Cette commande recherche toutes les commandes n'ayant pas encore reçu d'email (`mail_sent=False`) et envoie une invitation HTML.

```bash
python manage.py send_review_emails