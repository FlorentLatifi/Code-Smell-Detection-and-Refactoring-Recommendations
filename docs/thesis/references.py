"""Referencat e punimit, në stilin APA (botimi i 7-të).

Mentorja kërkoi më 15 tetor 2026 që referencat dhe citimet të harmonizohen sipas
një stili të vetëm, APA. Lista nuk numërohet më: renditet alfabetikisht sipas
mbiemrit të autorit të parë, me dhëmbëzim të varur, dhe citimi në tekst është
«(Mbiemri, viti)» ose «Mbiemri (viti)». Elementet bibliografike që nuk janë pjesë e
titullit shkruhen shqip, si numri i faqes te teksti («f. 80»): «Në», «f.», «bot.»,
«Artikulli», «[Softuer]». Titujt mbeten në gjuhën e burimit.

Pjesët me `*...*` shtypen me shkronja të pjerrëta: titulli i librit, emri i revistës
me vëllimin, dhe emri i përmbledhjes së konferencës. `build_references` e lexon këtë
shenjë; teksti i kapitujve nuk e përdor.

Ndarja në lista nuk është stilistike. `CITED_BY_SYSTEM` janë burimet që kodi i
zbaton drejtpërdrejt — çdo prag, çdo përkufizim metrike dhe e vërteta bazë — dhe
secila prej tyre është e cituar tashmë në docstring-un e kodit që e përdor.
`RELATED_WORK` janë burimet që i duhen Kapitullit 2; ato nuk zbatohen nga kodi,
por pa to shqyrtimi i literaturës nuk qëndron.

RREGULLI I SHABLLONIT: te «Referencat» shkojnë vetëm burimet e cituara. Çdo
burim i lexuar por i pacituar shkon te «Bibliografia». Prandaj një referencë
hiqet nga kjo listë nëse citimi përkatës del nga teksti.

VERIFIKIM: shih shënimet mbi `PAGES_VERIFIED` në fund të skedarit.
"""

from __future__ import annotations

import unicodedata

# ---------------------------------------------------------------------
# Burimet që sistemi i zbaton drejtpërdrejt
# ---------------------------------------------------------------------
CITED_BY_SYSTEM = [
    (
        "Bieman, J. M., & Kang, B.-K. (1995). Cohesion and reuse in an object-oriented "
        "system. Në *Proceedings of the 1995 Symposium on Software Reusability (SSR ’95)* "
        "(f. 259–262). ACM. https://doi.org/10.1145/211782.211856"
    ),
    (
        "Chidamber, S. R., & Kemerer, C. F. (1994). A metrics suite for object oriented "
        "design. *IEEE Transactions on Software Engineering, 20*(6), 476–493. "
        "https://doi.org/10.1109/32.295895"
    ),
    (
        "Fowler, M. (2018). *Refactoring: Improving the design of existing code* (bot. i "
        "2-të). Addison-Wesley."
    ),
    (
        "Henderson-Sellers, B. (1996). *Object-oriented metrics: Measures of complexity*. "
        "Prentice Hall."
    ),
    (
        "Lanza, M., & Marinescu, R. (2006). *Object-oriented metrics in practice: Using "
        "software metrics to characterize, evaluate, and improve the design of "
        "object-oriented systems*. Springer. https://doi.org/10.1007/3-540-39538-5"
    ),
    (
        "Madeyski, L., & Lewowski, T. (2020). MLCQ: Industry-relevant code smell data set. "
        "Në *Proceedings of the 24th International Conference on Evaluation and Assessment "
        "in Software Engineering (EASE ’20)* (f. 342–347). ACM. "
        "https://doi.org/10.1145/3383219.3383264"
    ),
    (
        "McCabe, T. J. (1976). A complexity measure. *IEEE Transactions on Software "
        "Engineering, SE-2*(4), 308–320. https://doi.org/10.1109/TSE.1976.233837"
    ),
    (
        "Park, R. E. (1992). *Software size measurement: A framework for counting source "
        "statements* (Raport teknik CMU/SEI-92-TR-020). Software Engineering Institute, "
        "Carnegie Mellon University."
    ),
]

# ---------------------------------------------------------------------
# Burimet metodologjike: si maten dhe si raportohen rezultatet
# ---------------------------------------------------------------------
METHODOLOGY = [
    (
        "Breiman, L. (2001). Random forests. *Machine Learning, 45*(1), 5–32. "
        "https://doi.org/10.1023/A:1010933404324"
    ),
    (
        "Brown, L. D., Cai, T. T., & DasGupta, A. (2001). Interval estimation for a "
        "binomial proportion. *Statistical Science, 16*(2), 101–133. "
        "https://doi.org/10.1214/ss/1009213286"
    ),
    # Shtuar më 15 tetor 2026 për kufizimin që kërkoi mentorja: zgjedhja e modelit më
    # të mirë mbi të njëjtat parashikime mbi të cilat raportohet shifra.
    (
        "Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and "
        "subsequent selection bias in performance evaluation. *Journal of Machine Learning "
        "Research, 11*(70), 2079–2107. https://www.jmlr.org/papers/v11/cawley10a.html"
    ),
    (
        "Chicco, D., & Jurman, G. (2020). The advantages of the Matthews correlation "
        "coefficient (MCC) over F1 score and accuracy in binary classification "
        "evaluation. *BMC Genomics, 21*(1), Artikulli 6. "
        "https://doi.org/10.1186/s12864-019-6413-7"
    ),
    (
        "Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational "
        "and Psychological Measurement, 20*(1), 37–46. "
        "https://doi.org/10.1177/001316446002000104"
    ),
    (
        "Efron, B., & Tibshirani, R. J. (1993). *An introduction to the bootstrap*. "
        "Chapman & Hall."
    ),
    (
        "Friedman, J. H. (2001). Greedy function approximation: A gradient boosting "
        "machine. *The Annals of Statistics, 29*(5), 1189–1232. "
        "https://doi.org/10.1214/aos/1013203451"
    ),
    (
        "Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data "
        "mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge "
        "Discovery from Data, 6*(4), Artikulli 15. https://doi.org/10.1145/2382577.2382579"
    ),
    (
        "Matthews, B. W. (1975). Comparison of the predicted and observed secondary "
        "structure of T4 phage lysozyme. *Biochimica et Biophysica Acta (BBA) – Protein "
        "Structure, 405*(2), 442–451. https://doi.org/10.1016/0005-2795(75)90109-9"
    ),
    (
        "PMD Team. (2026). *PMD: An extensible cross-language static code analyzer* "
        "(Versioni 7.27.0) [Softuer]. https://pmd.github.io/"
    ),
    (
        "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., "
        "Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, "
        "A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011). "
        "Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, "
        "12*(85), 2825–2830. https://jmlr.org/papers/v12/pedregosa11a.html"
    ),
    (
        "Strobl, C., Boulesteix, A.-L., Zeileis, A., & Hothorn, T. (2007). Bias in random "
        "forest variable importance measures: Illustrations, sources and a solution. "
        "*BMC Bioinformatics, 8*(1), Artikulli 25. https://doi.org/10.1186/1471-2105-8-25"
    ),
    (
        "Wilson, E. B. (1927). Probable inference, the law of succession, and statistical "
        "inference. *Journal of the American Statistical Association, 22*(158), 209–212. "
        "https://doi.org/10.1080/01621459.1927.10502953"
    ),
    (
        "Wohlin, C., Runeson, P., Höst, M., Ohlsson, M. C., Regnell, B., & Wesslén, A. "
        "(2012). *Experimentation in software engineering*. Springer. "
        "https://doi.org/10.1007/978-3-642-29044-2"
    ),
]

# ---------------------------------------------------------------------
# Puna e lidhur, për Kapitullin 2
# ---------------------------------------------------------------------
RELATED_WORK = [
    (
        "Arcelli Fontana, F., Mäntylä, M. V., Zanoni, M., & Marino, A. (2016). Comparing "
        "and experimenting machine learning techniques for code smell detection. "
        "*Empirical Software Engineering, 21*(3), 1143–1191. "
        "https://doi.org/10.1007/s10664-015-9378-4"
    ),
    (
        "Azeem, M. I., Palomba, F., Shi, L., & Wang, Q. (2019). Machine learning "
        "techniques for code smell detection: A systematic literature review and "
        "meta-analysis. *Information and Software Technology, 108*, 115–138. "
        "https://doi.org/10.1016/j.infsof.2018.12.009"
    ),
    (
        "Bavota, G., De Lucia, A., Di Penta, M., Oliveto, R., & Palomba, F. (2015). An "
        "experimental investigation on the innate relationship between quality and "
        "refactoring. *Journal of Systems and Software, 107*, 1–14. "
        "https://doi.org/10.1016/j.jss.2015.05.024"
    ),
    (
        "Cunningham, W. (1992). The WyCash portfolio management system. Në *Addendum to "
        "the Proceedings on Object-Oriented Programming Systems, Languages, and "
        "Applications (OOPSLA ’92)* (f. 29–30). ACM. https://doi.org/10.1145/157709.157715"
    ),
    (
        "Di Nucci, D., Palomba, F., Tamburri, D. A., Serebrenik, A., & De Lucia, A. "
        "(2018). Detecting code smells using machine learning techniques: Are we there "
        "yet? Në *Proceedings of the 25th IEEE International Conference on Software "
        "Analysis, Evolution and Reengineering (SANER ’18)* (f. 612–621). IEEE. "
        "https://doi.org/10.1109/SANER.2018.8330266"
    ),
    (
        "Khomh, F., Di Penta, M., Guéhéneuc, Y.-G., & Antoniol, G. (2012). An "
        "exploratory study of the impact of antipatterns on class change- and "
        "fault-proneness. *Empirical Software Engineering, 17*(3), 243–275. "
        "https://doi.org/10.1007/s10664-011-9171-y"
    ),
    (
        "Lehman, M. M. (1980). Programs, life cycles, and laws of software evolution. "
        "*Proceedings of the IEEE, 68*(9), 1060–1076. "
        "https://doi.org/10.1109/PROC.1980.11805"
    ),
    (
        "Madeyski, L., & Lewowski, T. (2023). Detecting code smells using "
        "industry-relevant data. *Information and Software Technology, 155*, Artikulli "
        "107112. https://doi.org/10.1016/j.infsof.2022.107112"
    ),
    (
        "Mäntylä, M. V., & Lassenius, C. (2006). Subjective evaluation of software "
        "evolvability using code smells: An empirical study. *Empirical Software "
        "Engineering, 11*(3), 395–431. https://doi.org/10.1007/s10664-006-9002-8"
    ),
    (
        "Marinescu, R. (2004). Detection strategies: Metrics-based rules for detecting "
        "design flaws. Në *Proceedings of the 20th IEEE International Conference on "
        "Software Maintenance (ICSM ’04)* (f. 350–359). IEEE. "
        "https://doi.org/10.1109/ICSM.2004.1357820"
    ),
    (
        "Mens, T., & Tourwé, T. (2004). A survey of software refactoring. *IEEE "
        "Transactions on Software Engineering, 30*(2), 126–139. "
        "https://doi.org/10.1109/TSE.2004.1265817"
    ),
    (
        "Moha, N., Guéhéneuc, Y.-G., Duchien, L., & Le Meur, A.-F. (2010). DECOR: A "
        "method for the specification and detection of code and design smells. *IEEE "
        "Transactions on Software Engineering, 36*(1), 20–36. "
        "https://doi.org/10.1109/TSE.2009.50"
    ),
    (
        "Murphy-Hill, E., Parnin, C., & Black, A. P. (2012). How we refactor, and how we "
        "know it. *IEEE Transactions on Software Engineering, 38*(1), 5–18. "
        "https://doi.org/10.1109/TSE.2011.41"
    ),
    (
        "Opdyke, W. F. (1992). *Refactoring object-oriented frameworks* [Disertacion "
        "doktorature, University of Illinois at Urbana-Champaign]."
    ),
    (
        "Palomba, F., Bavota, G., Di Penta, M., Oliveto, R., Poshyvanyk, D., & De Lucia, "
        "A. (2015). Mining version histories for detecting code smells. *IEEE "
        "Transactions on Software Engineering, 41*(5), 462–489. "
        "https://doi.org/10.1109/TSE.2014.2372760"
    ),
    (
        "Palomba, F., Bavota, G., Di Penta, M., Fasano, F., Oliveto, R., & De Lucia, A. "
        "(2018). On the diffuseness and the impact on maintainability of code smells: A "
        "large scale empirical investigation. *Empirical Software Engineering, 23*(3), "
        "1188–1221. https://doi.org/10.1007/s10664-017-9535-z"
    ),
    (
        "Sharma, T., & Spinellis, D. (2018). A survey on software smells. *Journal of "
        "Systems and Software, 138*, 158–173. https://doi.org/10.1016/j.jss.2017.12.034"
    ),
    (
        "Silva, D., Tsantalis, N., & Valente, M. T. (2016). Why we refactor? Confessions "
        "of GitHub contributors. Në *Proceedings of the 24th ACM SIGSOFT International "
        "Symposium on Foundations of Software Engineering (FSE ’16)* (f. 858–870). ACM. "
        "https://doi.org/10.1145/2950290.2950305"
    ),
    (
        "Sjøberg, D. I. K., Yamashita, A., Anda, B. C. D., Mockus, A., & Dybå, T. (2013). "
        "Quantifying the effect of code smells on maintenance effort. *IEEE Transactions "
        "on Software Engineering, 39*(8), 1144–1156. https://doi.org/10.1109/TSE.2012.89"
    ),
    (
        "Tsantalis, N., & Chatzigeorgiou, A. (2009). Identification of Move Method "
        "refactoring opportunities. *IEEE Transactions on Software Engineering, 35*(3), "
        "347–367. https://doi.org/10.1109/TSE.2009.1"
    ),
    (
        "Tufano, M., Palomba, F., Bavota, G., Oliveto, R., Di Penta, M., De Lucia, A., & "
        "Poshyvanyk, D. (2015). When and why your code starts to smell bad. Në "
        "*Proceedings of the 37th IEEE/ACM International Conference on Software "
        "Engineering (ICSE ’15)* (f. 403–414). IEEE. https://doi.org/10.1109/ICSE.2015.59"
    ),
    (
        "Yamashita, A., & Moonen, L. (2013). Do developers care about code smells? An "
        "exploratory survey. Në *Proceedings of the 20th Working Conference on Reverse "
        "Engineering (WCRE ’13)* (f. 242–251). IEEE. "
        "https://doi.org/10.1109/WCRE.2013.6671299"
    ),
]

# ---------------------------------------------------------------------
# Mjetet, të cituara si softuer sipas APA-s
# ---------------------------------------------------------------------
# Tree-sitter nuk publikon skedar citimi; autori është krijuesi i tij dhe mbajtësi
# i të drejtave në licencë, siç e do APA për softuerin pa autor kolektiv.
TOOLS = [
    (
        "Brunsfeld, M. (2026). *Tree-sitter: An incremental parsing system for "
        "programming tools* (Versioni 0.26) [Softuer]. "
        "https://tree-sitter.github.io/tree-sitter/"
    ),
]


def _sort_key(reference: str) -> str:
    """Renditje alfabetike që nuk e prish diakritika.

    Pa këtë, «Mäntylä» bie pas «Murphy-Hill», sepse «ä» renditet pas çdo shkronje
    ASCII. Dekompozimi i heq shenjat dhe e lë emrin aty ku e pret lexuesi. Shenja e
    shkronjave të pjerrëta hiqet po ashtu, që të mos renditet si shkronjë.
    """
    stripped = unicodedata.normalize("NFKD", reference.replace("*", ""))
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
# autorët, viti, titulli, vëllimi dhe faqet dolën si janë shkruar.
#
# Më 2026-10-15, me kalimin në APA, çdo DOI i shtuar te lista u kërkua te Crossref
# (`api.crossref.org/works/<doi>`), dhe titulli, autori i parë, viti, vëllimi,
# fashikulli dhe faqet që ktheu përputheshin me hyrjen, 37 nga 37. Efron &
# Tibshirani mbetet pa DOI, sepse DOI-ja që ekziston i përket ribotimit të Springer-it
# dhe jo botimit të Chapman & Hall që citohet. Cawley & Talbot 2010 dhe lista e plotë
# e 16 autorëve të Pedregosa et al. 2011 u kontrolluan te faqja e JMLR-së, që nuk
# cakton DOI. Mäntylä & Lassenius mban vitin e fashikullit (2006); Crossref jep 2007
# si vit të botimit në letër të të njëjtit fashikull.
PAGES_VERIFIED = (
    "Arcelli Fontana et al. 2016",
    "Azeem et al. 2019",
    "Bavota et al. 2015",
    "Bieman & Kang 1995",
    "Breiman 2001",
    "Brown et al. 2001",
    "Cawley & Talbot 2010",
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
