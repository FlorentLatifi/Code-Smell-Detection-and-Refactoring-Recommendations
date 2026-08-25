# Regjistri i vendimeve

Çdo vendim teknik me pasoja, i shkruar kur merret. Ky skedar është lënda e parë e
**Kapitullit 4 (Metodologjia)** — mbrojtja e një zgjedhjeje tre muaj më vonë, nga
kujtesa, është ku humbin pikët.

Formati: konteksti → vendimi → alternativat → pasojat. Një vendim i ndryshuar nuk
fshihet; i shtohet një hyrje e re që e zëvendëson, sepse edhe ndryshimi i mendjes
është metodologji.

| # | Vendimi | Data | Statusi |
|---|---|---|---|
| VD-01 | Java si gjuhë e vetme e analizuar | 2026-08-25 | aktiv |
| VD-02 | tree-sitter si front-end analizues | 2026-08-25 | aktiv |
| VD-03 | Pa LLM në rrugën e produktit | 2026-08-25 | aktiv |
| VD-04 | Tri qasje të pavarura dhe të krahasueshme | 2026-08-25 | aktiv |
| VD-05 | MLCQ si e vërtetë bazë | 2026-08-25 | aktiv |
| VD-06 | Ashpërsia derivohet nga teprica, në shkallën e MLCQ | 2026-08-25 | aktiv |
| VD-07 | Pragjet të centralizuara dhe të citueshme | 2026-08-25 | aktiv |
| VD-08 | Detektorët kthejnë kushtet, jo boolean | 2026-08-25 | aktiv |
| VD-09 | Large Class e ndarë nga God Class | 2026-08-25 | aktiv |
| VD-10 | Python për backend-in që analizon Java | 2026-08-25 | aktiv |
| VD-11 | Refuzimi është rezultat i saktë i refaktorimit | 2026-08-25 | aktiv |
| VD-12 | Ndarje sipas depos në vlerësimin ML | 2026-08-25 | aktiv |
| VD-13 | Punimi gjenerohet me kod, jo formatohet me dorë | 2026-08-25 | aktiv |
| VD-14 | Portë cilësie e detyrueshme para shkrimit të kodit kritik | 2026-08-25 | aktiv |

---

### VD-01 — Java si gjuhë e vetme e analizuar

**Konteksti.** Detektimi i code smells varet nga metrika objekt-orientuara që
supozojnë klasa, trashëgimi dhe fusha.

**Vendimi.** Analizohet vetëm Java.

**Alternativat.** Mbështetje shumë-gjuhëshe; Python si gjuhë e dytë.

**Pasojat.** Metrikat CK zbatohen drejtpërdrejt pa përshtatje; MLCQ është
tërësisht Java, pra e vërteta bazë përputhet me objektin e analizës; verifikimi
me `javac` bëhet i mundur. Kufizim: përgjithësimi te gjuhët jo-OO nuk pretendohet
dhe raportohet te "kufizimet".

---

### VD-02 — tree-sitter si front-end analizues

**Konteksti.** Nevojitet një pemë analize e saktë për Java-n moderne, pa varësi
nga JVM-ja gjatë analizës.

**Vendimi.** `tree-sitter` + `tree-sitter-java`.

**Alternativat.** `javalang` (Python, i pambështetur mirë për sintaksën pas Java 8);
JavaParser përmes një procesi Java (kërkon JVM dhe një urë ndër-procesore).

**Pasojat.** Mbulon record, sealed types, switch expressions dhe lambda; analiza
nuk kërkon JVM. Kompromis i pranuar: tree-sitter nuk zgjidh simbole, prandaj
parser-i regjistron vetëm fakte sintaksore dhe interpretimi bëhet te `metrics/`,
ku klasa deklaruese njihet. Kjo mjafton për të gjitha strategjitë e Lanza &
Marinescu dhe shmang ndërtimin e një sistemi tipash.

---

### VD-03 — Pa LLM në rrugën e produktit

**Konteksti.** Rekomandimet e refaktorimit mund të gjenerohen nga një model
gjuhësor. API-të me pagesë janë të përjashtuara (kosto), dhe një model lokal mbi
Ryzen 7 5825U pa GPU të dedikuar është praktikisht i papërdorshëm.

**Vendimi.** Refaktorimet janë transformime deterministike mbi AST, sipas
katalogut të Fowler-it.

**Alternativat.** API e paguar; model lokal i kuantizuar; qasje hibride.

**Pasojat.** Dalja është e riprodhueshme dhe e verifikueshme me `javac` — një
pretendim empirik shumë më i fortë se "modeli propozoi diçka që duket mirë".
Komisioni mund ta ekzekutojë sistemin pa asnjë çelës. Kufizim: mbulohen vetëm
transformimet e implementuara, jo çdo rishkrim i mundshëm.

---

### VD-04 — Tri qasje të pavarura dhe të krahasueshme

**Konteksti.** Një punim diplome ka nevojë për një pyetje kërkimore, jo vetëm për
një vegël.

**Vendimi.** Tri shtylla: (A) rregulla me metrika, (B) machine learning mbi MLCQ,
(C) motor refaktorimi. A dhe B prodhojnë dalje të krahasueshme mbi të njëjtin
input.

**Alternativat.** Vetëm rregulla (i thjeshtë por pa kontribut); vetëm ML (kuti e
zezë, pa gjurmueshmëri).

**Pasojat.** Krahasimi A vs B është kontributi kryesor empirik. Kërkon që të dyja
qasjet të ndajnë të njëjtën shkallë ashpërsie dhe të njëjtat entitete — prandaj
VD-06 dhe përputhësi i Fazës 1.

---

### VD-05 — MLCQ si e vërtetë bazë

**Konteksti.** ML-ja kërkon etiketa; vlerësimi i Qasjes A kërkon një referencë të
pavarur nga vetë rregullat tona.

**Vendimi.** MLCQ (Madeyski & Lewowski, 2020) — mostra Java të etiketuara nga
zhvillues profesionistë, për Blob, Data Class, Long Method dhe Feature Envy.

**Alternativat.** Etiketim manual (i pamundur në shkallë brenda afatit);
dataset-e sintetike (jo relevante industrialisht); dalja e një vegle tjetër si
referencë (do të matte pajtimin me atë vegël, jo saktësinë).

**Pasojat.** Katër smells kanë vlerësim sasior; katër të tjerët e implementuar
(Large Class, Brain Method, Long Parameter List, Deep Nesting) raportohen vetëm
në mënyrë përshkruese, dhe kjo thuhet hapur. MLCQ nuk përmban kod — korpusi duhet
materializuar nga GitHub, me humbjen e pashmangshme të depove të fshira, e cila
raportohet si kufizim i studimit.

---

### VD-06 — Ashpërsia derivohet nga teprica, në shkallën e MLCQ

**Konteksti.** Ashpërsia e caktuar në mënyrë arbitrare ("God Class = gjithmonë
kritike") nuk mbrohet dot.

**Vendimi.** `Severity` merr vlerat `minor/major/critical` — pikërisht shkalla e
MLCQ — dhe llogaritet si mesatare e tepricës mbi pragje, e kufizuar në 5× që një
metrikë ekstreme të mos e ngrejë vetëm një rast të butë.

**Alternativat.** Ashpërsi fikse për smell; ashpërsi e mësuar nga ML-ja.

**Pasojat.** Dalja e rregullave krahasohet me etiketat manuale pa hap përkthimi.
Kufizimi 5× dhe kufijtë 1.5/2.5 janë zgjedhje kalibrimi që duhet t'i nënshtrohen
analizës së ndjeshmërisë në Fazën 5.

---

### VD-07 — Pragjet të centralizuara dhe të citueshme

**Konteksti.** Pragjet e shpërndara nëpër kod nuk mund as të mbrohen as të
variohen.

**Vendimi.** Të gjitha në `detectors/thresholds.py`, si `dataclass` e ngrirë, me
burimin e cituar pranë secilës vlerë.

**Pasojat.** Analiza e ndjeshmërisë bëhet programatikisht duke krijuar instanca
alternative; ngrirja pengon që një fshirje ta ndotë bazën me të cilën krahasohet.

---

### VD-08 — Detektorët kthejnë kushtet, jo boolean

**Konteksti.** Një vegël që thotë vetëm "kjo klasë ka erë" nuk ndihmon askënd.

**Vendimi.** Çdo `Smell` mban listën e `Condition`-eve me metrikën, operatorin,
pragun dhe vlerën e matur.

**Pasojat.** Ndërfaqja shpjegon *pse*; punimi raporton cila klauzolë e mbajti
detektimin; ashpërsia rrjedh nga matja. Kosto: pak më shumë kod për detektor,
plotësisht e justifikuar.

---

### VD-09 — Large Class e ndarë nga God Class

**Konteksti.** Të dyja kanë të bëjnë me madhësinë e klasës.

**Vendimi.** Raportohen veçmas: God Class kërkon edhe dëshminë e mungesës së
kohezionit (WMC ∧ TCC ∧ ATFD), Large Class vetëm madhësinë (CLOC ∨ NOM).

**Pasojat.** Një klasë e madhe por kohezive nuk etiketohet si God Class. Në
vlerësimin ndaj MLCQ-së, vetëm God Class krahasohet me etiketën *Blob*; Large
Class trajtohet si sinjal i veçantë, jo si i njëjti smell.

---

### VD-10 — Python për backend-in që analizon Java

**Konteksti.** Sistemi analizon Java; nuk rrjedh që duhet shkruar në Java.

**Vendimi.** Python 3.13 për analizën, ML-në dhe API-në.

**Alternativat.** Java me JavaParser dhe Spring (ekosistemi vendas i analizës);
hibrid Java-analizë + Python-ML.

**Pasojat.** scikit-learn dhe pandas janë të disponueshme drejtpërdrejt, pa urë
ndër-gjuhëshe — vendimtare për Shtyllën B. `javac` përdoret vetëm si nënproces
verifikimi, që është një sipërfaqe e vogël dhe e kontrolluar.

---

### VD-11 — Refuzimi është rezultat i saktë i refaktorimit

**Konteksti.** Një transformim mbi kod të huaj mund ta prishë atë kur parakushtet
nuk verifikohen.

**Vendimi.** Kur një parakusht nuk provohet nga pema e analizës, transformimi
kthen "e paaplikueshme" me arsye, dhe kjo numërohet në rezultate.

**Alternativat.** Provo gjithsesi dhe kthehu prapa nëse `javac` dështon (rrezik
ndryshimesh që kompilojnë por ndryshojnë sjelljen).

**Pasojat.** Shkalla e aplikimit do të jetë më e ulët se e një vegle agresive,
por çdo transformim i aplikuar është i mbrojtshëm. Shpërndarja e arsyeve të
refuzimit bëhet vetë një rezultat interesant i punimit.

---

### VD-12 — Ndarje sipas depos në vlerësimin ML

**Konteksti.** MLCQ përmban shumë mostra nga e njëjta depo, me stil dhe konventa
të përbashkëta.

**Vendimi.** `GroupKFold` me depon si grup; asnjë depo nuk shfaqet njëkohësisht
në trajnim dhe testim. Farë e fiksuar.

**Alternativat.** Ndarje e rastësishme sipas rreshtave (jep numra dukshëm më të
mirë — dhe të pavlefshëm).

**Pasojat.** Rezultate më modeste por të vërteta, që matin përgjithësimin te një
projekt i panjohur — pikërisht ai është përdorimi real i veglës.

---

### VD-13 — Punimi gjenerohet me kod, jo formatohet me dorë

**Konteksti.** Shablloni i UBT-së ka tri regjime numërimi faqesh, rregulla fonti
për nivel titulli dhe hapësirë rreshtash minimale — të lehta për t'u prishur me
redaktim manual.

**Vendimi.** `docs/thesis/build_thesis.py` e ndërton dokumentin me `python-docx`;
përmbajtja qëndron e ndarë nga paraqitja.

**Pasojat.** Përputhshmëria me shabllonin rifitohet me një ekzekutim. Kufizim i
rëndësishëm: pas dorëzimit të skeletit, redaktimi kalon në Word dhe rikthimi i
skriptit e mbishkruan skedarin — pra në atë pikë skripti dhe dokumenti duhet të
konsiderohen të shkëputur, ose përmbajtja të mbahet e sinkronizuar në `CONTENT`.

---

### VD-14 — Portë cilësie e detyrueshme para shkrimit të kodit kritik

**Konteksti.** Kodi kryesor (motori i refaktorimit, harness-i i vlerësimit) ende
nuk është shkruar. Vendosja e kontrolleve automatike *pasi* të shkruhet do të
thoshte t'i zbatosh mbi disa mijëra rreshta njëherësh — çka zakonisht përfundon
me çaktivizimin e tyre.

**Vendimi.** `ruff` (lint + format), `mypy --strict`, `pytest-cov` dhe GitHub
Actions vendosen para Fazës 1. Paralajmërimet e testeve trajtohen si gabime.
Python-i pinohet në 3.13 edhe në CI.

**Alternativat.** Vetëm teste (linter-i dhe tipizimi shtohen më vonë ose kurrë);
`mypy` jo-strikt për të shmangur anotimet.

**Pasojat.** Kostoja u pagua menjëherë dhe u kthye po aq shpejt: kontrollet
zbuluan një defekt që rrëzonte tërë analizën e një projekti (`Node.text` mund të
jetë `None`), një element të dyfishtë në filtrin e LOC-ut, dhe faktin që `cli.py` —
pikënisja e eksperimenteve — nuk kishte asnjë test. Kufizim i pranuar: `ruff format`
i shpërthen listat e kolonave CSV një-për-rresht, çka është më pak e lexueshme se
rreshtimi tabelar; pranohet si kompromis dhe pastrohet në Fazën 4, kur API-ja t'i
ripërdorë ato kolona si konstante të përbashkët.

Pinimi i Python 3.13 nuk është pedanteri: një metrikë që ndryshon vlerë në heshtje
mes versioneve të interpretuesit do t'i bënte të pariprodhueshme numrat e publikuar.
