# Portrait des candidats qualifiés au second tour

Ce projet cherche à décrire le profil des candidates et des candidats qui passent le premier tour de l'élection présidentielle sous la Ve République.

Le premier essai porte sur l'élection de 2022. Il mesure deux indicateurs pendant les six mois qui précèdent le premier tour du 10 avril 2022 :

- les intentions de vote au premier tour ;
- la cote de popularité.

## Structure de la base

La base `data/presidentielle.sqlite` contient deux tables.

La table `candidat` décrit chaque candidature :

| Colonne | Contenu |
| --- | --- |
| `id` | Identifiant |
| `prenom` | Prénom |
| `nom` | Nom |
| `annee_election` | Année de l'élection |
| `qualifie_second_tour` | 1 si la personne est qualifiée au second tour, 0 sinon |

La table `cote_popularite` stocke chaque mesure publiée :

| Colonne | Contenu |
| --- | --- |
| `candidat_id` | Lien vers la table `candidat` |
| `date` | Dernier jour de terrain du sondage |
| `valeur` | Valeur en pourcentage |
| `type_mesure` | `intention_de_vote` ou `popularite` |
| `libelle_mesure` | Question posée (par exemple « bonne opinion ») |
| `institut` | Institut de sondage |
| `url_source` | Lien vers la notice du sondage |

## Sources

Les intentions de vote viennent de la page Wikipédia « Liste de sondages sur l'élection présidentielle française de 2022 ». Chaque valeur renvoie à la notice déposée par l'institut auprès de la Commission des sondages.

Les cotes de popularité viennent du « Tableau de bord des personnalités » publié chaque mois par Ifop-Fiducial pour Paris Match et Sud Radio. La question mesure la part de « bonne opinion ». Le fichier `data/popularite_2022.csv` donne le lien vers le document source de chaque valeur.

Ce baromètre a des limites :

- Ifop ne teste Éric Zemmour qu'à partir de décembre 2021.
- Ifop ne teste jamais Philippe Poutou. Ses valeurs viennent de l'Observatoire politique d'Elabe pour Les Echos et Radio Classique (« image positive »), de janvier à mars 2022. Les deux questions diffèrent : comparez ces valeurs avec prudence.
- Aucun baromètre consulté ne teste Nathalie Arthaud ni Jean Lassalle.
- Le terrain de chaque vague Ifop a lieu au début du mois. Les cinq dernières semaines avant le premier tour ne sont donc pas couvertes.

## Règles de calcul

- La période couvre six mois civils : d'octobre 2021 à mars 2022.
- Chaque point du graphique est la moyenne des valeurs publiées dans le mois.
- En octobre et en novembre 2021, Les Républicains n'ont pas encore désigné leur candidate. Le script garde seulement les hypothèses où Valérie Pécresse représente LR.
- Une valeur « inférieure à 0,5 % » vaut 0,25 %. Une valeur « inférieure à 1 % » vaut 0,5 %.
- Les sondages quotidiens (« rolling ») comptent comme les autres. Ils pèsent donc davantage en mars 2022.

## Reproduire les résultats

```bash
pip install pandas lxml beautifulsoup4 matplotlib
python scripts/intentions_de_vote.py     # télécharge et extrait les sondages
python scripts/construire_base.py        # crée la base SQLite
python scripts/graphiques.py             # trace les graphiques
```

## Graphiques

Le dossier `graphiques/` propose deux visions pour chaque mesure :

- `*_2022_par_election.png` : une courbe par candidat, d'octobre 2021 à mars 2022 ;
- `*_superpose.png` : abscisse relative (M-6 à M-1). Les qualifiés au second tour sont en couleur, les autres en gris. Cette vision servira à comparer les élections entre elles.
