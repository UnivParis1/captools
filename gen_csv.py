import argparse
import csv
import re
import shutil
import time
from datetime import date
import pandas as pd

import ldap
from dotenv import dotenv_values

ORIGINAL_CSV_FILE_PATH = 'data/CAPLAB_DCT_IPE_FichierPersonne_2.0.csv'

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
                    'à partir de la liste des emails des comptes à ajouter ou d\'une catégorie d\'utilisateurs.')
    parser.add_argument('-u', '--users', nargs='+',
                        help='Catégorie ou adresses mail des personnes à inclure dans le CSV, '
                             'séparées par des espaces',
                        required=True)
    parser.add_argument('-s', '--suffix', default=None,
                        help='Suffixe à ajouter au nom de fichier',
                        required=True)
    return parser.parse_args()


def create_output_file(suffix: str = None) -> str:
    """
    Génère un nom de fichier de sortie avec timestamp

    :param suffix: str Suffixe à ajouter au nom de fichier
    :return: le chemin du fichier de sortie
    """
    output = f"data/import_caplab_{suffix or time.strftime('%Y%m%d%H%M%S')}.csv"
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
                    if (acronym and f"{acronym.upper()} :" in title.upper()) or (
                            nom and nom.upper() in title.upper()) or (
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


def fetch_experts() -> list[dict]:
    """
    Interroge le LDAP pour les experts Caplab

    :param mails: liste des adresses email
    :return: liste des enregistrements LDAP trouvés
    """

    connexion = ldap.initialize(config['LDAP_URL'])
    connexion.set_option(ldap.OPT_REFERRALS, 0)
    connexion.simple_bind_s(config['LDAP_DN'], config['LDAP_PASSWD'])
    ldap_users = connexion.search_s(PEOPLE_BRANCH,
                                    ldap.SCOPE_SUBTREE,
                                    '(&(objectClass=supannPerson)(eduPersonEntitlement=https://entitlement.p1ps.fr/application=caplab/eval-aapi))')
    if len(ldap_users) == 0:
        print("Aucun utilisateur expert trouvé dans l'annuaire")
        return []
    users = [ldap_user[1] | {'unit_code': None, 'unit_title': None, 'unit_role': None} for ldap_user in
             ldap_users]
    return users


def build_csv_row(user: dict, today_str: str, universities: pd.DataFrame) -> list[str]:
    """
    Construit la ligne de CSV depuis l'enregistrement utilisateur trouvé dans le LDAP

    :param user: données utilisateur trouvé dans le LDAP
    :param today_str: date du jour, JJ/MM/AAAA, qui tient lieu de date d'arrivée fictive
    :return: liste de valeurs à insérer, dans l'ordre attendu
    """
    etab_uai = config['UNIV_UAI']
    etab_name = config['UNIV_NAME']
    if 'supannEtablissement' in user:
        user_etab = user['supannEtablissement'][0].decode()
        search = re.search(r"\{UAI\}(.+)", user_etab)
        uai_found = len(search.groups())
        while uai_found > 0:
            uai = search.groups()[0]
            if uai == etab_uai:
                break
            from_scanr = universities[universities['uai - identifiant'] == uai]
            if len(from_scanr) == 0:
                break
            etab_name = from_scanr.iloc[0]['Libellé']
            etab_uai = uai
            uai_found = 0

    unit_code = user['unit_code'] or etab_uai
    unit_title = user['unit_title'] or ""
    unit_role = user['unit_role'] or ""

    user_mail = None
    if 'mail' in user and len(user['mail']) > 0:
        user_mail = user['mail'][0].decode()
    if 'supannMailPerso' in user and len(user['supannMailPerso']) > 0:
        user_mail = user['supannMailPerso'][0].decode()
    return [etab_uai,
            etab_name,
            unit_code,
            unit_title,
            user['sn'][0].decode(),
            user['givenName'][0].decode(),
            user_mail,
            today_str,
            today_str,
            unit_role,
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


def write_data(users: list[dict], output_file_name: str, universities: pd.DataFrame) -> None:
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
            values = build_csv_row(user, today_str, universities)
            writer.writerow(dict(zip(fieldnames, values)))
    print(f"Fichier généré {output_file_name}")


def load_research_units() -> pd.DataFrame:
    """
    Load research units from Caplab CSV export

    :return: Research unit table
    """
    return pd.read_csv("data/export_ur.csv", delimiter=";")


def load_universities() -> pd.DataFrame:
    """
    Load research units from Caplab CSV export

    :return: Research unit table
    """
    return pd.read_csv("data/fr-esr-principaux-etablissements-enseignement-superieur.csv", delimiter=";")


def main(args):
    universities = load_universities()
    if len(args.users) == 1 and args.users[0] == "experts":
        users = fetch_experts()
    else:
        research_units = load_research_units()
        users = fetch_users(args.users, research_units)
    output_file_name = create_output_file(suffix=args.suffix)
    write_data(users, output_file_name, universities=universities)


if __name__ == '__main__':
    main(parse_arguments())
