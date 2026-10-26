# JavaSmell në një imazh të vetëm: ndërfaqja, API-ja, modelet e Qasjes B dhe JDK-ja
# për verifikimin e rishkrimeve. Përdoruesi nuk instalon as Python, as Node, as
# Java (VD-142).
#
#   docker build -t javasmell .
#   docker run --rm -p 127.0.0.1:8000:8000 -v "/shtegu/i/projekteve:/projekte" javasmell
#
# Pastaj hapet http://localhost:8000.
#
# Imazhet bazë fiksohen me digest dhe jo vetëm me etiketë: një etiketë si `3.13-slim`
# lëviz çdo javë, dhe i njëjti Dockerfile ndërtonte imazhe të ndryshme pa asnjë
# ndryshim në depo. Dependabot i përditëson digest-et me pull request (VD-158).
# Secili digest është i një liste për disa arkitektura, ndaj vlen për amd64 dhe arm64.

# --- 1. Ndërfaqja: Node duhet vetëm për ta ndërtuar ------------------------------
FROM node:26-slim@sha256:36793bcbb160a6a16cede1e62b93f84e26b78a972a8a4c0b879c1c12f22761ec AS interface
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Faqja e vlerësimit i lexon shifrat e punimit gjatë ndërtimit, nga i njëjti burim.
COPY data/results/*.json /app/data/results/
# Fjalori i mënyrës së thjeshtë, i njëjti që lexon CLI-ja (VD-144).
COPY backend/javasmell/glossary/plain_sq.json /app/backend/javasmell/glossary/
RUN npm run build

# --- 2. Varësitë Python, të përbashkëta për trajnimin dhe për imazhin ------------
FROM python:3.13-slim@sha256:d98cc29d3266e535dd9da1099688d9cb3ca4753813571e071763d17725460962 AS python
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
# Dosjet `tests` të bibliotekave (rreth 60 MB, kryesisht të SciPy-së) nuk importohen
# kurrë gjatë punës; janë testet e vetë bibliotekave. Hiqen në të njëjtin hap, sepse
# një `rm` në shtresë tjetër nuk e zvogëlon imazhin.
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && find /usr/local/lib/python3.13/site-packages -depth -type d -name tests \
        -exec rm -rf {} +

# --- JDK-ja, pa pjesët që javac-u nuk i lexon ------------------------------------
# `jmods/` (rreth 80 MB) i duhet vetëm jlink-ut. javac-u lexon `lib/modules` dhe
# `lib/ct.sym`, që mbeten të paprekura: verdikti i kompilimit nuk ndryshon. Një JDK
# i ngushtuar me jlink do të ishte më i vogël, por do të ndryshonte cilat API i
# sheh javac-u, pra edhe verdiktet (VD-158).
FROM eclipse-temurin:25-jdk@sha256:2d5d5e9b533342a565907c84f47a2ec298c40cde7b13a3ca85d4950fa456a641 AS jdk
RUN rm -rf /opt/java/openjdk/jmods /opt/java/openjdk/man /opt/java/openjdk/lib/src.zip

# --- 3. Modelet: trajnohen nga tabela e komituar, si te README-ja ----------------
# `data/models/` nuk komitohet, sepse një estimator i ruajtur me pickle nuk është i
# përcaktuar mes versioneve të scikit-learn. Këtu trajnohet me të njëjtat pina që
# do ta lexojnë, ndaj ky problem nuk lind. Rezultatet e vlerësimit shkruhen jashtë
# imazhit përfundimtar: shifrat e punimit mbeten ato të komituara.
FROM python AS models
COPY backend/javasmell backend/javasmell
COPY scripts/train_models.py scripts/train_models.py
COPY data/results/mlcq_dataset.csv data/results/rules_evaluation_samples.csv data/results/
RUN python scripts/train_models.py --out /tmp/vleresimi --models data/models

# --- 4. Imazhi që ekzekutohet ----------------------------------------------------
FROM python
# javac-u verifikon çdo rishkrim (Nënkapitulli 4.7). Pa të, patch-i ndërtohet njësoj
# por çdo verdikt del «i pakontrolluar». JDK-ja merret nga imazhi zyrtar i Temurin-it
# dhe jo nga apt, që versioni të jetë i njëjtë kudo ku ndërtohet imazhi.
# `verify.javac_command` e gjen te JAVA_HOME (VD-139).
COPY --from=jdk /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:$PATH

# «Apliko» shkruan vetëm brenda një depoje git të pastër, sepse `git restore .` është
# zhbërja (VD-111). Pa git-in në imazh, çdo shkrim refuzohej si «nuk është depo git»,
# edhe kur projekti i montuar ishte depo e pastër (VD-143). `safe.directory`: dosja
# e montuar i përket përdoruesit të kompjuterit dhe jo atij të kontejnerit, dhe git-i
# e refuzon një depo me pronar tjetër. Kontejneri prek vetëm atë që montohet, ndaj
# pronësia këtu nuk mbron asgjë.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*' \
    && pip uninstall --yes pip
# pip-i i duhet vetëm ndërtimit. Kopjet e tij të brendshme të urllib3-it dhe
# msgpack-ut kishin dobësi të njohura që skaneri i raportonte, edhe pse mjeti nuk i
# përdor kurrë; pa pip-in, imazhi nuk mban kod që askush nuk e thërret (VD-158).

COPY backend/javasmell backend/javasmell
COPY data/results/mlcq_dataset.csv data/results/mlcq_dataset.csv
# Tabela dhe modelet rrjedhin nga MLCQ (CC BY 4.0), që kërkon atribuimin kudo ku
# shpërndahen; imazhi është një shpërndarje e tillë (VD-157).
COPY LICENSE NOTICE ./
COPY --from=models /app/data/models data/models
COPY --from=interface /app/frontend/dist frontend/dist

# Projektet e përdoruesit montohen te /projekte; depot nga GitHub zbresin te
# /app/data/projects, që një vëllim mund t'i mbajë mes nisjeve.
ENV JAVASMELL_ROOT=/projekte \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1000 javasmell \
    && mkdir -p /projekte data/projects \
    && chown javasmell /projekte data/projects
USER javasmell

EXPOSE 8000
# Brenda kontejnerit serveri dëgjon në të gjitha ndërfaqet, sepse ndryshe porti nuk
# arrihet nga jashtë. Kufiri i rrjetit vendoset te `-p 127.0.0.1:8000:8000`, dhe
# roja e API-së pranon ende vetëm emrat localhost (VD-127).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request as u; u.urlopen(u.Request('http://127.0.0.1:8000/api/health', headers={'Host': 'localhost'}), timeout=4)"
CMD ["python", "-m", "uvicorn", "javasmell.api.bundle:create_bundle", "--factory", \
     "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
