FROM gliderlabs/alpine:3.3
MAINTAINER Hypothes.is Project and contributors

# Install system build and runtime dependencies.
RUN apk add --update \
    ca-certificates \
    libffi \
    libpq \
    python \
    py-pip \
    nodejs \
    git \
  && apk add \
    libffi-dev \
    g++ \
    make \
    postgresql-dev \
    python-dev \
  && pip install --no-cache-dir -U pip \
  && rm -rf /var/cache/apk/*

# Create the hypothesis user, group, home directory and package directory.
RUN addgroup -S hypothesis \
  && adduser -S -G hypothesis -h /var/lib/hypothesis hypothesis
WORKDIR /var/lib/hypothesis

# Copy packaging
COPY h/__init__.py h/_version.py ./h/
COPY README.rst setup.* requirements.txt ./
COPY scripts ./scripts/
COPY package.json gulpfile.js ./

# Install application dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY gunicorn.conf.py ./
COPY conf ./conf/
COPY h ./h/

# Build client and static assets

## Remove dependencies required only for unit testing
RUN npm install --production \
  && npm cache clean
RUN npm run build-assets

# Expose the default port.
EXPOSE 5000

# Set the Python IO encoding to UTF-8.
ENV PYTHONIOENCODING utf_8

# Start the web server by default
USER hypothesis
CMD ["gunicorn", "--paste", "conf/app.ini"]
