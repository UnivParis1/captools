import argparse
import csv
import re
import shutil
import time
from datetime import date
import pandas as pd

import ldap
from dotenv import dotenv_values

ORIGINAL_CSV_FILE_PATH = 'data/CAPLAB_DCT_IPE_FichierPersonne_1.6.csv'

PEOPLE_BRANCH = 'ou=people,dc=univ-paris1,dc=fr'
STRUCTURE_BRANCH = 'ou=structures,o=Paris1,dc=univ-paris1,dc=fr'

config = dotenv_values(".env")


def parse_arguments() -> argparse.Namespace:
    """
    Parses user command line

    :return: argparse data structure
    """
    parser = argparse.ArgumentParser(
        description='Génère un CSV d\'import dans Caplab depuis un annuaire LDAP '
                    'à partir de la liste des emails des comptes à ajouter.')
    parser.add_argument('-u', '--users', nargs='+',
                        help='Adresses mail des personnes à inclure dans le CSV, '
                             'séparées par des espaces',
                        required=True)
    return parser.parse_args()


def create_output_file() -> str:
    """
    Génère un nom de fichier de sortie avec timestamp

    :return: le chemin du fichier de sortie
    """
    output = f"data/import_caplab_{time.strftime('%Y%m%d%H%M%S')}.csv"
    shutil.copyfile(ORIGINAL_CSV_FILE_PATH, output)
    return output


def extract_field_names() -> list[str]:
    """
    Extrait les noms des chmps du template d'import Caplab

    :return:  la liste des noms des champs, encodée en ISO-8859-1
    """
    fieldnames = None
    with open(ORIGINAL_CSV_FILE_PATH, 'r', newline='', encoding='iso-8859-1') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for row in csv_reader:
            fieldnames = row
            break
    return list(map(lambda s: s.encode('latin1'), fieldnames))


def fetch_users(mails: list[str], research_units: pd.DataFrame) -> list[dict]:
    """
    Interroge le LDAP pour chaque email fourni en entrée

    :param mails: liste des adresses email
    :return: liste des enregistrements LDAP trouvés
    """

    connexion = ldap.initialize(config['LDAP_URL'])
    users = []
    for mail in mails:
        ldap_user = connexion.search_s(PEOPLE_BRANCH,
                                       ldap.SCOPE_SUBTREE,
                                       f"mail={mail}")
        if len(ldap_user) == 0:
            print(f"Utilisateur {mail} non trouvé dans l'annuaire")
            continue
        user = ldap_user[0][1] | {'unit_code': None, 'unit_title': None, 'unit_role': None}
        if user['eduPersonPrimaryAffiliation'][0] in [b'teacher', b'researcher']:
            for struct_identifier in user['supannEntiteAffectation']:
                ldap_struct = connexion.search_s(STRUCTURE_BRANCH,
                                                 ldap.SCOPE_SUBTREE,
                                                 f"ou={struct_identifier.decode()}")
                cat = ldap_struct[0][1]['businessCategory']
                if b'research' not in cat and b'pedagogy' not in cat:
                    continue
                title = ldap_struct[0][1]['description'][0].decode().split(' - ')[1]
                title = title.replace("\xa0", " ")
                for _, research_unit in research_units.iterrows():
                    acronym = research_unit['Acronyme']
                    if pd.isna(acronym):
                        acronym = None
                    nom = research_unit['Nom de l\'unité']
                    if pd.isna(nom):
                        nom = None
                    num = research_unit['Code interne de l\'unité']
                    if pd.isna(num):
                        num = None
                    else:
                        num = re.sub("[^0-9]", "", num)
                    if (acronym and f"{acronym.upper()} :" in title.upper()) or (nom and nom.upper() in title.upper()) or (
                            num and num in title):
                        user['unit_code'] = research_unit['Code RNSR']
                        user['unit_title'] = nom.replace('\u2019', "'")
                    else:
                        continue
                    if 'supannRoleEntite' not in user:
                        continue
                    unit_role = user['supannRoleEntite'][0].decode()
                    if struct_identifier.decode() in unit_role and any(
                            f"{{UAI:0751717J:HARPEGE.FCSTR}}{s}" in unit_role for s in ["529", "530", "532"]):
                        user['unit_role'] = "DU"
                user['research_unit'] = ldap_struct[0][1]['description'][0].decode().split('-')[1]
        users.append(user)
    return users


def build_csv_row(user: dict, today_str: str) -> list[str]:
    """
    Construit la ligne de CSV depuis l'enregistrement utilisateur trouvé dans le LDAP

    :param user: données utilisateur trouvé dans le LDAP
    :param today_str: date du jour, JJ/MM/AAAA, qui tient lieu de date d'arrivée fictive
    :return: liste de valeurs à insérer, dans l'ordre attendu
    """
    unit_code = user['unit_code'] or config['UNIV_UAI']
    unit_title = user['unit_title'] or ""
    unit_role = user['unit_role'] or ""

    return [config['UNIV_UAI'],
            config['UNIV_NAME'],
            unit_code,
            unit_title,
            user['sn'][0].decode(),
            user['givenName'][0].decode(),
            user['mail'][0].decode(),
            today_str,
            today_str,
            unit_role,
            "",
            "",
            "",
            "",
            "",
            user['supannCivilite'][0].decode(),
            "",
            "FR",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            user['eduPersonPrincipalName'][0].decode()
            ]


def write_data(users: list[dict], output_file_name: str) -> None:
    """
    Writes LDAP data to output CSV file

    :param users: list of rows returned by LDAP
    :param output_file_name: path to the resulting CSV file
    """
    fieldnames = extract_field_names()
    today_str = date.today().strftime("%d/%m/%Y")
    with open(output_file_name, 'a', newline='', encoding='iso-8859-1') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_ALL)
        for user in users:
            values = build_csv_row(user, today_str)
            writer.writerow(dict(zip(fieldnames, values)))
    print(f"Fichier généré {output_file_name}")


def load_research_units() -> pd.DataFrame:
    """
    Load research units from Caplab CSV export

    :return: Research unit table
    """
    return pd.read_csv("data/export_ur.csv", delimiter=";")


def main(args):
    research_units = load_research_units()
    users = fetch_users(args.users, research_units)
    output_file_name = create_output_file()
    write_data(users, output_file_name)


if __name__ == '__main__':
    main(parse_arguments())
