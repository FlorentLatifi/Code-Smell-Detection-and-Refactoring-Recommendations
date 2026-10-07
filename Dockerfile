# JavaSmell në një imazh të vetëm: ndërfaqja, API-ja, modelet e Qasjes B dhe JDK-ja
# për verifikimin e rishkrimeve. Përdoruesi nuk instalon as Python, as Node, as
# Java (VD-142).
#
#   docker build -t javasmell .
#   docker run --rm -p 127.0.0.1:8000:8000 -v "/shtegu/i/projekteve:/projekte" javasmell
#
# Pastaj hapet http://localhost:8000.

# --- 1. Ndërfaqja: Node duhet vetëm për ta ndërtuar ------------------------------
FROM node:22-slim AS interface
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Faqja e vlerësimit i lexon shifrat e punimit gjatë ndërtimit, nga i njëjti burim.
COPY data/results/*.json /app/data/results/
RUN npm run build

# --- 2. Varësitë Python, të përbashkëta për trajnimin dhe për imazhin ------------
FROM python:3.13-slim AS python
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

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
COPY --from=eclipse-temurin:21-jdk /opt/java/openjdk /opt/java/openjdk
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
    && git config --system --add safe.directory '*'

COPY backend/javasmell backend/javasmell
COPY data/results/mlcq_dataset.csv data/results/mlcq_dataset.csv
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
