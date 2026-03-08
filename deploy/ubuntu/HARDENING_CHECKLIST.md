# Hardening Checklist (Critica + Alta)

## 1) CSP
- Aplicado en Nginx (`smartcontrol-hardened-*.conf`).

Verificar:
```bash
curl -I https://app.tudominio.com | grep -i content-security-policy
```

## 2) HSTS
- Activo solo en plantilla HTTPS.

Verificar:
```bash
curl -I https://app.tudominio.com | grep -i strict-transport-security
```

## 3) Bloqueo de archivos sensibles
- Deniega `.env`, dotfiles y extensiones sensibles.

Verificar:
```bash
curl -i https://app.tudominio.com/.env
curl -i https://app.tudominio.com/.git/config
```

## 4) WAF
### Cloudflare
- Security > WAF > Managed Rules: ON.
- OWASP Core Ruleset: ON.
- Bot Fight Mode: ON.
- Regla rate-limit: `/api/auth/login`, 5 req/min/IP, bloqueo 10 min.

### Servidor
- Nginx aplica `limit_req` para login.
- Opcional: ModSecurity + OWASP CRS.

## 5) Rate limiting backend
- Backend: `RATE_LIMIT_LOGIN=5/minute`.
- Login protegido por `slowapi`.

## 6) Headers de alta prioridad
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy` restringida

## 7) Ocultar fingerprinting
- `server_tokens off` en Nginx.
- `proxy_hide_header X-Powered-By` para backend.

Verificar:
```bash
curl -I https://app.tudominio.com | grep -Ei 'server:|x-powered-by'
```

## 8) TLS fuerte
- `ssl_protocols TLSv1.2 TLSv1.3;`
- TLS 1.0/1.1 deshabilitado.

Verificar:
```bash
openssl s_client -connect app.tudominio.com:443 -tls1
# Debe fallar
```

## 9) Cookies seguras de sesion
- Backend setea cookie de sesion con `HttpOnly; Secure; SameSite=Strict`.
- Cookie CSRF separada para header token.

## 10) CSRF protection
- Backend exige `X-CSRF-Token` en `POST/PUT/PATCH/DELETE` de `/api/*` (excepto login).
- Frontend envia token automaticamente.

## 11) systemd hardening
- `NoNewPrivileges=true`
- `ProtectSystem=full`
- `ProtectHome=true`
- `MemoryDenyWriteExecute=true`
- `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`

Verificar:
```bash
systemctl cat smartcontrol-backend
```

## 12) Post-deploy obligatorio
1. Cambiar password del usuario admin.
2. Rotar `SECRET_KEY` si fue compartida.
3. Confirmar CORS y TRUSTED_HOSTS reales.
4. Ejecutar:
```bash
nginx -t && systemctl reload nginx
systemctl restart smartcontrol-backend
curl -fsS http://127.0.0.1:8000/health
```
