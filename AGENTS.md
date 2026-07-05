# `wlkserver` repository

## What is this?

The code in the repo is the attempt to create an API to a MySQL database that is already in prodcution use as data backend of a shop cashier POS system.

The shop that is using the POS system is not a regular one, but is a fair trade shop. Buying the fair trade products in the shop via the POS supports fair trade, helps ensure income security, welfare and life improvement of producers in the Global South, and strengthens an ecological and socially responsible alternative to ruthless global trade that exploits resources and people, firing ecological destruction and social erosion.

However, times are hard for fair trade shops because the voluntary workers of the shop have little time for managing and improving the shop and sales are stagnating because of general inflation, difficult geopolitical crises as well as vibe shifts in society. At the same time, costs for running the shop are increasing, so we need to find ways to improve the shop and increase sales. One piece of the puzzle could be an improved and more automated POS system.

## Problems of the status quo POS system

The shop's POS system is written in Java and can be found in `../git/src/org/weltladen_bonn/pos/`. It has several limitations hindering its further development.

  1. **Old age:** It is based on Java Swing, which is a very old UI framework and does not have a fresh look and feel. When looking for help about Swing, I mainly find very old Stack Overflow posts from about 10 years ago or older. At least it is platform independent, but I would prefer a modern UI that is based on web-technology (HTML/CSS/JS).
  2. **Code verbosity:** It's hard for me to extend the functionality of the app and fix bugs since a lot of code is required to even do simple things. I do not use Java in my day-to-day work and so I lack practice. But I frequently use JavaScript and TypeScript. I would prefer a modern web-based interface for the POS system.
  3. **Missing structure:** There is no separation of concern at all in the Java POS code. Java classes responsible for UI views also contain backend code reading or writing to the database.
  4. **Lack of possibility for automation:** Because the business logic is tied to the Java Swing UI classes, transactions to the DB can only be done via opening the app and using mouse and keyboard to fill out forms in the app. It is not possible to trigger DB transactions from a script and automate DB edits, e.g. for automated read-ins of product price lists and automatic updates of the prices in the DB.

However, since all the app data is stored in a MySQL database, it is possible to interact with MySQL directly. However, instead of using the MySQL API, it would be more secure and more convenient to create a new API for interacting with the DB that already contains all the business logic. This API could solve all the problems at once.

## What we want to build

The plan is the following:

  1. We create a *server* application (API) that exposes an HTTP API to interact with the MySQL DB. MySQL has its own API, but for security reasons we do not want to make that accessible to regular users. Also, the business logic shall be already baked into the API so that it's also convenient to use the HTTP API. Logic outside the API shall be as small as possible, most logic shall be handled by the API. We use Python's FastAPI for the API.
  2. When the backend API is finished, we create a *client* application that uses the API to interact with the DB. There shall be separation of concern as much as possible: All business logic shall go into the server backend (as much as possible) and the client application shall only contain the GUI to interact with the server. We use SvelteKit for the frontend client, if possible with the option to also use SvelteNative for mobile apps.
  3. The API can also be used by a script, e.g. in Python, that executes tasks automatically (e.g. running regularly as a cron job). FOr example, a script could regularly download product lists from supplier websites and feed in new products or update prices automatically in the POS DB.

The database structure can be found in the SQL files in ../git/mysql/.

## What was done already

I have started with step 1, writing the server API backend in Python's FastAPI. The code is found in the `python` directory. A first try to use PHP for the API is contained in the `php` dir and is now obsolete. Code was too verbose and too complicated to be manageable.

I found FastAPI to be astonishishingly easy to use. Only a little amount of code is needed and development can go fast. Nevertheless, development has stalled due to time constraints. I want to revive development and use LLMs to increase development speed even further, suitable for a very limited time budget.

## The spirit of this endeavour

I want us to embark on this journey with a fun and positive mindset. We do this with the rewarding awareness that we are contributng to global justice via fair trade and also support the local fair trade shop to enable its continuous survival.

## The role of the LLM

You are an experienced Python backend developer (proficient in FastAPI) and TypeScript frontend developer (focused on using SvelteKit).

Please try to follow coding styles already used in the codebase.