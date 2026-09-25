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
        "Brown, L. D., Cai, T. T. & DasGupta, A. 2001. “Interval Estimation for a "
        "Binomial Proportion.” Statistical Science, 16(2), pp. 101-133."
    ),
    (
        "Chicco, D. & Jurman, G. 2020. “The advantages of the Matthews correlation "
        "coefficient (MCC) over F1 score and accuracy in binary classification "
        "evaluation.” BMC Genomics, 21, 6."
    ),
    (
        "Cohen, J. 1960. “A Coefficient of Agreement for Nominal Scales.” Educational "
        "and Psychological Measurement, 20(1), pp. 37-46."
    ),
    (
        "Efron, B. & Tibshirani, R. J. 1993. An Introduction to the Bootstrap. New "
        "York: Chapman & Hall."
    ),
    (
        "Friedman, J. H. 2001. “Greedy Function Approximation: A Gradient Boosting "
        "Machine.” The Annals of Statistics, 29(5), pp. 1189-1232."
    ),
    (
        "Kaufman, S., Rosset, S., Perlich, C. & Stitelman, O. 2012. “Leakage in Data "
        "Mining: Formulation, Detection, and Avoidance.” ACM Transactions on Knowledge "
        "Discovery from Data, 6(4), 15."
    ),
    (
        "Matthews, B. W. 1975. “Comparison of the predicted and observed secondary "
        "structure of T4 phage lysozyme.” Biochimica et Biophysica Acta (BBA) - "
        "Protein Structure, 405(2), pp. 442-451."
    ),
    (
        "PMD Team, 2026. PMD: An Extensible Cross-Language Static Code Analyzer, "
        "versioni 7.27.0. [https://pmd.github.io/], data e qasjes: 08.09.2026."
    ),
    (
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, "
        "O., et al. 2011. “Scikit-learn: Machine Learning in Python.” Journal of "
        "Machine Learning Research, 12, pp. 2825-2830."
    ),
    (
        "Strobl, C., Boulesteix, A.-L., Zeileis, A. & Hothorn, T. 2007. “Bias in random "
        "forest variable importance measures: Illustrations, sources and a solution.” "
        "BMC Bioinformatics, 8, 25."
    ),
    (
        "Wilson, E. B. 1927. “Probable Inference, the Law of Succession, and "
        "Statistical Inference.” Journal of the American Statistical Association, "
        "22(158), pp. 209-212."
    ),
    (
        "Wohlin, C., Runeson, P., Höst, M., Ohlsson, M. C., Regnell, B. & Wesslén, A. "
        "2012. Experimentation in Software Engineering. Berlin: Springer."
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
        "Bavota, G., De Lucia, A., Di Penta, M., Oliveto, R. & Palomba, F. 2015. “An "
        "experimental investigation on the innate relationship between quality and "
        "refactoring.” Journal of Systems and Software, 107, pp. 1-14."
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
        "Khomh, F., Di Penta, M., Guéhéneuc, Y.-G. & Antoniol, G. 2012. “An "
        "exploratory study of the impact of antipatterns on class change- and "
        "fault-proneness.” Empirical Software Engineering, 17(3), pp. 243-275."
    ),
    (
        "Lehman, M. M. 1980. “Programs, Life Cycles, and Laws of Software Evolution.” "
        "Proceedings of the IEEE, 68(9), pp. 1060-1076."
    ),
    (
        "Madeyski, L. & Lewowski, T. 2023. “Detecting code smells using "
        "industry-relevant data.” Information and Software Technology, 155, 107112."
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
        "Mens, T. & Tourwé, T. 2004. “A Survey of Software Refactoring.” IEEE "
        "Transactions on Software Engineering, 30(2), pp. 126-139."
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
        "Palomba, F., Bavota, G., Di Penta, M., Fasano, F., Oliveto, R. & De Lucia, A. "
        "2018. “On the diffuseness and the impact on maintainability of code smells: a "
        "large scale empirical investigation.” Empirical Software Engineering, 23, "
        "pp. 1188-1221."
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
        "Sjøberg, D. I. K., Yamashita, A., Anda, B. C. D., Mockus, A. & Dybå, T. 2013. "
        "“Quantifying the Effect of Code Smells on Maintenance Effort.” IEEE "
        "Transactions on Software Engineering, 39(8), pp. 1144-1156."
    ),
    (
        "Tsantalis, N. & Chatzigeorgiou, A. 2009. “Identification of Move Method "
        "Refactoring Opportunities.” IEEE Transactions on Software Engineering, 35(3), "
        "pp. 347-367."
    ),
    (
        "Tufano, M., Palomba, F., Bavota, G., Oliveto, R., Di Penta, M., De Lucia, A. & "
        "Poshyvanyk, D. 2015. “When and Why Your Code Starts to Smell Bad.” Proceedings "
        "of the 37th IEEE/ACM International Conference on Software Engineering (ICSE "
        "’15), pp. 403-414."
    ),
    (
        "Yamashita, A. & Moonen, L. 2013. “Do developers care about code smells? An "
        "exploratory survey.” Proceedings of the 20th Working Conference on Reverse "
        "Engineering (WCRE ’13), pp. 242-251."
    ),
]

# ---------------------------------------------------------------------
# Mjetet, të cituara si burime elektronike sipas shabllonit
# ---------------------------------------------------------------------
TOOLS = [
    (
        "Brunsfeld, M. et al. tree-sitter: An incremental parsing system for "
        "programming tools. [https://tree-sitter.github.io/tree-sitter/], "
        "data e qasjes: 30.08.2026."
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
#
# Më 2026-09-17 të gjitha referencat u kontrolluan se ekzistojnë. Për çdo hyrje me
# DOI, Crossref ktheu të njëjtin titull, autorë, vëllim dhe faqe; Madeyski &
# Lewowski 2023 u shtua me DOI 10.1016/j.infsof.2022.107112, dhe numri i artikullit
# 107112 është ai i botuesit. Librat, teza e Opdyke-s dhe dy mjetet u konfirmuan te
# botuesi, universiteti ose faqja e projektit (VD-125).
#
# Më 2026-09-25, me kërkesë të mentores («kontrollo referencat a ekzistojnë»), çdo
# hyrje u rikontrollua një nga një te faqja e botuesit ose te një indeks akademik
# (IEEE Xplore, ACM DL, Springer, ScienceDirect, Project Euclid, JSTOR, DBLP), dhe
# autorët, viti, titulli, vëllimi dhe faqet dolën si janë shkruar. Me këtë, hyrjet
# që ishin «të transkriptuara por jo të rikontrolluara» kaluan te lista e
# verifikuar. Dymbëdhjetë burimet e shtuara atë ditë (VD-136) u shtuan vetëm pasi
# kaloi i njëjti kontroll, dhe për Palomba et al. 2018 numri i fashikullit mungon me
# qëllim, sepse burimi e jep vetëm vëllimin dhe faqet.
PAGES_VERIFIED = (
    "Arcelli Fontana et al. 2016",
    "Azeem et al. 2019",
    "Bavota et al. 2015",
    "Bieman & Kang 1995",
    "Breiman 2001",
    "Brown et al. 2001",
    "Chidamber & Kemerer 1994",
    "Cohen 1960",
    "Cunningham 1992",
    "Di Nucci et al. 2018",
    "Friedman 2001",
    "Khomh et al. 2012",
    "Lehman 1980",
    "Madeyski & Lewowski 2020",
    "Madeyski & Lewowski 2023",
    "Mäntylä & Lassenius 2006",
    "Marinescu 2004",
    "Matthews 1975",
    "McCabe 1976",
    "Mens & Tourwé 2004",
    "Moha et al. 2010",
    "Murphy-Hill et al. 2012",
    "Palomba et al. 2015",
    "Palomba et al. 2018",
    "Pedregosa et al. 2011",
    "Sharma & Spinellis 2018",
    "Silva et al. 2016",
    "Sjøberg et al. 2013",
    "Tsantalis & Chatzigeorgiou 2009",
    "Tufano et al. 2015",
    "Wilson 1927",
    "Yamashita & Moonen 2013",
)

# Hyrjet me numra faqesh që nuk janë kontrolluar nga një burim i dytë. Pas
# kontrollit të 2026-09-25 nuk mbetet asnjë; lista mbahet që një hyrje e re me faqe
# të ketë vend ku të shkojë derisa të kontrollohet, në vend që të kalojë heshtazi
# si e verifikuar.
PAGES_UNVERIFIED: tuple[str, ...] = ()
