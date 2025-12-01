# Installation steps
- clone this repository;
- start `docker` (if it's not running yet), `cd` inside the local repo directory and build the dockerized service:
    ```bash
    sudo systemctl start docker
    cd ./qt_assignment
    docker-compose up --build
    ```

# Usage
- the service relies on CIK data to exist in the Redis storage;
- there is a background worker that handles the fetching of the CIK data automatically and periodically;
- the CIK data fetching can also be manually triggered via
    ```bash
    curl -X POST localhost:8000/refresh-cik
    ```

- get file:
    ```bash
    curl -X GET "localhost:8000/get-file?name=<name_of_entity>&file_type=<file_type>"
    ```

- companies of interest:
    ```bash
    curl -X GET "localhost:8000/get-file?name=apple%20inc&file_type=10-K"
    curl -X GET "localhost:8000/get-file?name=amazon%20com%20inc&file_type=10-K"
    curl -X GET "localhost:8000/get-file?name=meta%20platforms%2C%20inc.&file_type=10-K"
    curl -X GET "localhost:8000/get-file?name=alphabet%20inc.&file_type=10-K"
    curl -X GET "localhost:8000/get-file?name=netflix%20inc&file_type=10-K"
    curl -X GET "localhost:8000/get-file?name=goldman%20sachs%20group%20inc&file_type=10-K&cik=0000886982"
    ```
- current solution makes use of `minio` as file storage, where resulting `.pdf` files are stored under the `sec-filings` bucket;
- access minio storage:
    ```bash
    http://127.0.0.1:9001
    ```

# Run the test suite
- having the docker containers up and running, the tests can be run inside the container:
    ```bash
    docker exec -it qtserver poetry run pytest
    ```

# TODOs / known issues:
- have a postgres db available and integrate that for further redundancy, in case redis fails;
- write better tests to be more robust - what if we decide to use a different pdf library?
- the files as they are now are unusable, maybe some xml parsing library might help before converting them to pdf;
- need a partial matching algorithm. Levenshtein's algorithm (fuzzywuzzy) did not prove so successful;
- goldman sachs has 2 CIKs... and we're storing only the last one of them, because we're storing them using hashmaps;
    temporary workaround: allow the users to manually specify the CIK id;
- storage url signing docker-vs-host issue:
    the URL signing happens inside the qtserver docker container. as such,
    it knows about `minio:9000` and the signature is done for this hostname specifically;
    but when trying from the host, obviously there's no such hostname as `minio`, so the link will not work;
- have the `/get-file` endpoint accept POST requests instead of GET;
- have the bucket name configurable (`config.py`) instead of the hardcoded value of `sec-filings`;
- while we're at it, allow ingesting a JSON list of company names, file types and possibly cik ids;
- offload the conversion / export process to background tasks (Celery), right now, Goldman Sachs' 10-K submission takes 20+ mins to process
