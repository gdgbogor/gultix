FROM pretix/standalone:stable

USER root

# Install midtransclient for plugin
RUN pip install --upgrade pip && \
    pip install --no-cache-dir midtransclient>=1.4.0

# Create directories for plugin installation
RUN mkdir -p /pretix/src/templates/pretix_midtrans

# Copy plugin files directly into the image
COPY pretix-midtrans /pretix/src/pretix-midtrans/
COPY pretix-fontpack-free-master /pretix/src/pretix-fontpack-free-master/

# Install the plugin during build
RUN cd /pretix/src/pretix-midtrans && \
    pip install -e .
RUN cd /pretix/src/pretix-fontpack-free-master && \
    pip install -e . && \
    make

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
