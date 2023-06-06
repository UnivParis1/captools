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

```text
~/myhome/captools$ python3 gen_csv.py --help
usage: gen_csv.py [-h] -u USERS [USERS ...] -s SUFFIX

Génère un CSV d'import dans Caplab depuis un annuaire LDAP à partir de la liste des emails des comptes à ajouter ou d'une catégorie d'utilisateurs.

options:
  -h, --help            show this help message and exit
  -u USERS [USERS ...], --users USERS [USERS ...]
                        Catégorie ou adresses mail des personnes à inclure dans le CSV, séparées par des espaces
  -s SUFFIX, --suffix SUFFIX
                        Suffixe à ajouter au nom de fichier
 
```

##### Par énumération

Créez un fichier d'import CSV comportant les utilisateurs dont les mails sont listés :

```shell
python3 gen_csv.py -u jean.dupont@univ-paris1.fr jeanne.durant@univ-paris1.fr claude.dubois@univ-paris1.fr
```

Le fichier généré est encodé en ISO-8859-1 conformément aux attendus de l'import Caplab

##### Par catégorie

Créez un fichier d'import CSV comportant une catégorie d'utilisateurs (pour l'instant, seuls les évaluateurs externes
AAPi via l'attribut eduPersonEntitlement) :

```shell
python3 gen_csv.py -u experts
```
##### Nommage du fichier en sortie

Par défaut, le nom du fichier en sortie est doté d'un timestamp : ex. import_caplab_20230605181121.csv
Ce comportement peut être contournée en utilisant l'option -s

