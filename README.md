# wlkserver

This repository contains the server backend with the HTTP-based API to interact with the SQL database.

This is meant as being part of a new, more modern, more modular server/client architecture of the fair trade shop point-of-sale system [Weltladenkasse](https://github.com/sgrubsmyon/Weltladenkasse).

## PHP version

A PHP version of the API was started, but not finished, based on this REST API PHP tutorial:
https://www.codeofaninja.com/2017/02/create-simple-rest-api-in-php.html.

In order to increase development speed (and perhaps also performance), a new version based on Python and the FastAPI library was started (see below).

### Requirements

Need to install `php` (e.g. `php7.4`) and `php7.4-mysql` packages in Ubuntu/Debian and a web server like `apache2`.

### Deploy

```
$ sudo rsync -rtlPvi --exclude=.git ./ /var/www/html/wlkserver/ && sudo chown www-data:www-data -R /var/www/html/wlkserver/
```

## Python version

I found this through https://realpython.com/fastapi-python-web-apis/ and like that you only need to write a minimal amount of code to get an API running. I also like that there is automatic documentation/testing available via Swagger.
