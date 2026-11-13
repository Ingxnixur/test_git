"""Trace les courbes des six mois qui précèdent le premier tour.

Deux visions par mesure :
- « par élection » : une courbe par candidat, abscisse en mois civils ;
- « superposée » : abscisse relative (M-6 à M-1) pour comparer les
  élections. Les candidats qualifiés au second tour sont en couleur,
  les autres en gris.

Chaque point est la moyenne des valeurs publiées dans le mois.
"""

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
BASE = RACINE / "data" / "presidentielle.sqlite"
SORTIE = RACINE / "graphiques"

# Dates des premiers tours (ministère de l'Intérieur).
PREMIER_TOUR = {2022: "2022-04-10"}

# Couleurs proches de celles des partis, assez distinctes entre elles.
COULEURS = {
    "Arthaud": "#8b0000", "Poutou": "#e8590c", "Roussel": "#d6336c",
    "Mélenchon": "#c92a2a", "Hidalgo": "#f783ac", "Jadot": "#2b8a3e",
    "Macron": "#f2b705", "Pécresse": "#1c7ed6", "Lassalle": "#0ca678",
    "Dupont-Aignan": "#7048e8", "Le Pen": "#0b2e6b", "Zemmour": "#5c3d2e",
}

TITRES = {
    "intention_de_vote": ("Intentions de vote au premier tour", "Intentions de vote (%)"),
    "popularite": ("Cote de popularité", "Popularité (%)"),
}

MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
               "août", "sept.", "oct.", "nov.", "déc."]


def charger():
    with sqlite3.connect(BASE) as connexion:
        df = pd.read_sql_query(
            """SELECT c.prenom, c.nom, c.annee_election, c.qualifie_second_tour,
                      p.date, p.valeur, p.type_mesure, p.libelle_mesure, p.institut
               FROM cote_popularite p JOIN candidat c ON c.id = p.candidat_id""",
            connexion,
        )
    df["date"] = pd.to_datetime(df["date"])
    df["mois"] = df["date"].dt.to_period("M")
    tour = df["annee_election"].map(lambda a: pd.Period(PREMIER_TOUR[a], "M"))
    df["rang"] = (df["mois"] - tour).map(lambda d: d.n)  # -6 … -1
    return df[df["rang"].between(-6, -1)]


def etiqueter(ax, fins, couleurs, ecart_min):
    """Place le nom au bout de chaque courbe sans chevauchement."""
    ordre = sorted(fins.items(), key=lambda kv: kv[1])
    positions, precedent = {}, None
    for nom, y in ordre:
        if precedent is not None and y - precedent < ecart_min:
            y = precedent + ecart_min
        positions[nom] = y
        precedent = y
    for nom, y in positions.items():
        ax.annotate(f"{nom} {fins[nom]:.1f}".replace(".", ","),
                    xy=(1.01, y), xycoords=("axes fraction", "data"),
                    va="center", fontsize=8.5, color=couleurs[nom])


def style(ax, ylabel):
    ax.set_ylabel(ylabel)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylim(bottom=0)


def par_election(df, mesure, annee):
    d = df[(df.type_mesure == mesure) & (df.annee_election == annee)]
    if d.empty:
        return None
    moyennes = d.groupby(["nom", "rang"])["valeur"].mean().unstack("rang")
    titre, ylabel = TITRES[mesure]
    fig, ax = plt.subplots(figsize=(11, 6.5))
    fins = {}
    for nom, serie in moyennes.iterrows():
        serie = serie.dropna()
        ax.plot(serie.index, serie.values, marker="o", markersize=4,
                linewidth=2, color=COULEURS.get(nom, "#555"))
        if not serie.empty:
            fins[nom] = serie.values[-1]
    style(ax, ylabel)
    tour = pd.Period(PREMIER_TOUR[annee], "M")
    rangs = list(range(-6, 0))
    ax.set_xticks(rangs)
    ax.set_xticklabels([f"{MOIS_COURTS[(tour + r).month - 1]} {(tour + r).year}" for r in rangs])
    ax.set_xlim(-6.2, -0.8)
    etiqueter(ax, fins, COULEURS, ecart_min=ax.get_ylim()[1] / 45)
    instituts = d["institut"].nunique()
    libelle = d["libelle_mesure"].dropna().iloc[0] if d["libelle_mesure"].notna().any() else ""
    ax.set_title(f"{titre} — présidentielle {annee}\n"
                 f"Moyenne mensuelle, {len(d)} valeurs, {instituts} institut(s). "
                 f"Mesure : {libelle}.", loc="left", fontsize=11)
    fig.subplots_adjust(right=0.82)
    chemin = SORTIE / f"{mesure}_{annee}_par_election.png"
    fig.savefig(chemin, dpi=150)
    plt.close(fig)
    return chemin


def superpose(df, mesure):
    d = df[df.type_mesure == mesure]
    if d.empty:
        return None
    moyennes = d.groupby(["annee_election", "nom", "qualifie_second_tour", "rang"])["valeur"].mean()
    titre, ylabel = TITRES[mesure]
    fig, ax = plt.subplots(figsize=(11, 6.5))
    fins = {}
    for (annee, nom, qualifie), serie in moyennes.groupby(level=[0, 1, 2]):
        serie = serie.droplevel([0, 1, 2])
        if qualifie:
            ax.plot(serie.index, serie.values, marker="o", markersize=4, linewidth=2.6,
                    color=COULEURS.get(nom, "#333"), zorder=3)
            fins[f"{nom} ({annee})"] = serie.values[-1]
        else:
            ax.plot(serie.index, serie.values, linewidth=1.2, color="#b5b5b5", zorder=2)
    style(ax, ylabel)
    ax.set_xticks(range(-6, 0))
    ax.set_xticklabels([f"M{r}" for r in range(-6, 0)])
    ax.set_xlabel("Mois avant le premier tour")
    ax.set_xlim(-6.2, -0.8)
    couleurs = {cle: COULEURS.get(cle.split(" (")[0], "#333") for cle in fins}
    etiqueter(ax, fins, couleurs, ecart_min=ax.get_ylim()[1] / 40)
    annees = sorted(d["annee_election"].unique())
    ax.set_title(f"{titre} — vision superposée ({', '.join(map(str, annees))})\n"
                 "En couleur : qualifiés au second tour. En gris : éliminés au premier tour.",
                 loc="left", fontsize=11)
    fig.subplots_adjust(right=0.82)
    chemin = SORTIE / f"{mesure}_superpose.png"
    fig.savefig(chemin, dpi=150)
    plt.close(fig)
    return chemin


def main():
    SORTIE.mkdir(exist_ok=True)
    df = charger()
    for mesure in TITRES:
        for annee in sorted(df["annee_election"].unique()):
            chemin = par_election(df, mesure, annee)
            if chemin:
                print(f"Graphique écrit : {chemin}")
        chemin = superpose(df, mesure)
        if chemin:
            print(f"Graphique écrit : {chemin}")


if __name__ == "__main__":
    main()
