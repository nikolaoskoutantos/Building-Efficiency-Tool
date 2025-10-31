## Service Overview & Configuration

- **IPFS**: Decentralized file storage. Used to store encrypted data and make it accessible via a content identifier (CID). Our app uploads encrypted files here and retrieves them by CID.
- **Vault**: Secrets management and encryption. Provides the encryption engine for encrypting data before it is uploaded to IPFS, and decrypting it when retrieved.
- **Caddy**: Web server and reverse proxy. Handles HTTPS, domain routing, and can provide authentication for IPFS and Vault endpoints.

Environment variables for each service are set directly in the `docker-compose.yml` file or in the service configuration files. There are no `.env` files required for this setup.

## Quick Start

```powershell
# Start all services
docker-compose up -d

# For encryption-before-IPFS workflow (REQUIRED):
./vault-setup.sh

# Access Vault UI: http://localhost:8200 
# Token: qoe-dev-token-2025
```

## Encrypt-then-Store Workflow

1. **Encrypt data** with Vault Transit engine
2. **Store encrypted data** in IPFS
3. **Retrieve and decrypt** when needed

See `ENCRYPT_IPFS_WORKFLOW.md` for detailed examples.

## Services

- **IPFS**: http://localhost:5001 (API), http://localhost:8080 (Gateway)
- **Caddy**: http://localhost:80/443 (Proxy)
- **Vault**: http://localhost:8200 (UI + Encryption API)

## Commands

```powershell
docker-compose logs -f      # View logs
docker-compose down         # Stop services
```

```bash
docker-compose up -d
```

That's it. Everything will start up and work together.

### Option 2: Install Everything Manually

#### First, get IPFS running:

```bash
# Download IPFS (visit https://docs.ipfs.tech/install/ if this doesn't work)
curl -sSL https://get.ipfs.io | sh
ipfs init
ipfs daemon
```

#### Then install Caddy:

```bash
# Windows folks:
choco install caddy
# or: scoop install caddy
# or: winget install Caddy.Caddy

# Mac people:
brew install caddy

# Linux users (Ubuntu/Debian):
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

### Configure IPFS for our app

IPFS needs to play nice with our web app, so run these commands:

```bash
# Allow our app to talk to IPFS
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Origin '["*"]'
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Methods '["PUT", "POST", "GET"]'
ipfs config --json API.HTTPHeaders.Access-Control-Allow-Headers '["Content-Type"]'

# Start it up
ipfs daemon
```

### Set up Caddy

1. Copy the example config:

   ```bash
   cp Caddyfile.ipfs.example Caddyfile
   ```
2. Edit it with your domain and settings
3. Fire it up:

   ```bash
   caddy run
   ```

## Running on a Server?

If you're setting this up on a VPS or dedicated server, you might want to:

### Create proper services (Linux)

Make IPFS start automatically:

```bash
sudo tee /etc/systemd/system/ipfs.service > /dev/null <<EOF
[Unit]
Description=IPFS daemon
After=network.target

[Service]
Type=notify
ExecStart=/usr/local/bin/ipfs daemon
Restart=on-failure
User=ipfs
Group=ipfs

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable ipfs
sudo systemctl start ipfs
```

Caddy usually handles this automatically, but you can enable it too:

```bash
sudo systemctl enable caddy
sudo systemctl start caddy
```

## Ports and Stuff

Here's what runs where:

- **IPFS API**: localhost:5001 (this is how our app talks to IPFS)
- **IPFS Gateway**: localhost:8080 (for viewing files in browser)
- **Caddy HTTP**: port 80
- **Caddy HTTPS**: port 443

## Troubleshooting (aka "Why isn't this working?!")

### IPFS being stubborn?

Sometimes IPFS just... stops. Here's what usually fixes it:

```bash
# First, check if it's actually alive
ipfs id

# If that fails, try restarting the daemon
# Kill it first: Ctrl+C or kill the process
# Then start fresh: ipfs daemon

# Still acting weird? Clean house:
ipfs repo gc
```

**Pro tip**: If IPFS won't start, it's usually because another instance is already running or the port is taken.

### Caddy throwing a fit?

Caddy is usually pretty good about telling you what's wrong:

```bash
# Check if your Caddyfile makes sense
caddy validate --config Caddyfile

# See what Caddy is complaining about
journalctl -u caddy -f

# Or if you're running it manually, just look at the terminal output
```

**Most common issue**: Wrong domain syntax in the Caddyfile or port conflicts.

### Nothing connecting to anything?

Network issues are the worst, but here's how to debug:

```bash
# See what's actually listening on your ports
netstat -tulpn | grep :5001
netstat -tulpn | grep :8080

# No output? Nothing's running on those ports
# Got output? Something is there, check if it's what you expect
```

**Quick fixes to try**:

- Restart everything (the classic IT solution)
- Check your firewall isn't blocking the ports
- Make sure you're not trying to run two things on the same port
- If using Docker, check the containers are actually running: `docker ps`

## Security Notes

Don't skip this part!

1. **Firewall**: Only open the ports you actually need
2. **IPFS**: Be careful what you put on there - it's public by default
3. **HTTPS**: Caddy handles this automatically (pretty cool, right?)
4. **Authentication**: The IPFS Caddyfile example has auth built in

## How This Connects to the Main App

Our weather data external adapter uploads stuff to IPFS like this:

```javascript
const IPFS_URL = process.env.IPFS_URL || 'http://127.0.0.1:5001/api/v0';
```

So make sure:

1. Your IPFS is reachable at that URL
2. Firewall allows the connection
3. Test it actually works before going live

## Need Help?

If something's not working:

1. Check the service logs first
2. Make sure you can actually reach the ports
3. Double-check your Caddyfile syntax
4. Try the Docker setup if manual install is being difficult

Remember: IPFS can be a bit finicky the first time, but once it's working, it's pretty solid!
