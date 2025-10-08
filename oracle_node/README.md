## 1) Running the Postgres Database as the [official docs](https://docs.chain.link/chainlink-nodes/v1/running-a-chainlink-node) depicts
```
docker run --name cl-postgres -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 -d postgres
```



## 2) Run the Chainlink Node

### Define the configuration files, like the [`chainlink-sepolia`](../chainlink-sepolia/) folder

### Windows Shell
```
$absolutePath = (Resolve-Path ../chainlink-sepolia).Path
docker run --platform linux/x86_64/v8 --name chainlink -v "${absolutePath}:/chainlink" -it -p 6688:6688 --add-host=host.docker.internal:host-gateway smartcontract/chainlink:2.17.0 node -config /chainlink/config.toml -secrets /chainlink/secrets.toml start -a /chainlink/.api
```


