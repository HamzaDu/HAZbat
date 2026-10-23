# Self-contained container (app + PostgreSQL in one):
#   docker build -t hazbat .
#   docker run -e START_LOCAL_DB=1 -p 8000:8000 -v hazbat-pgdata:/var/lib/postgresql/data -v hazbat-config:/etc/hazbat hazbat
#
# External database (START_LOCAL_DB not set):
#   docker run -p 8000:8000 -v hazbat-config:/etc/hazbat hazbat
#
# Settings are read from /etc/hazbat/hazbat.ini:
#   [database]  host, port, name, admin_password, read_write_password, read_only_password
#   [app]       session_secret, base_url, gemini_api_key (optional)

FROM alpine:latest

RUN apk add --no-cache \
    bash git su-exec \
    python3 python3-dev py3-pip \
    build-base gfortran openblas-dev libffi-dev jpeg-dev zlib-dev \
    postgresql postgresql-contrib

ENV PGDATA=/var/lib/postgresql/data

# Alpine's Python refuses system-wide pip installs (PEP 668); this is a single-purpose container, so override it.
# Requirements first, so this slow layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

RUN adduser -D app
WORKDIR /app
ENV PATH="$PATH:/app/scripts"
COPY main.py HAZbot.py ./
COPY core core
COPY routers routers
COPY services services
COPY utils utils
COPY schemas schemas
COPY --chmod=755 scripts scripts
COPY templates templates
COPY static static
RUN mkdir -p uploads/cycling_data && chown -R app /app/uploads
WORKDIR /

# Set START_LOCAL_DB=1 to run PostgreSQL inside this container. Everything else is read from /etc/hazbat/hazbat.ini.
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh

EXPOSE 8000
VOLUME ["/var/lib/postgresql/data", "/app/uploads", "/etc/hazbat"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
