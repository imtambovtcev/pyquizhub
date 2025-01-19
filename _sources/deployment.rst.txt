Deployment Guide
==============

Server Setup
-----------

1. System Requirements:
   
   * Python 3.10+
   * PostgreSQL (optional)
   * Redis (optional)

2. Environment Variables:

   .. code-block:: bash

      PYQUIZHUB_STORAGE=sql  # or filesystem
      PYQUIZHUB_DB_URL=postgresql://user:pass@localhost/pyquizhub
      PYQUIZHUB_SECRET_KEY=your-secret-key
      PYQUIZHUB_LOG_LEVEL=INFO

Docker Deployment
---------------

1. Build the image:

   .. code-block:: bash

      docker build -t pyquizhub .

2. Run with docker-compose:

   .. code-block:: yaml

      version: '3.8'
      services:
        web:
          image: pyquizhub
          ports:
            - "8080:8080"
          environment:
            - PYQUIZHUB_STORAGE=sql
            - PYQUIZHUB_DB_URL=postgresql://user:pass@db/pyquizhub
          depends_on:
            - db
        db:
          image: postgres:15
          environment:
            - POSTGRES_DB=pyquizhub
            - POSTGRES_USER=user
            - POSTGRES_PASSWORD=pass

Security Considerations
---------------------

1. Access Control
   * Use strong tokens
   * Implement rate limiting
   * Enable HTTPS

2. Database Security
   * Regular backups
   * Connection encryption
   * Proper user permissions
