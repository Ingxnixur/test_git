"""Extrait les intentions de vote au premier tour de la présidentielle 2022.

Source : Wikipédia, « Liste de sondages sur l'élection présidentielle
française de 2022 ». Chaque valeur garde le lien vers la notice du sondage
(Commission des sondages ou site de l'institut).

Règles appliquées :
- période : du 1er octobre 2021 au 31 mars 2022 (six mois civils avant le
  premier tour du 10 avril 2022) ;
- date retenue : dernier jour de terrain du sondage ;
- en octobre et novembre 2021, la droite n'a pas encore choisi sa candidate.
  On garde seulement les hypothèses où Valérie Pécresse représente LR ;
- « <0,5 % » devient 0,25 et « <1 % » devient 0,5 (moitié du seuil) ;
- « — » signifie « non testé » : la valeur est ignorée.

Usage : python intentions_de_vote.py [chemin_html]
Sans argument, le script télécharge la page.
"""

import csv
import io
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

URL = ("https://fr.wikipedia.org/wiki/Liste_de_sondages_sur_l%27%C3%A9lection_"
       "pr%C3%A9sidentielle_fran%C3%A7aise_de_2022")
SORTIE = Path(__file__).resolve().parent.parent / "data" / "intentions_de_vote_2022.csv"

# Nom de colonne Wikipédia -> (prénom, nom)
CANDIDATS = {
    "Arthaud": ("Nathalie", "Arthaud"),
    "Poutou": ("Philippe", "Poutou"),
    "Roussel": ("Fabien", "Roussel"),
    "Mélenchon": ("Jean-Luc", "Mélenchon"),
    "Hidalgo": ("Anne", "Hidalgo"),
    "Jadot": ("Yannick", "Jadot"),
    "Macron": ("Emmanuel", "Macron"),
    "Pécresse": ("Valérie", "Pécresse"),
    "Lassalle": ("Jean", "Lassalle"),
    "Dupont-Aignan": ("Nicolas", "Dupont-Aignan"),
    "Le Pen": ("Marine", "Le Pen"),
    "Zemmour": ("Éric", "Zemmour"),
}

MOIS = {"janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10,
        "novembre": 11, "décembre": 12}

# Index des tableaux utiles dans la page, avec l'année des sondages.
# 0 : après la liste officielle (mars-avril 2022), 1 : mars 2022,
# 2 : février 2022, 3 : janvier 2022, 4 : décembre 2021,
# 5 : octobre-novembre 2021.
TABLEAUX = {0: 2022, 1: 2022, 2: 2022, 3: 2022, 4: 2021, 5: 2021}

DEBUT, FIN = date(2021, 10, 1), date(2022, 3, 31)


def institut_normalise(nom):
    """Harmonise l'orthographe : 'Harris Interractive' -> 'Harris Interactive'."""
    nom = re.sub(r"\[.*?\]", "", nom).strip()
    rolling = " (rolling)" if "rolling" in nom.lower() else ""
    nom = re.sub(r"\(rolling\)", "", nom, flags=re.I).strip()
    corrections = {"opinionway": "OpinionWay", "harris interractive": "Harris Interactive",
                   "cluster 17": "Cluster17"}
    return corrections.get(nom.lower(), nom) + rolling


def texte(cellule):
    """pandas renvoie (texte, lien) avec extract_links='all'."""
    return cellule[0] if isinstance(cellule, tuple) else cellule


def date_fin(libelle, annee):
    """'29 septembre- 1er octobre' -> date(…, 10, 1)."""
    fin = libelle.split("-")[-1].strip()
    m = re.match(r"(\d+)(?:er)?\s+(\w+)", fin)
    if not m or m.group(2).lower() not in MOIS:
        return None
    return date(annee, MOIS[m.group(2).lower()], int(m.group(1)))


def valeur(brut):
    if brut is None or not isinstance(brut, str):
        return None
    brut = re.sub(r"\[.*?\]", "", brut).replace("\xa0", " ").strip()
    m = re.search(r"(<)?\s*(\d+(?:,\d+)?)\s*%?", brut)
    if not m:
        return None
    nombre = float(m.group(2).replace(",", "."))
    return nombre / 2 if m.group(1) else nombre


def candidat_de_colonne(entete):
    for cle in CANDIDATS:
        if entete.startswith(cle):
            return cle
    return None


def extraire(html):
    from bs4 import BeautifulSoup

    tables = BeautifulSoup(html, "lxml").select("table.wikitable")
    lignes = []
    for index, annee in TABLEAUX.items():
        df = pd.read_html(io.StringIO(str(tables[index])), extract_links="all")[0]
        entetes = [texte(c[-1] if isinstance(c, tuple) and isinstance(c[-1], tuple) else c)
                   for c in df.columns]
        entetes = [re.sub(r"\[.*?\]", "", e).strip() for e in entetes]
        for _, ligne in df.iterrows():
            cellules = list(ligne)
            sondeur, lien = cellules[0] if isinstance(cellules[0], tuple) else (cellules[0], None)
            dates = texte(cellules[1])
            if not isinstance(dates, str) or dates == texte(cellules[0]):
                continue  # ligne d'événement ou d'en-tête
            jour = date_fin(dates, annee)
            if jour is None or not (DEBUT <= jour <= FIN):
                continue
            hypothese = []
            retenue = True
            for entete, cellule in zip(entetes, cellules):
                brut = texte(cellule)
                cle = candidat_de_colonne(entete)
                if entete.startswith("Candidat LR"):
                    # Colonne « Candidat LR » : on ne garde que Pécresse.
                    if not isinstance(brut, str) or "Pécresse" not in brut:
                        retenue = False
                        break
                    cle = "Pécresse"
                if cle is None:
                    continue
                v = valeur(brut)
                if v is None:
                    continue
                prenom, nom = CANDIDATS[cle]
                hypothese.append({
                    "prenom": prenom, "nom": nom, "date": jour.isoformat(),
                    "valeur": v, "institut": institut_normalise(sondeur),
                    "url_source": lien or URL,
                })
            if retenue:
                lignes.extend(hypothese)
    return lignes


def main():
    if len(sys.argv) > 1:
        html = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        requete = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (script de recherche)"})
        html = urllib.request.urlopen(requete).read().decode("utf-8")
    lignes = extraire(html)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", newline="", encoding="utf-8") as f:
        champs = ["prenom", "nom", "date", "valeur", "institut", "url_source"]
        ecrivain = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        ecrivain.writeheader()
        ecrivain.writerows(lignes)
    print(f"{len(lignes)} valeurs écrites dans {SORTIE}")


if __name__ == "__main__":
    main()
