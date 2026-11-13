"""Construit la base SQLite à partir des fichiers CSV du dossier data/.

Tables :
- candidat (id, prenom, nom, annee_election, qualifie_second_tour)
- cote_popularite (id, candidat_id, date, valeur, type_mesure,
  libelle_mesure, institut, url_source)

type_mesure vaut « intention_de_vote » ou « popularite ».
"""

import csv
import sqlite3
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
BASE = DATA / "presidentielle.sqlite"

SCHEMA = """
DROP TABLE IF EXISTS cote_popularite;
DROP TABLE IF EXISTS candidat;

CREATE TABLE candidat (
    id                   INTEGER PRIMARY KEY,
    prenom               TEXT    NOT NULL,
    nom                  TEXT    NOT NULL,
    annee_election       INTEGER NOT NULL,
    qualifie_second_tour INTEGER NOT NULL CHECK (qualifie_second_tour IN (0, 1)),
    UNIQUE (prenom, nom, annee_election)
);

CREATE TABLE cote_popularite (
    id             INTEGER PRIMARY KEY,
    candidat_id    INTEGER NOT NULL REFERENCES candidat(id),
    date           TEXT    NOT NULL,   -- dernier jour de terrain, AAAA-MM-JJ
    valeur         REAL    NOT NULL,   -- en %
    type_mesure    TEXT    NOT NULL CHECK (type_mesure IN ('intention_de_vote', 'popularite')),
    libelle_mesure TEXT,
    institut       TEXT,
    url_source     TEXT
);

CREATE INDEX idx_cote_candidat ON cote_popularite (candidat_id, type_mesure, date);
"""


def lire(chemin):
    if not chemin.exists():
        print(f"Fichier absent, ignoré : {chemin.name}")
        return []
    with chemin.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    candidats = lire(DATA / "candidats.csv")
    connexion = sqlite3.connect(BASE)
    connexion.executescript(SCHEMA)
    connexion.executemany(
        "INSERT INTO candidat (prenom, nom, annee_election, qualifie_second_tour) "
        "VALUES (:prenom, :nom, :annee_election, :qualifie_second_tour)",
        candidats,
    )
    ids = {(p, n): i for i, p, n in connexion.execute("SELECT id, prenom, nom FROM candidat")}

    mesures = [
        ("intention_de_vote", DATA / "intentions_de_vote_2022.csv", "intention de vote au 1er tour"),
        ("popularite", DATA / "popularite_2022.csv", None),
    ]
    for type_mesure, chemin, libelle_defaut in mesures:
        lignes = lire(chemin)
        inconnus = {(l["prenom"], l["nom"]) for l in lignes} - set(ids)
        if inconnus:
            raise ValueError(f"Candidats absents de candidats.csv : {inconnus}")
        connexion.executemany(
            "INSERT INTO cote_popularite (candidat_id, date, valeur, type_mesure, "
            "libelle_mesure, institut, url_source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(ids[(l["prenom"], l["nom"])], l["date"], float(l["valeur"]), type_mesure,
              l.get("mesure") or libelle_defaut, l.get("institut"), l.get("url_source"))
             for l in lignes if l.get("valeur") not in (None, "")],
        )
        print(f"{type_mesure} : {len(lignes)} valeurs chargées")

    connexion.commit()
    connexion.close()
    print(f"Base écrite : {BASE}")


if __name__ == "__main__":
    main()
