# gameserver-client

A simple server-client communication based on asyncio stream sockets using python 3.9.
As an example of requests, this application is based on simple ship/equipment economic

# Requirements

You will need a mysql DBMS. It is easier to setup it using docket:
```bash
docker run -d -ti --name mysql_db -e MYSQL_ROOT_PASSWORD="q1w2e3r4" -e MYSQL_DATABASE="gmdb" -p 3306:3306 mysql:8
```

# Run server

First, install dependencies for server running:

```bash
pip3 install -e ".[server]"
```

Then, you will need to edit settings.json to match your environment.

Also you will need a MySQL instance

Finally, you can start server to handle connections

```bash
python3 gameserver/server_cli.py [--settings-path PATH_TO_SETTINGS]
```

# Run client

First, install dependencies for client running. If you've done server running, you can skip this step:

```bash
pip3 install -e "."
```

Now you can connect to the server to begin some groovy actions:

```bash
python3 gameserver/client_cli.py --host SERVER_HOST --port SERVER_PORT
```

# Run tests

First, install dependencies for tests.

```bash
pip3 install -e ".[test]"
```

Then, execute pytest from repository root directory:

```bash
pytest
```

You can filter tests using `-k` argument

```bash
pytest -k "some pattern"
pytest -k "test_validate" #  You can specify here function name
pytest -k "test_client.py" #  Or a filename
```