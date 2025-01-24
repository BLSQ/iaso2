# Environnement variables

## DB connection related

the url is build based on the following env variables

```
RDS_USERNAME
RDS_PASSWORD
RDS_HOSTNAME
RDS_DB_NAME
RDS_PORT
```

the SQL dashboard use a dedicated user/password with readonly access to the data

```
DB_READONLY_USERNAME 
DB_READONLY_PASSWORD
```

## AWS related

Storing the various files like

- js/css/... static assets
- raw forms (xlsform), submissions (xml and media),... is done in s3 (or an s3 compatible api like minio)

```
AWS_ACCESS_KEY_ID:
AWS_SECRET_ACCESS_KEY:
AWS_S3_REGION_NAME
AWS_STORAGE_BUCKET_NAME:
AWS_S3_ENDPOINT_URL: (used to for ex to point to minio)
```

for async task

```
BACKGROUND_TASK_SERVICE    : default to SQS :  possible values are  SQS POSTGRES
BEANSTALK_SQS_REGION
BEANSTALK_SQS_URL

```

## ClamAV related

If you don't set the required variables, ClamAV will not be configured and Iaso will not be able to scan uploaded files.

| name          | optional | default value      | description                                                                                  |
|---------------|----------|--------------------|----------------------------------------------------------------------------------------------|
| CLAMAV_ACTIVE | false    | `False`            | whether uploaded files need to be scanned with ClamAV or not                                 |
| CLAMAV_FQDN   | false    | `www.some-url.com` | address that Iaso can use to reach ClamAV - FQDN, not full URL (e.g. `clamav.mywebsite.com`) |
| CLAMAV_PORT   | true     | `3310`             | port that Iaso can use to reach ClamAV                                                       |



# Security Settings

## Django settings

Iaso allows to set some of Django security settings as environment variable. To activate these features
set the environment variable to `"true"`. Default is `"false"`

```
CSRF_COOKIE_HTTPONLY 
CSRF_COOKIE_SECURE 
SESSION_COOKIE_SECURE
```

## CORS

It is possible to setup a IASO server with CORS authorizing access from any server with the following environment
variable `"ENABLE_CORS"`.
Default is `"true"`

## Disabling login through passwords    

Set the environment variable `DISABLE_PASSWORD_LOGINS`to the value`"true"` in case you wish to deactivate passwords
using login:

- in the basic login page
- to connect to the admin
- through /api/token , which is used by default by the mobile application

## Sentry related

If you don't provide a SENTRY_URL, sentry won't be configured

| name                                | optional | default value | description                                    | --- |
|-------------------------------------|----------|---------------|------------------------------------------------|-----|
| SENTRY_URL                          | true     | -             | url specific to your sentry account            |     |
| SENTRY_ENVIRONMENT                  | true     | development   | environnement (dev, staging, prod,...)         |     |
| SENTRY_TRACES_SAMPLE_RATE           | true     | 0.1           | float between 0 and 1 : send 10%               |     |
| SENTRY_ERRORS_SAMPLE_RATE           | true     | 1.0           | float between 0 and 1 : send everything        |     |
| SENTRY_ERRORS_HTTPERROR_SAMPLE_RATE | true     | 0.8           | float between 0 and 1 : send 80% of the errors |     |  

## Maintenance mode
`MAINTENANCE_MODE` (default is `"false"`)

If you need to set up IASO in maintenance mode, meaning that it will display at / a page indicating that the 
server is under maintenance, and give a 404 answer to all requests except for /health or /_health (wich we encourage to use 
for status monitoring), you can set the environment variable `MAINTENANCE_MODE` to the value `"true"`