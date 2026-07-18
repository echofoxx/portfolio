# Reverse Proxy and Rate-Limit Configuration

v0.4.0 does not use Express and does not rely on unrestricted proxy trust. Uvicorn proxy-header rewriting is intentionally disabled so the application’s exact-hop resolver remains the single client-identity authority. The FastAPI middleware resolves the client address using the exact configured number of controlled proxy hops.

## Direct access

```env
TRUST_PROXY_HOPS=0
```

The application ignores `X-Forwarded-For` and uses the direct socket peer.

## One reverse proxy

Browser → Synology/Nginx/Traefik/Cloudflare Tunnel connector → application:

```env
TRUST_PROXY_HOPS=1
```

The proxy must overwrite—not append untrusted client values to—the forwarding headers according to its security configuration.

## Multiple controlled proxies

Browser → edge proxy → internal reverse proxy → application:

```env
TRUST_PROXY_HOPS=2
```

Use the exact path length. Different-length paths to the same application can make hop-count trust unsafe and require a proxy-network allow-list implementation before production.

## Rate limits

```env
RATE_LIMIT_REQUESTS=300
RATE_LIMIT_WINDOW_SECONDS=900
```

The local reference implementation uses an in-memory bucket per process and client/scope. A multi-replica production deployment requires a shared approved rate-limit store such as Redis and coordinated proxy controls.

## Verification

```bash
curl -I http://localhost:8080/health/ready
```

Authenticated/write/API responses include:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-Resolved-Client-IP-Source`
- `Retry-After` when limited

Do not expose a client-IP debug endpoint in operational environments.
