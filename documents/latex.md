# MediFlow HDJ — Guide d'utilisation (source LaTeX)

**Nom du projet :** MediFlow HDJ  
**Sous-titre :** Assistant intelligent de simulation multi-agents pour l'hospitalisation de jour

Compile avec `pdflatex` (deux passes) ou collez le bloc ci-dessous dans Overleaf.

```latex
\documentclass[11pt,a4paper]{article}

\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[french]{babel}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{fancyhdr}

\geometry{margin=2.5cm}
\hypersetup{
  colorlinks=true,
  linkcolor=blue!60!black,
  urlcolor=teal!70!black
}

\definecolor{CHUPrimary}{HTML}{1976D2}
\definecolor{CHUAccent}{HTML}{26A69A}
\definecolor{CHUBg}{HTML}{FAFAFA}
\definecolor{CHUText}{HTML}{212121}
\definecolor{CHULight}{HTML}{ECEFF1}

\setlist[itemize,1]{
  label=\textcolor{CHUPrimary}{\Large\textbullet},
  leftmargin=1.4em,
  itemsep=5pt,
  parsep=2pt,
  topsep=6pt
}
\setlist[itemize,2]{
  label=\textcolor{CHUAccent}{\scriptsize\textbullet},
  leftmargin=1.6em,
  itemsep=3pt
}
\setlist[enumerate,1]{
  label=\textcolor{CHUPrimary}{\bfseries\arabic*.},
  leftmargin=1.6em,
  itemsep=5pt,
  topsep=6pt
}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\color{CHUText}MediFlow HDJ}
\fancyhead[R]{\small\color{CHUText}Guide d'utilisation}
\fancyfoot[C]{\small\color{CHUText}\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\begin{document}

\begin{titlepage}
\centering

\vspace*{2.5cm}

{\large\bfseries CHU DE GUYANE}\\[0.4em]
Défi 5 · Innovation organisationnelle\\[2.5cm]

{\Huge\bfseries MediFlow HDJ}\\[0.8em]
{\Large Assistant intelligent de simulation\\
multi-agents pour l'hospitalisation de jour}\\[2.5cm]

{\LARGE\bfseries Guide d'utilisation}\\[3cm]

Version MVP\\[0.6em]
{\large\bfseries 7 juin 2026}\\[0.5em]
Cayenne · Guyane française\\[2.5cm]

\small
Document destiné aux équipes médicales, organisationnelles et de direction.\\
Les analyses reposent exclusivement sur \textbf{vos saisies} ; aucune donnée fictive n'est injectée.

\vfill

\small
\textcopyright{} 2026 CHU de Guyane · Tous droits réservés

\end{titlepage}

\tableofcontents
\newpage

% ---------------------------------------------------------------------------
\section{Présentation du projet MediFlow HDJ}
% ---------------------------------------------------------------------------

\subsection{Objectif}

\textbf{MediFlow HDJ} est le nom du prototype développé dans le cadre du \textbf{Défi 5} du CHU de Guyane. L'application aide les équipes à arbitrer entre trois orientations organisationnelles pour les parcours ambulatoires :

\begin{itemize}
  \item conserver le \textbf{statu quo} ;
  \item \textbf{optimiser les HDJ existants} par regroupement et ordonnancement ;
  \item \textbf{créer un nouvel HDJ} dédié à une spécialité prioritaire.
\end{itemize}

Une simulation multi-agents rejoue vos hypothèses et produit une \textbf{décision conseillée} argumentée sur les délais, la conversion HDJ, la saturation des ressources et l'impact financier.

\subsection{Public visé}

\begin{itemize}
  \item Directions médicales et de l'organisation des soins ;
  \item Chefs de pôle et responsables de parcours ;
  \item Équipes projet HDJ, qualité et planification ;
  \item Membres de comité et arbitrage budget (synthèse étape 8).
\end{itemize}

\subsection{Prérequis techniques}

\begin{itemize}
  \item \textbf{Python} : version 3.10 ou supérieure ;
  \item \textbf{Navigateur} : Chrome, Firefox ou Edge (version récente) ;
  \item \textbf{Installation des dépendances} : \texttt{pip install -r requirements.txt} ;
  \item \textbf{Lancement} : \texttt{streamlit run app.py} ;
  \item \textbf{Accès local} : \url{http://localhost:8501}.
\end{itemize}

% ---------------------------------------------------------------------------
\section{Parcours utilisateur}
% ---------------------------------------------------------------------------

L'application ne comporte \textbf{pas de tableau de bord détaillé}. L'expérience est entièrement guidée par un assistant en \textbf{8 étapes}. Le flux global est le suivant :

\begin{enumerate}
  \item \textbf{Écran d'accueil animé} avec logo CHU et transition fluide ;
  \item \textbf{Page d'atterrissage} avec le bouton « Commencer l'analyse » ;
  \item \textbf{Analyse guidée} en huit étapes, puis retour à l'accueil.
\end{enumerate}

\subsection{Page d'atterrissage}

Après le splash, la page d'accueil propose :

\begin{itemize}
  \item \textbf{Commencer l'analyse} : lance l'assistant pas à pas ;
  \item \textbf{Démarrer la narration (60 s)} : disponible uniquement après une première analyse ; reprend les résultats de la dernière session sous forme de cartes explicatives.
\end{itemize}

Si une analyse précédente existe, des indicateurs synthétiques s'affichent :

\begin{itemize}
  \item gain d'attente estimé ;
  \item taux de conversion HDJ ;
  \item nombre de scénarios comparés.
\end{itemize}

\subsection{Mémorisation locale}

\begin{itemize}
  \item Vos saisies sont enregistrées automatiquement sur l'appareil ;
  \item Fichier local : \texttt{data/last\_inputs.json} (hors dépôt Git) ;
  \item Au prochain lancement, les champs du formulaire sont pré-remplis ;
  \item Les données restent sur votre poste : pour repartir de zéro, modifiez les champs ou supprimez \texttt{data/last\_inputs.json}.
\end{itemize}

% ---------------------------------------------------------------------------
\section{Les 8 étapes de l'analyse guidée}
% ---------------------------------------------------------------------------

Chaque étape affiche une barre de progression, le titre de l'étape et, à partir de l'étape 3, un encart « L'agent travaille… » pendant le calcul.

\textbf{Navigation :}

\begin{itemize}
  \item \textbf{Étape suivante} et \textbf{Étape précédente} pour avancer ou reculer ;
  \item \textbf{Recommencer} pour revenir au choix de spécialité ;
  \item \textbf{Modifier mes données} depuis l'étape 3 pour corriger le formulaire.
\end{itemize}

\subsection{Détail des étapes}

\begin{itemize}
  \item \textbf{Étape 1 · Choix de la spécialité}
  \begin{itemize}
    \item Cartes cliquables : Oncologie, Cardiologie, Diabétologie, Néphrologie, Douleur chronique ;
    \item Toute l'analyse porte sur le périmètre sélectionné.
  \end{itemize}

  \item \textbf{Étape 2 · Vos données}
  \begin{itemize}
    \item Formulaire : file active, fragmentation, éligibilité HDJ, délais, actes, tarifs, capacité HDJ ;
    \item Validation puis lancement de l'analyse étape par étape.
  \end{itemize}

  \item \textbf{Étape 3 · Cartographie des parcours}
  \begin{itemize}
    \item Métriques patients et taux de fragmentation ;
    \item Graphique par spécialité ;
    \item Expander « Comment ce taux est calculé ? » (fermé par défaut).
  \end{itemize}

  \item \textbf{Étape 4 · Création des agents}
  \begin{itemize}
    \item Agents patients, ressources, triage, ordonnanceur et évaluateur ;
    \item Description du rôle de chaque agent dans la simulation.
  \end{itemize}

  \item \textbf{Étape 5 · Triage organisationnel}
  \begin{itemize}
    \item Répartition fragmenté / HDJ existant / nouveau HDJ ;
    \item Diagramme Sankey du scénario recommandé.
  \end{itemize}

  \item \textbf{Étape 6 · Ordonnancement et capacité}
  \begin{itemize}
    \item Attente moyenne simulée ;
    \item Jauge de saturation avec seuil d'alerte à 85\,\%.
  \end{itemize}

  \item \textbf{Étape 7 · Évaluation médico-économique}
  \begin{itemize}
    \item Gain net, investissement structurel et conversion HDJ ;
    \item Graphique comparatif des trois scénarios.
  \end{itemize}

  \item \textbf{Étape 8 · Recommandation}
  \begin{itemize}
    \item Décision conseillée et justifications détaillées ;
    \item Proposition HDJ le cas échéant ;
    \item Bouton \textbf{Retour à l'accueil}.
  \end{itemize}
\end{itemize}

% ---------------------------------------------------------------------------
\section{Saisie des données (étape 2)}
% ---------------------------------------------------------------------------

\subsection{File active et parcours}

\begin{itemize}
  \item \textbf{Nombre de patients} (50 à 2000) : file active ambulatoire sur la période analysée ;
  \item \textbf{Parcours fragmentés (\%)} (1 à 100) : part des patients dont les actes sont dispersés ;
  \item \textbf{Patients convertibles en HDJ (\%)} (1 à 100) : sous-ensemble regroupable en hospitalisation de jour ;
  \item \textbf{Délai moyen d'attente} (1 à 120 jours) : délai actuel avant prise en charge complète ;
  \item \textbf{Nombre moyen d'actes par patient} (2 à 10) : complexité moyenne du parcours ;
  \item \textbf{Horizon d'analyse} : 14, 30 ou 60 jours ;
  \item \textbf{Durée d'un créneau} : 20, 30, 45 ou 60 minutes.
\end{itemize}

\subsection{Tarification}

\begin{itemize}
  \item \textbf{Tarif parcours fragmenté (€)} : obligatoire, strictement supérieur à 0 ;
  \item \textbf{Tarif parcours HDJ (€)} : obligatoire, strictement supérieur à 0 ;
  \item \textbf{Coût d'ouverture par créneau HDJ (€)} : investissement structurel en cas de création (0 à 10\,000 €).
\end{itemize}

\subsection{Capacité HDJ de l'établissement}

\begin{itemize}
  \item \textbf{Nombre d'unités HDJ} : de 1 à 6 ;
  \item \textbf{Places et lits HDJ (total)} : de 1 à 100 ;
  \item \textbf{Créneaux patients par jour (total)} : de 1 à 200 ;
  \item \textbf{Examens techniques par jour} : de 1 à 100.
\end{itemize}

\subsection{Règles de validation}

L'analyse ne démarre que si les conditions suivantes sont remplies :

\begin{enumerate}
  \item le taux de convertibles HDJ est inférieur ou égal au taux de parcours fragmentés ;
  \item les tarifs fragmenté et HDJ sont strictement positifs ;
  \item une spécialité a été choisie à l'étape 1.
\end{enumerate}

Cliquez sur \textbf{Lancer l'analyse étape par étape} pour valider le formulaire.

% ---------------------------------------------------------------------------
\section{Les trois scénarios simulés}
% ---------------------------------------------------------------------------

\begin{itemize}
  \item \textbf{Statu quo}
  \begin{itemize}
    \item Parcours fragmentés maintenus ;
    \item Coordination limitée entre les actes.
  \end{itemize}

  \item \textbf{Optimisation HDJ existants}
  \begin{itemize}
    \item Regroupement et ordonnancement améliorés ;
    \item Utilisation optimisée des unités déjà en place.
  \end{itemize}

  \item \textbf{Création nouveau HDJ}
  \begin{itemize}
    \item Ouverture d'une unité dédiée à la spécialité choisie ;
    \item Prise en compte du coût d'investissement structurel.
  \end{itemize}
\end{itemize}

Pour chaque scénario, le moteur calcule :

\begin{itemize}
  \item le délai moyen simulé ;
  \item le taux de conversion en parcours HDJ ;
  \item la saturation maximale des ressources (créneaux, salles, examens) ;
  \item les revenus estimatifs et le gain net par rapport au statu quo.
\end{itemize}

% ---------------------------------------------------------------------------
\section{Formules et recommandation}
% ---------------------------------------------------------------------------

\subsection{Taux de fragmentation}

\[
  \text{taux de fragmentation (\%)} = \frac{\text{nombre de patients fragmentés}}{\text{nombre total de patients}} \times 100
\]

\begin{itemize}
  \item Les effectifs sont dérivés \textbf{déterministiquement} de vos pourcentages saisis ;
  \item Aucun tirage aléatoire n'est appliqué.
\end{itemize}

\subsection{Gain net}

\[
  \text{gain net} = \text{revenus supplémentaires vs statu quo} - \text{investissement structurel}
\]

L'investissement ne s'applique qu'au scénario \emph{Création nouveau HDJ} :

\[
  \text{investissement} = \text{créneaux proposés/jour} \times \text{coût d'ouverture par créneau}
\]

\subsection{Logique de décision conseillée}

La recommandation retient le scénario au \textbf{meilleur gain net} positif :

\begin{enumerate}
  \item si optimisation et création ont un gain net inférieur ou égal à 0 : \textbf{Statu quo} ;
  \item si la création bat l'optimisation \emph{et} que le gain net est positif : \textbf{Création nouveau HDJ} ;
  \item sinon, si l'optimisation a un gain net positif : \textbf{Optimisation HDJ existants} ;
  \item sinon, si seule la création est positive : \textbf{Création nouveau HDJ}.
\end{enumerate}

\textbf{Règle complémentaire :}

\begin{itemize}
  \item si les HDJ existants sont saturés ($\geq 85\,\%$) ;
  \item et que la création est nettement plus rentable que l'optimisation ;
  \item alors la création d'un nouvel HDJ est favorisée.
\end{itemize}

\subsection{Seuil de saturation}

\begin{itemize}
  \item \textbf{Inférieur à 85\,\%} : capacité soutenable (message vert à l'étape 6) ;
  \item \textbf{Supérieur ou égal à 85\,\%} : vigilance, prévoir du lissage ou de la capacité supplémentaire.
\end{itemize}

% ---------------------------------------------------------------------------
\section{Interprétation des résultats}
% ---------------------------------------------------------------------------

\subsection{Étape 3 · Cartographie}

\begin{itemize}
  \item Comparez le volume total et le taux de fragmentation de votre spécialité ;
  \item Ouvrez l'expander \emph{Comment ce taux est calculé ?} pour la formule et les conseils contextuels :
  \begin{itemize}
    \item \textbf{60\,\% et plus} : fragmentation élevée, prioriser le regroupement ou une nouvelle unité ;
    \item \textbf{40 à 59\,\%} : optimiser d'abord l'existant, puis comparer avec une création ;
    \item \textbf{Moins de 40\,\%} : fragmentation modérée, l'optimisation des HDJ existants suffit souvent.
  \end{itemize}
\end{itemize}

\subsection{Étape 5 · Triage}

\begin{itemize}
  \item Le diagramme Sankey montre l'orientation des patients dans le scénario recommandé ;
  \item Trois flux possibles : parcours fragmenté, HDJ existant, nouveau HDJ.
\end{itemize}

\subsection{Étape 7 · Médico-économique}

Le graphique en barres compare le \textbf{gain net} des trois scénarios. Points clés à retenir :

\begin{itemize}
  \item le gain net du scénario recommandé ;
  \item l'investissement structurel (0 € si optimisation seule) ;
  \item le taux de conversion HDJ atteint.
\end{itemize}

\subsection{Étape 8 · Recommandation}

L'écran final affiche :

\begin{itemize}
  \item la \textbf{décision conseillée} (libellé en français) ;
  \item la spécialité étudiée ;
  \item une liste de \textbf{justifications} (gains, saturation, comparaison optimisation vs création) ;
  \item une fiche action en cas de création HDJ (créneaux par jour, investissement estimé).
\end{itemize}

% ---------------------------------------------------------------------------
\section{Exemple de profil « Création nouveau HDJ »}
% ---------------------------------------------------------------------------

Pour tester une recommandation orientée \textbf{Création nouveau HDJ}, saisissez par exemple :

\begin{itemize}
  \item \textbf{Spécialité} : Oncologie ;
  \item \textbf{Patients (file active)} : 150 ;
  \item \textbf{Parcours fragmentés} : 75\,\% ;
  \item \textbf{Convertibles en HDJ} : 70\,\% ;
  \item \textbf{Délai moyen} : 50 jours ;
  \item \textbf{Actes par patient} : 4 ;
  \item \textbf{Tarif fragmenté} : 80 € ;
  \item \textbf{Tarif HDJ} : 400 € ;
  \item \textbf{Coût d'ouverture par créneau} : 300 € ;
  \item \textbf{Unités HDJ} : 1 ;
  \item \textbf{Lits} : 2 ;
  \item \textbf{Créneaux par jour} : 3 ;
  \item \textbf{Examens par jour} : 2 ;
  \item \textbf{Horizon d'analyse} : 30 jours.
\end{itemize}

Ce profil combine forte fragmentation, file importante, capacité HDJ serrée et écart tarifaire favorable au regroupement. Les gains nets typiques placent la création au-dessus de l'optimisation.

% ---------------------------------------------------------------------------
\section{Navigation et raccourcis}
% ---------------------------------------------------------------------------

\begin{itemize}
  \item \textbf{Étape suivante / Étape précédente} : avance ou recule dans l'assistant sans perdre les saisies ;
  \item \textbf{Modifier mes données} (depuis l'étape 3) : retour au formulaire de l'étape 2 ;
  \item \textbf{Recommencer} : retour au choix de spécialité (étape 1) ;
  \item \textbf{Retour à l'accueil} (étape 8) : sauvegarde les saisies et affiche la page d'atterrissage ;
  \item \textbf{Changer de spécialité} (étape 2) : retour à la sélection des cartes spécialité.
\end{itemize}

% ---------------------------------------------------------------------------
\section{Dépannage}
% ---------------------------------------------------------------------------

\begin{itemize}
  \item \textbf{Erreur de validation à l'étape 2}
  \begin{itemize}
    \item Vérifiez que les convertibles HDJ ne dépassent pas les parcours fragmentés ;
    \item Vérifiez que les tarifs sont strictement supérieurs à 0 €.
  \end{itemize}

  \item \textbf{Résultat inattendu après modification}
  \begin{itemize}
    \item Rafraîchissez la page (F5) ;
    \item L'application recalcule automatiquement à chaque étape à partir de la 3.
  \end{itemize}

  \item \textbf{Import ou module obsolète}
  \begin{itemize}
    \item Arrêtez Streamlit avec \texttt{Ctrl+C} ;
    \item Relancez avec \texttt{streamlit run app.py}.
  \end{itemize}

  \item \textbf{Saisies anciennes}
  \begin{itemize}
    \item Supprimez \texttt{data/last\_inputs.json} ;
    \item Ou modifiez les champs puis relancez l'analyse.
  \end{itemize}
\end{itemize}

% ---------------------------------------------------------------------------
\section{Limites du MVP et évolutions}
% ---------------------------------------------------------------------------

\begin{itemize}
  \item Données \textbf{saisies manuellement} : branchement PMSI, CCAM et SIH non implémenté dans ce MVP ;
  \item Une seule spécialité analysée à la fois (celle choisie à l'étape 1) ;
  \item Simulation déterministe : les pourcentages saisis sont répartis de façon fixe sur la file active ;
  \item Pas de tableau de bord avancé : toute la restitution passe par les 8 étapes guidées ;
  \item Seuil de regroupement HDJ (\texttt{grouping\_rate}, défaut 0{,}35) : paramètre interne, non exposé dans le formulaire.
\end{itemize}

% ---------------------------------------------------------------------------
\section{Références}
% ---------------------------------------------------------------------------

\begin{itemize}
  \item Santibañez et al. (2009) : simulation des parcours ambulatoires ;
  \item Li et al. (2024) : Agent Hospital ;
  \item Sujet HDJ Agent : EL-BAHRI / CARTIER, CHU de Guyane ;
  \item Dépôt GitHub : \url{https://github.com/Ismailbak/HospitalFlow}.
\end{itemize}

\vfill
\begin{center}
  \small\color{CHUText!80}
  \textcopyright{} 2026 CHU de Guyane · Tous droits réservés\\[0.3em]
  \textbf{MediFlow HDJ} · Guide d'utilisation · 7 juin 2026
\end{center}

\end{document}
```

## Compilation locale

```bash
# Extraire le bloc LaTeX dans guide_mediflow_hdj.tex puis :
pdflatex guide_mediflow_hdj.tex
pdflatex guide_mediflow_hdj.tex
```

## Résumé des changements

- **Nom du projet :** MediFlow HDJ
- **Page de garde simple** : texte centré, sans bandeaux ni encadrés (date : 7 juin 2026)
- **Listes à puces colorées** partout (tableaux et tirets « — » supprimés du corps du document)
