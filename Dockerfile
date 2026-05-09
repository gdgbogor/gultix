FROM pretix/standalone:stable

USER root

# Install git in case it's not present for fetching from private repo
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install midtransclient for plugin
RUN pip install --upgrade pip && \
    pip install --no-cache-dir midtransclient>=1.4.0

# Install pretix-midtrans plugin from private repository
RUN pip install "git+https://${GITHUB_TOKEN}@github.com/awsugid/pretix-midtrans.git"

# Install the fontpack plugin from private github repository
RUN pip install "git+https://${GITHUB_TOKEN}@github.com/gdgbogor/gultix-google-font.git"

# Collect static files for all plugins
RUN pretix collectstatic --no-input

# Set proper permissions for source files
RUN chown -R pretixuser:pretixuser /pretix/src/

# Ensure /data directory exists with proper permissions
RUN mkdir -p /data && \
    chmod 755 /data && \
    chown -R pretixuser:pretixuser /data

# Set PYTHONPATH for plugin
ENV PYTHONPATH=/pretix/src

EXPOSE 80

ENTRYPOINT ["pretix"]
# CMD ["all"]
