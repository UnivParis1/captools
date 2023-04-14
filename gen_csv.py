import argparse
import csv
import shutil
import time
from datetime import date

import ldap
from dotenv import dotenv_values

ORIGINAL_CSV_FILE_PATH = 'data/CAPLAB_DCT_IPE_FichierPersonne_1.6.csv'

PEOPLE_BRANCH = 'ou=people,dc=univ-paris1,dc=fr'

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


def fetch_users(mails: list[str]) -> list[dict]:
    """
    Interroge le LDAP pour chaque email fourni en entrée

    :param mails: liste des adresses email
    :return: liste des enregistrements LDAP trouvés
    """

    connexion = ldap.initialize(config['LDAP_URL'])
    users = []
    for mail in mails:
        query = f"mail={mail}"
        ldap_response = connexion.search_s(PEOPLE_BRANCH,
                                           ldap.SCOPE_SUBTREE,
                                           query)
        if len(ldap_response) == 0:
            print(f"Utilisateur {mail} non trouvé dans l'annuaire")
            continue
        users.append(ldap_response[0][1])
    return users


def build_csv_row(user: dict, today_str: str) -> list[str]:
    """
    Construit la ligne de CSV depuis l'enregistrement utilisateur trouvé dans le LDAP

    :param user: données utilisateur trouvé dans le LDAP
    :param today_str: date du jour, JJ/MM/AAAA, qui tient lieu de date d'arrivée fictive
    :return: liste de valeurs à insérer, dans l'ordre attendu
    """
    return [config['UNIV_UAI'],
            config['UNIV_NAME'],
            config['UNIV_UAI'],
            "",
            user['sn'][0].decode(),
            user['givenName'][0].decode(),
            user['mail'][0].decode(),
            today_str,
            today_str,
            "",
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
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        for user in users:
            values = build_csv_row(user, today_str)
            writer.writerow(dict(zip(fieldnames, values)))
    print(f"Fichier généré {output_file_name}")


def main(args):
    users = fetch_users(args.users)
    output_file_name = create_output_file()
    write_data(users, output_file_name)


if __name__ == '__main__':
    main(parse_arguments())
