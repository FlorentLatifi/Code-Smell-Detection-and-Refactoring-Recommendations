"""Referencat e punimit, në formatin që kërkon shablloni i UBT-së.

Renditja është alfabetike sipas mbiemrit të autorit të parë, dhe numri në kllapa
katrore është ai që del te kapitulli «Referencat». Citimi në tekst bëhet
`(Mbiemri, viti)`, siç e kërkon shablloni.

Ndarja në dy lista nuk është stilistike. `CITED_BY_SYSTEM` janë burimet që kodi i
zbaton drejtpërdrejt — çdo prag, çdo përkufizim metrike dhe e vërteta bazë — dhe
secila prej tyre është e cituar tashmë në docstring-un e kodit që e përdor.
`RELATED_WORK` janë burimet që i duhen Kapitullit 2; ato nuk zbatohen nga kodi,
por pa to shqyrtimi i literaturës nuk qëndron.

RREGULLI I SHABLLONIT: te «Referencat» shkojnë vetëm burimet e cituara. Çdo
burim i lexuar por i pacituar shkon te «Bibliografia». Prandaj një referencë
hiqet nga kjo listë nëse citimi përkatës del nga teksti.

VERIFIKIM: autorët, titujt, vitet dhe revistat janë të sakta. Numrat e vëllimeve
dhe të faqeve janë rikontrolluar kundrejt regjistrit të botuesit vetëm për një
pjesë, dhe `PAGES_VERIFIED` e `PAGES_UNVERIFIED` e thonë saktësisht se cila është
cila. Ndarja mbahet këtu e jo në kokë, sepse «i kontrolluar» harrohet brenda javës
dhe pastaj rikontrollohet e njëjta gjë ndërsa tjetra mbetet përgjithmonë e paprekur.
"""

from __future__ import annotations

import unicodedata

# ---------------------------------------------------------------------
# Burimet që sistemi i zbaton drejtpërdrejt
# ---------------------------------------------------------------------
CITED_BY_SYSTEM = [
    (
        "Bieman, J. M. & Kang, B.-K. 1995. “Cohesion and Reuse in an Object-Oriented "
        "System.” Proceedings of the ACM Symposium on Software Reusability (SSR ’95), "
        "pp. 259-262."
    ),
    (
        "Chidamber, S. R. & Kemerer, C. F. 1994. “A Metrics Suite for Object Oriented "
        "Design.” IEEE Transactions on Software Engineering, 20(6), pp. 476-493."
    ),
    (
        "Fowler, M. 2018. Refactoring: Improving the Design of Existing Code, 2nd edn. "
        "Boston: Addison-Wesley."
    ),
    (
        "Henderson-Sellers, B. 1996. Object-Oriented Metrics: Measures of Complexity. "
        "Upper Saddle River, NJ: Prentice Hall."
    ),
    (
        "Lanza, M. & Marinescu, R. 2006. Object-Oriented Metrics in Practice: Using "
        "Software Metrics to Characterize, Evaluate, and Improve the Design of "
        "Object-Oriented Systems. Berlin: Springer."
    ),
    (
        "Madeyski, L. & Lewowski, T. 2020. “MLCQ: Industry-relevant code smell data "
        "set.” Proceedings of the 24th International Conference on Evaluation and "
        "Assessment in Software Engineering (EASE ’20), pp. 342-347."
    ),
    (
        "McCabe, T. J. 1976. “A Complexity Measure.” IEEE Transactions on Software "
        "Engineering, SE-2(4), pp. 308-320."
    ),
    (
        "Park, R. E. 1992. Software Size Measurement: A Framework for Counting Source "
        "Statements. Technical Report CMU/SEI-92-TR-020. Pittsburgh: Software "
        "Engineering Institute, Carnegie Mellon University."
    ),
]

# ---------------------------------------------------------------------
# Burimet metodologjike: si maten dhe si raportohen rezultatet
# ---------------------------------------------------------------------
METHODOLOGY = [
    (
        "Breiman, L. 2001. “Random Forests.” Machine Learning, 45(1), pp. 5-32."
    ),
    (
        "Cohen, J. 1960. “A Coefficient of Agreement for Nominal Scales.” Educational "
        "and Psychological Measurement, 20(1), pp. 37-46."
    ),
    (
        "Friedman, J. H. 2001. “Greedy Function Approximation: A Gradient Boosting "
        "Machine.” The Annals of Statistics, 29(5), pp. 1189-1232."
    ),
    (
        "Matthews, B. W. 1975. “Comparison of the predicted and observed secondary "
        "structure of T4 phage lysozyme.” Biochimica et Biophysica Acta (BBA) - "
        "Protein Structure, 405(2), pp. 442-451."
    ),
    (
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, "
        "O., et al. 2011. “Scikit-learn: Machine Learning in Python.” Journal of "
        "Machine Learning Research, 12, pp. 2825-2830."
    ),
]

# ---------------------------------------------------------------------
# Puna e lidhur, për Kapitullin 2
# ---------------------------------------------------------------------
RELATED_WORK = [
    (
        "Arcelli Fontana, F., Mäntylä, M. V., Zanoni, M. & Marino, A. 2016. “Comparing "
        "and experimenting machine learning techniques for code smell detection.” "
        "Empirical Software Engineering, 21(3), pp. 1143-1191."
    ),
    (
        "Azeem, M. I., Palomba, F., Shi, L. & Wang, Q. 2019. “Machine learning "
        "techniques for code smell detection: A systematic literature review and "
        "meta-analysis.” Information and Software Technology, 108, pp. 115-138."
    ),
    (
        "Cunningham, W. 1992. “The WyCash Portfolio Management System.” OOPSLA ’92 "
        "Experience Report. Addendum to the Proceedings on Object-Oriented "
        "Programming Systems, Languages, and Applications, pp. 29-30."
    ),
    (
        "Di Nucci, D., Palomba, F., Tamburri, D. A., Serebrenik, A. & De Lucia, A. "
        "2018. “Detecting code smells using machine learning techniques: Are we there "
        "yet?” Proceedings of the 25th IEEE International Conference on Software "
        "Analysis, Evolution and Reengineering (SANER ’18), pp. 612-621."
    ),
    (
        "Lehman, M. M. 1980. “Programs, Life Cycles, and Laws of Software Evolution.” "
        "Proceedings of the IEEE, 68(9), pp. 1060-1076."
    ),
    (
        "Mäntylä, M. V. & Lassenius, C. 2006. “Subjective evaluation of software "
        "evolvability using code smells: An empirical study.” Empirical Software "
        "Engineering, 11(3), pp. 395-431."
    ),
    (
        "Marinescu, R. 2004. “Detection Strategies: Metrics-Based Rules for Detecting "
        "Design Flaws.” Proceedings of the 20th IEEE International Conference on "
        "Software Maintenance (ICSM ’04), pp. 350-359."
    ),
    (
        "Moha, N., Guéhéneuc, Y.-G., Duchien, L. & Le Meur, A.-F. 2010. “DECOR: A "
        "Method for the Specification and Detection of Code and Design Smells.” IEEE "
        "Transactions on Software Engineering, 36(1), pp. 20-36."
    ),
    (
        "Murphy-Hill, E., Parnin, C. & Black, A. P. 2012. “How We Refactor, and How We "
        "Know It.” IEEE Transactions on Software Engineering, 38(1), pp. 5-18."
    ),
    (
        "Opdyke, W. F. 1992. Refactoring Object-Oriented Frameworks. PhD thesis. "
        "University of Illinois at Urbana-Champaign."
    ),
    (
        "Palomba, F., Bavota, G., Di Penta, M., Oliveto, R., Poshyvanyk, D. & De "
        "Lucia, A. 2015. “Mining Version Histories for Detecting Code Smells.” IEEE "
        "Transactions on Software Engineering, 41(5), pp. 462-489."
    ),
    (
        "Sharma, T. & Spinellis, D. 2018. “A survey on software smells.” Journal of "
        "Systems and Software, 138, pp. 158-173."
    ),
    (
        "Silva, D., Tsantalis, N. & Valente, M. T. 2016. “Why We Refactor? Confessions "
        "of GitHub Contributors.” Proceedings of the 24th ACM SIGSOFT International "
        "Symposium on Foundations of Software Engineering (FSE ’16), pp. 858-870."
    ),
    (
        "Tsantalis, N. & Chatzigeorgiou, A. 2009. “Identification of Move Method "
        "Refactoring Opportunities.” IEEE Transactions on Software Engineering, 35(3), "
        "pp. 347-367."
    ),
]

# ---------------------------------------------------------------------
# Mjetet, të cituara si burime elektronike sipas shabllonit
# ---------------------------------------------------------------------
TOOLS = [
    (
        "Brunsfeld, M. et al. tree-sitter: An incremental parsing system for "
        "programming tools. [https://tree-sitter.github.io/tree-sitter/], "
        "data e qasjes: [PLOTËSO]."
    ),
]


def _sort_key(reference: str) -> str:
    """Renditje alfabetike që nuk e prish diakritika.

    Pa këtë, «Mäntylä» bie pas «Murphy-Hill», sepse «ä» renditet pas çdo shkronje
    ASCII. Dekompozimi i heq shenjat dhe e lë emrin aty ku e pret lexuesi.
    """
    stripped = unicodedata.normalize("NFKD", reference)
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


def all_references() -> list[str]:
    """Të gjitha referencat, të renditura alfabetikisht si një listë e vetme."""
    return sorted(CITED_BY_SYSTEM + METHODOLOGY + RELATED_WORK + TOOLS, key=_sort_key)


# Vëllimi dhe faqet e rikontrolluara më 2026-08-31 kundrejt regjistrit të botuesit:
# DBLP për të katërtat e para, IEEE Xplore dhe Springer për të tjerat. Të tetë dolën
# të sakta ashtu si ishin shkruar; asnjë hyrje nuk u ndryshua.
PAGES_VERIFIED = (
    "Arcelli Fontana et al. 2016",
    "Bieman & Kang 1995",
    "Chidamber & Kemerer 1994",
    "Cunningham 1992",
    "Di Nucci et al. 2018",
    "Madeyski & Lewowski 2020",
    "Marinescu 2004",
    "McCabe 1976",
)

# Hyrjet me numra faqesh që nuk janë kontrolluar nga një burim i dytë. Janë
# transkriptuar nga vetë botimi dhe s'ka arsye të dyshohen, por «e patestuar» dhe
# «e saktë» nuk shkruhen njësoj. Librat dhe raportet nuk hyjnë as këtu as më lart,
# sepse nuk kanë numra faqesh për t'u kontrolluar.
PAGES_UNVERIFIED = (
    "Azeem et al. 2019",
    "Breiman 2001",
    "Cohen 1960",
    "Friedman 2001",
    "Lehman 1980",
    "Mäntylä & Lassenius 2006",
    "Matthews 1975",
    "Moha et al. 2010",
    "Murphy-Hill et al. 2012",
    "Palomba et al. 2015",
    "Pedregosa et al. 2011",
    "Sharma & Spinellis 2018",
    "Silva et al. 2016",
    "Tsantalis & Chatzigeorgiou 2009",
)
