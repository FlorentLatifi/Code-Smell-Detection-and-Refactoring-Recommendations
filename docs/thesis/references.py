"""Referencat e punimit, në stilin IEEE.

Mentorja kërkoi më 16 tetor 2026 stilin IEEE, një ditë pasi kishte kërkuar APA-n
(VD-151), dhe ndryshimet i bëri vetë te kopja e punimit që dërgoi. Hyrjet këtu janë
ato të asaj kopjeje, fjalë për fjalë; vetëm numri para tyre mungon (VD-152).

Çdo hyrje është një çift: etiketa «Mbiemri vit» dhe teksti. Etiketa është çelësi me të
cilin teksti e citon burimin. Kapitujt shkruajnë «Fowler (2018)» ose «(Lanza &
Marinescu, 2006)», dhe `build_thesis` i kthen në «Fowler [2]» dhe «[5]». Numri nuk
shkruhet as këtu as te kapitujt: lista numërohet sipas radhës në të cilën burimi
citohet për herë të parë, duke nisur nga Kapitulli 1, dhe ajo radhë është veti e
tekstit. Një paragraf i zhvendosur e rinumëron listën vetë, në vend që ta lërë me
numra që nuk ndjekin më leximin.

Shkurtimet janë ato standarde të IEEE-së (vol., no., pp., ed., Art. no., doi:), emrat
e revistave shkruhen të plotë, dhe vendi i botuesit të një libri jepet si «Qyteti, ST,
Shteti». Me më shumë se gjashtë autorë hyrja mban vetëm të parin dhe «et al.». Pjesët
me `*...*` shtypen me shkronja të pjerrëta: titulli i librit dhe emri i revistës ose i
përmbledhjes së konferencës. `build_references` e lexon këtë shenjë; teksti i
kapitujve nuk e përdor.

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

# ---------------------------------------------------------------------
# Burimet që sistemi i zbaton drejtpërdrejt
# ---------------------------------------------------------------------
CITED_BY_SYSTEM = [
    (
        "Bieman & Kang 1995",
        "J. M. Bieman and B.-K. Kang, “Cohesion and reuse in an object-oriented system,” in "
        "*Proceedings of the 1995 Symposium on Software Reusability (SSR ’95)*, 1995, pp. "
        "259–262, doi: 10.1145/211782.211856."
    ),
    (
        "Chidamber & Kemerer 1994",
        "S. R. Chidamber and C. F. Kemerer, “A metrics suite for object oriented design,” "
        "*IEEE Transactions on Software Engineering*, vol. 20, no. 6, pp. 476–493, 1994, "
        "doi: 10.1109/32.295895."
    ),
    (
        "Fowler 2018",
        "M. Fowler, *Refactoring: Improving the Design of Existing Code*, 2nd ed. Boston, "
        "MA, USA: Addison-Wesley, 2018."
    ),
    (
        "Henderson-Sellers 1996",
        "B. Henderson-Sellers, *Object-Oriented Metrics: Measures of Complexity*. Upper "
        "Saddle River, NJ, USA: Prentice Hall, 1996."
    ),
    (
        "Lanza & Marinescu 2006",
        "M. Lanza and R. Marinescu, *Object-Oriented Metrics in Practice: Using Software "
        "Metrics to Characterize, Evaluate, and Improve the Design of Object-Oriented "
        "Systems*. Berlin, Germany: Springer, 2006, doi: 10.1007/3-540-39538-5."
    ),
    (
        "Madeyski & Lewowski 2020",
        "L. Madeyski and T. Lewowski, “MLCQ: Industry-relevant code smell data set,” in "
        "*Proceedings of the 24th International Conference on Evaluation and Assessment in "
        "Software Engineering (EASE ’20)*, 2020, pp. 342–347, doi: 10.1145/3383219.3383264."
    ),
    (
        "McCabe 1976",
        "T. J. McCabe, “A complexity measure,” *IEEE Transactions on Software Engineering*, "
        "vol. SE-2, no. 4, pp. 308–320, 1976, doi: 10.1109/TSE.1976.233837."
    ),
    (
        "Park 1992",
        "R. E. Park, “Software size measurement: A framework for counting source "
        "statements,” Software Engineering Institute, Carnegie Mellon University, "
        "Pittsburgh, PA, USA, Tech. Rep. CMU/SEI-92-TR-020, 1992."
    ),
]

# ---------------------------------------------------------------------
# Burimet metodologjike: si maten dhe si raportohen rezultatet
# ---------------------------------------------------------------------
METHODOLOGY = [
    (
        "Breiman 2001",
        "L. Breiman, “Random forests,” *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001, "
        "doi: 10.1023/A:1010933404324."
    ),
    (
        "Brown et al. 2001",
        "L. D. Brown, T. T. Cai, and A. DasGupta, “Interval estimation for a binomial "
        "proportion,” *Statistical Science*, vol. 16, no. 2, pp. 101–133, 2001, doi: "
        "10.1214/ss/1009213286."
    ),
    (
        "Cawley & Talbot 2010",
        "G. C. Cawley and N. L. C. Talbot, “On over-fitting in model selection and "
        "subsequent selection bias in performance evaluation,” *Journal of Machine Learning "
        "Research*, vol. 11, no. 70, pp. 2079–2107, 2010. [Online]. Available: "
        "https://www.jmlr.org/papers/v11/cawley10a.html"
    ),
    (
        "Chicco & Jurman 2020",
        "D. Chicco and G. Jurman, “The advantages of the Matthews correlation coefficient "
        "(MCC) over F1 score and accuracy in binary classification evaluation,” *BMC "
        "Genomics*, vol. 21, no. 1, Art. no. 6, 2020, doi: 10.1186/s12864-019-6413-7."
    ),
    (
        "Cohen 1960",
        "J. Cohen, “A coefficient of agreement for nominal scales,” *Educational and "
        "Psychological Measurement*, vol. 20, no. 1, pp. 37–46, 1960, doi: "
        "10.1177/001316446002000104."
    ),
    (
        "Efron & Tibshirani 1993",
        "B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York, NY, "
        "USA: Chapman & Hall, 1993."
    ),
    (
        "Friedman 2001",
        "J. H. Friedman, “Greedy function approximation: A gradient boosting machine,” *The "
        "Annals of Statistics*, vol. 29, no. 5, pp. 1189–1232, 2001, doi: "
        "10.1214/aos/1013203451."
    ),
    (
        "Kaufman et al. 2012",
        "S. Kaufman, S. Rosset, C. Perlich, and O. Stitelman, “Leakage in data mining: "
        "Formulation, detection, and avoidance,” *ACM Transactions on Knowledge Discovery "
        "from Data*, vol. 6, no. 4, Art. no. 15, 2012, doi: 10.1145/2382577.2382579."
    ),
    (
        "Matthews 1975",
        "B. W. Matthews, “Comparison of the predicted and observed secondary structure of T4 "
        "phage lysozyme,” *Biochimica et Biophysica Acta (BBA) – Protein Structure*, vol. "
        "405, no. 2, pp. 442–451, 1975, doi: 10.1016/0005-2795(75)90109-9."
    ),
    (
        "Pedregosa et al. 2011",
        "F. Pedregosa et al., “Scikit-learn: Machine learning in Python,” *Journal of "
        "Machine Learning Research*, vol. 12, no. 85, pp. 2825–2830, 2011. [Online]. "
        "Available: https://jmlr.org/papers/v12/pedregosa11a.html"
    ),
    (
        "PMD Team 2026",
        "PMD Team, *PMD: An Extensible Cross-Language Static Code Analyzer*, version 7.27.0. "
        "(2026). [Online]. Available: https://pmd.github.io/"
    ),
    (
        "Strobl et al. 2007",
        "C. Strobl, A.-L. Boulesteix, A. Zeileis, and T. Hothorn, “Bias in random forest "
        "variable importance measures: Illustrations, sources and a solution,” *BMC "
        "Bioinformatics*, vol. 8, no. 1, Art. no. 25, 2007, doi: 10.1186/1471-2105-8-25."
    ),
    (
        "Wilson 1927",
        "E. B. Wilson, “Probable inference, the law of succession, and statistical "
        "inference,” *Journal of the American Statistical Association*, vol. 22, no. 158, "
        "pp. 209–212, 1927, doi: 10.1080/01621459.1927.10502953."
    ),
    (
        "Wohlin et al. 2012",
        "C. Wohlin, P. Runeson, M. Höst, M. C. Ohlsson, B. Regnell, and A. Wesslén, "
        "*Experimentation in Software Engineering*. Berlin, Germany: Springer, 2012, doi: "
        "10.1007/978-3-642-29044-2."
    ),
]

# ---------------------------------------------------------------------
# Puna e lidhur, për Kapitullin 2
# ---------------------------------------------------------------------
RELATED_WORK = [
    (
        "Arcelli Fontana et al. 2016",
        "F. Arcelli Fontana, M. V. Mäntylä, M. Zanoni, and A. Marino, “Comparing and "
        "experimenting machine learning techniques for code smell detection,” *Empirical "
        "Software Engineering*, vol. 21, no. 3, pp. 1143–1191, 2016, doi: "
        "10.1007/s10664-015-9378-4."
    ),
    (
        "Azeem et al. 2019",
        "M. I. Azeem, F. Palomba, L. Shi, and Q. Wang, “Machine learning techniques for code "
        "smell detection: A systematic literature review and meta-analysis,” *Information "
        "and Software Technology*, vol. 108, pp. 115–138, 2019, doi: "
        "10.1016/j.infsof.2018.12.009."
    ),
    (
        "Bavota et al. 2015",
        "G. Bavota, A. De Lucia, M. Di Penta, R. Oliveto, and F. Palomba, “An experimental "
        "investigation on the innate relationship between quality and refactoring,” *Journal "
        "of Systems and Software*, vol. 107, pp. 1–14, 2015, doi: 10.1016/j.jss.2015.05.024."
    ),
    (
        "Cunningham 1992",
        "W. Cunningham, “The WyCash portfolio management system,” in *Addendum to the "
        "Proceedings on Object-Oriented Programming Systems, Languages, and Applications "
        "(OOPSLA ’92)*, 1992, pp. 29–30, doi: 10.1145/157709.157715."
    ),
    (
        "Di Nucci et al. 2018",
        "D. Di Nucci, F. Palomba, D. A. Tamburri, A. Serebrenik, and A. De Lucia, “Detecting "
        "code smells using machine learning techniques: Are we there yet?” in *Proceedings "
        "of the 25th IEEE International Conference on Software Analysis, Evolution and "
        "Reengineering (SANER ’18)*, 2018, pp. 612–621, doi: 10.1109/SANER.2018.8330266."
    ),
    (
        "Khomh et al. 2012",
        "F. Khomh, M. Di Penta, Y.-G. Guéhéneuc, and G. Antoniol, “An exploratory study of "
        "the impact of antipatterns on class change- and fault-proneness,” *Empirical "
        "Software Engineering*, vol. 17, no. 3, pp. 243–275, 2012, doi: "
        "10.1007/s10664-011-9171-y."
    ),
    (
        "Lehman 1980",
        "M. M. Lehman, “Programs, life cycles, and laws of software evolution,” *Proceedings "
        "of the IEEE*, vol. 68, no. 9, pp. 1060–1076, 1980, doi: 10.1109/PROC.1980.11805."
    ),
    (
        "Madeyski & Lewowski 2023",
        "L. Madeyski and T. Lewowski, “Detecting code smells using industry-relevant data,” "
        "*Information and Software Technology*, vol. 155, Art. no. 107112, 2023, doi: "
        "10.1016/j.infsof.2022.107112."
    ),
    (
        "Marinescu 2004",
        "R. Marinescu, “Detection strategies: Metrics-based rules for detecting design "
        "flaws,” in *Proceedings of the 20th IEEE International Conference on Software "
        "Maintenance (ICSM ’04)*, 2004, pp. 350–359, doi: 10.1109/ICSM.2004.1357820."
    ),
    (
        "Mens & Tourwé 2004",
        "T. Mens and T. Tourwé, “A survey of software refactoring,” *IEEE Transactions on "
        "Software Engineering*, vol. 30, no. 2, pp. 126–139, 2004, doi: "
        "10.1109/TSE.2004.1265817."
    ),
    (
        "Moha et al. 2010",
        "N. Moha, Y.-G. Guéhéneuc, L. Duchien, and A.-F. Le Meur, “DECOR: A method for the "
        "specification and detection of code and design smells,” *IEEE Transactions on "
        "Software Engineering*, vol. 36, no. 1, pp. 20–36, 2010, doi: 10.1109/TSE.2009.50."
    ),
    (
        "Murphy-Hill et al. 2012",
        "E. Murphy-Hill, C. Parnin, and A. P. Black, “How we refactor, and how we know it,” "
        "*IEEE Transactions on Software Engineering*, vol. 38, no. 1, pp. 5–18, 2012, doi: "
        "10.1109/TSE.2011.41."
    ),
    (
        "Mäntylä & Lassenius 2006",
        "M. V. Mäntylä and C. Lassenius, “Subjective evaluation of software evolvability "
        "using code smells: An empirical study,” *Empirical Software Engineering*, vol. 11, "
        "no. 3, pp. 395–431, 2006, doi: 10.1007/s10664-006-9002-8."
    ),
    (
        "Opdyke 1992",
        "W. F. Opdyke, “Refactoring object-oriented frameworks,” Ph.D. dissertation, "
        "University of Illinois at Urbana-Champaign, Urbana, IL, USA, 1992."
    ),
    (
        "Palomba et al. 2015",
        "F. Palomba, G. Bavota, M. Di Penta, R. Oliveto, D. Poshyvanyk, and A. De Lucia, "
        "“Mining version histories for detecting code smells,” *IEEE Transactions on "
        "Software Engineering*, vol. 41, no. 5, pp. 462–489, 2015, doi: "
        "10.1109/TSE.2014.2372760."
    ),
    (
        "Palomba et al. 2018",
        "F. Palomba, G. Bavota, M. Di Penta, F. Fasano, R. Oliveto, and A. De Lucia, “On the "
        "diffuseness and the impact on maintainability of code smells: A large scale "
        "empirical investigation,” *Empirical Software Engineering*, vol. 23, no. 3, pp. "
        "1188–1221, 2018, doi: 10.1007/s10664-017-9535-z."
    ),
    (
        "Sharma & Spinellis 2018",
        "T. Sharma and D. Spinellis, “A survey on software smells,” *Journal of Systems and "
        "Software*, vol. 138, pp. 158–173, 2018, doi: 10.1016/j.jss.2017.12.034."
    ),
    (
        "Silva et al. 2016",
        "D. Silva, N. Tsantalis, and M. T. Valente, “Why we refactor? Confessions of GitHub "
        "contributors,” in *Proceedings of the 24th ACM SIGSOFT International Symposium on "
        "Foundations of Software Engineering (FSE ’16)*, 2016, pp. 858–870, doi: "
        "10.1145/2950290.2950305."
    ),
    (
        "Sjøberg et al. 2013",
        "D. I. K. Sjøberg, A. Yamashita, B. C. D. Anda, A. Mockus, and T. Dybå, “Quantifying "
        "the effect of code smells on maintenance effort,” *IEEE Transactions on Software "
        "Engineering*, vol. 39, no. 8, pp. 1144–1156, 2013, doi: 10.1109/TSE.2012.89."
    ),
    (
        "Tsantalis & Chatzigeorgiou 2009",
        "N. Tsantalis and A. Chatzigeorgiou, “Identification of Move Method refactoring "
        "opportunities,” *IEEE Transactions on Software Engineering*, vol. 35, no. 3, pp. "
        "347–367, 2009, doi: 10.1109/TSE.2009.1."
    ),
    (
        "Tufano et al. 2015",
        "M. Tufano et al., “When and why your code starts to smell bad,” in *Proceedings of "
        "the 37th IEEE/ACM International Conference on Software Engineering (ICSE ’15)*, "
        "2015, pp. 403–414, doi: 10.1109/ICSE.2015.59."
    ),
    (
        "Yamashita & Moonen 2013",
        "A. Yamashita and L. Moonen, “Do developers care about code smells? An exploratory "
        "survey,” in *Proceedings of the 20th Working Conference on Reverse Engineering "
        "(WCRE ’13)*, 2013, pp. 242–251, doi: 10.1109/WCRE.2013.6671299."
    ),
]

# ---------------------------------------------------------------------
# Mjetet, të cituara si softuer
# ---------------------------------------------------------------------
# Tree-sitter nuk publikon skedar citimi; autori është krijuesi i tij dhe mbajtësi
# i të drejtave në licencë.
TOOLS = [
    (
        "Brunsfeld 2026",
        "M. Brunsfeld, *Tree-sitter: An Incremental Parsing System for Programming Tools*, "
        "version 0.26. (2026). [Online]. Available: "
        "https://tree-sitter.github.io/tree-sitter/"
    ),
]


def all_references() -> list[tuple[str, str]]:
    """Të gjitha referencat si çifte (etiketa, hyrja), pa renditje.

    Renditja i përket tekstit, jo listës: `build_thesis` i rendit sipas citimit të parë.
    """
    return CITED_BY_SYSTEM + METHODOLOGY + RELATED_WORK + TOOLS


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
#
# Më 2026-10-16, me kalimin në IEEE, hyrjet u morën nga kopja e mentores. Çdo DOI,
# vëllim, fashikull, faqe dhe vit i tyre u krahasua me hyrjen APA që zëvendësuan, 45
# nga 45, dhe asnjë nuk ndryshonte; verifikimet më lart vlejnë pra edhe për to. Shtesat
# e IEEE-së (qyteti i botuesit, «2nd ed.», «[Online]») nuk kanë burim të dytë.
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
