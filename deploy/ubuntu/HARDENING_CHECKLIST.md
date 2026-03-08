# Hardening Checklist (Prioridad Critica)

## 1) Content-Security-Policy (CSP)
- Aplicado en Nginx (`smartcontrol-hardened-*.conf`).
- No usar CSP en `frontend/index.html` para no romper dev runtime.

Verificar:
```bash
curl -I https://app.tudominio.com | grep -i content-security-policy
```

## 2) HSTS
- Activo solo en `smartcontrol-hardened-https.conf`.
- Requiere TLS valido.

Verificar:
```bash
curl -I https://app.tudominio.com | grep -i strict-transport-security
```

## 3) Bloqueo de archivos sensibles
- Regla Nginx para `.env`, dotfiles y extensiones sensibles (`.sql`, `.bak`, `.pem`, etc).

Verificar:
```bash
curl -i https://app.tudominio.com/.env
curl -i https://app.tudominio.com/.git/config
```
Debe responder `404`.

## 4) WAF (Cloudflare + servidor)
### Cloudflare (recomendado)
- Security > WAF > Managed Rules: ON.
- Activar OWASP Core Ruleset.
- Security Level: Medium o High.
- Bot Fight Mode: ON.
- Rate limiting rule:
  - URI equals `/api/auth/login`
  - Threshold: 5 requests / 1 minute por IP
  - Action: Block 10 minutos.

### Servidor
- Nginx ya aplica `limit_req` en `/api/auth/login`.
- Opcional extra: ModSecurity + OWASP CRS si tu infraestructura lo permite.

## 5) Rate limiting backend
- Backend: `RATE_LIMIT_LOGIN=5/minute` en `.env`.
- Endpoint protegido: `/api/auth/login`.

Verificar:
- Intentar 6+ logins fallidos en 1 minuto y confirmar `429` o bloqueo.

## 6) systemd hardening
- `NoNewPrivileges=true`
- `ProtectSystem=full`
- `ProtectHome=true`
- `MemoryDenyWriteExecute=true`
- `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`

Verificar:
```bash
systemctl cat smartcontrol-backend
```

## 7) Post-deploy obligatorio
1. Cambiar password del usuario admin.
2. Rotar `SECRET_KEY` si fue compartida.
3. Validar CORS en `.env` a dominio real.
4. Ejecutar:
```bash
nginx -t && systemctl reload nginx
systemctl restart smartcontrol-backend
curl http://127.0.0.1:8000/health
```
