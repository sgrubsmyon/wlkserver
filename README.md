# wlkserver

This repository contains the server backend with the HTTP-based API to interact with the SQL database.

This is meant as being part of a new, more modern, more modular server/client architecture of the fair trade shop point-of-sale system [Weltladenkasse](https://github.com/sgrubsmyon/Weltladenkasse).

The API is written in PHP and is based on this REST API PHP tutorial:
https://www.codeofaninja.com/2017/02/create-simple-rest-api-in-php.html.

## Requirements

Need to install `php` (e.g. `php7.4`) and `php7.4-mysql` packages in Ubuntu/Debian and a web server like `apache2`.

## Deploy

```
$ sudo rsync -rtlPvi --exclude=.git ./ /var/www/html/wlkserver/ && sudo chown www-data:www-data -R /var/www/html/wlkserver/
```