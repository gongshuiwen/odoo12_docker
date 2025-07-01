FROM python:3.7-slim-bullseye

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Generate locale C.UTF-8 for postgres and general locale data
ENV LANG=C.UTF-8

# Set the relative path of the source files relative to the build context
ARG SOURCE_DIR=odoo

# Set the relative path of the docker files relative to the build context
ARG DOCKER_DIR=.

# Set deb mirrors
RUN echo 'deb https://mirrors.aliyun.com/debian/ bullseye main non-free contrib' > /etc/apt/sources.list && \
    echo 'deb https://mirrors.aliyun.com/debian/ bullseye-updates main non-free contrib' >> /etc/apt/sources.list && \
    echo 'deb https://mirrors.aliyun.com/debian/ bullseye-backports main non-free contrib' >> /etc/apt/sources.list && \
    echo 'deb https://mirrors.aliyun.com/debian-security bullseye-security main' >> /etc/apt/sources.list

# Install essential packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    node-less \
    xz-utils

# Install wkhtmltopdf
COPY $DOCKER_DIR/deb/wkhtmltox_0.12.6.1-3.bullseye_amd64.deb /wkhtmltox.deb
RUN apt-get update && apt-get install -y --no-install-recommends ./wkhtmltox.deb && \
    rm -f wkhtmltox.deb

# Install fonts
COPY $DOCKER_DIR/fonts/* /usr/share/fonts/windows/
RUN apt-get update && apt-get install -y xfonts-utils fonts-noto-cjk && \
    mkfontscale && mkfontdir && fc-cache -fv

# Install latest postgresql-client
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg dirmngr && \
    echo "deb https://mirrors.aliyun.com/postgresql/repos/apt/ bullseye-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/apt.postgresql.org.gpg >/dev/null && \
    apt-get update && apt-get install -y --no-install-recommends postgresql-client libpq-dev && \
    rm /etc/apt/sources.list.d/pgdg.list

# Install python requirements
COPY $DOCKER_DIR/requirements.txt /requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    pip3 install --no-cache-dir\
      -r /requirements.txt \
      -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    apt-get remove -y build-essential && apt-get -y autoremove

# Patch werkzeug logging format
RUN cd /usr/local/lib/python3.7/site-packages/werkzeug && \
    sed -i "293s/%s - - \[%s\] %s/%s/" serving.py && \
    sed -i "293s/self.address_string(),/message % args))/" serving.py && \
    sed -i '294,295d' serving.py

# Create user and gourp, create /mnt/extra-addons, set permissions
RUN adduser --system --home "/var/lib/odoo" --quiet --group "odoo" && \
    mkdir -p /mnt/extra-addons && \
    chown -R odoo:odoo /var/lib/odoo /mnt/extra-addons

# Copy Odoo 12.0 source files to python site-packages
COPY --chown=odoo $SOURCE_DIR/odoo /usr/local/lib/python3.7/site-packages/odoo/
COPY --chown=odoo $SOURCE_DIR/addons /usr/local/lib/python3.7/site-packages/odoo/addons/

# Patch RequestHandler to support HTTP/1.1
RUN sed -i "128i\        self.protocol_version = 'HTTP/1.1'" \
    /usr/local/lib/python3.7/site-packages/odoo/service/server.py

# Patch PreforkServer#process_spawn to support no long_polling worker
RUN sed -i "755c\            if not self.long_polling_pid and config['longpolling_port'] >= 0:" \
    /usr/local/lib/python3.7/site-packages/odoo/service/server.py

# Copy odoo configuration file, entrypoint script and start scripts
COPY --chown=odoo $DOCKER_DIR/odoo.conf /etc/odoo/odoo.conf
COPY --chown=odoo $DOCKER_DIR/docker-entrypoint.sh /
COPY --chown=odoo $DOCKER_DIR/*.py /usr/local/bin/

# Mount /var/lib/odoo to allow restoring filestore
VOLUME ["/var/lib/odoo"]

# Expose Odoo services
EXPOSE 8069 8072

# Set the default config file
ENV ODOO_RC=/etc/odoo/odoo.conf

# Set default user when running the container
USER odoo

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["odoo"]
