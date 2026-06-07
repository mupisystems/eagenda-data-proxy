# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |

## Reporting a Vulnerability

This project handles **personally identifiable information (PII)**, so we take security seriously.

**Do not open a public issue for security vulnerabilities.**

Instead, please report them privately:

1. **Email**: Send details to **contato@mupisystems.com.br**
2. **GitHub**: Use [GitHub's private vulnerability reporting](https://github.com/mupisystems/eagendas-data-proxy/security/advisories/new) if available

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: within 48 hours
- **Initial assessment**: within 5 business days
- **Fix or mitigation**: depends on severity, typically within 30 days

We will coordinate disclosure with you and credit you in the advisory (unless you prefer to remain anonymous).

## Security Best Practices for Deployers

- Run the proxy behind a reverse proxy (nginx/Traefik) with TLS termination
- Restrict access to `/admin/` via network rules or reverse proxy authentication
- Use strong, unique values for `PROXY_AUTH_TOKENS`
- Rotate API tokens periodically
- Keep PostgreSQL and Redis on a private network (not exposed to the internet)
- Set `AUDIT_RETENTION_DAYS` according to your data retention policy
- Review audit logs regularly
