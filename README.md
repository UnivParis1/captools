# Captools

## Utilitaires en lien avec le projet Caplab

### gen_csv (en cours de développement)

Générateur du fichier CSV d'import des personnes depuis un annuaire LDAP
(Cas où Caplab n'est pas alimenté automatiquement)

#### Installation

- Cloner le projet

```shell
git clone https://github.com/UnivParis1/captools.git
cd captools
```

- Créez un environnement virtuel (optionnel)

```shell
python3 -m venv venv
source venv/bin/activate
```

- Installez les dépendances

```shell
pip install -r requirements.txt
```

- Dupliquez le fichier d'environnement et définissez les variables d'environnement locales

```shell
cp .env.example .env
```

Éditez le fichier .env

- Téléchargez la restitution Caplab 'Liste des unités de recherche'


  Enregistrez la en CSV, avec le separateur ';' et l'encodage UTF-8, sous 'data/export_ur.csv'
  Supprimez toutes les lignes d'informations après la dernière ligne de données

#### Usage

Créez un fichier d'import CSV comportant les utilisateurs dont les mails sont listés :

```shell
python3 gen_csv.py -u jean.dupont@univ-paris1.fr jeanne.durant@univ-paris1.fr claude.dubois@univ-paris1.fr
```

Le fichier généré est encodé en ISO-8859-1 conformément aux attendus de l'import Caplab